"""Runtime leak probe — prove isolation on the deployed container, not on paper.

Why this exists
---------------
A static file-layout check is not isolation. A layout can look clean on disk
while the agent's shell can still ``cat`` the reference oracle on the live box,
and then every score is the model reading the answer. Isolation has to be shown
by a trace from the running container, where every attempt to reach the oracle
is made and seen to fail.

PriorLock's isolation is *structurally* strong — the verifier grades against its
own pristine copy, so even a fully leaked library changes no score, and gate G8
proves that. But "strong by argument" is not a trace. This
module produces the trace.

How it works
------------
``priorlock leakprobe <task>`` generates a sibling Harbor task:

    <task>__leakprobe/
        environment/     identical to the wrapped task — the SAME image
        solution/solve.sh   the probe: every leak vector, from every entrypoint
        tests/test.sh       asserts every attempt FAILED; reward 1.0 or 0.0

Running it with ``harbor run -a oracle`` executes the probe **inside the real
deployed container, with the agent's own privileges and paths**, and the
verifier then judges the trace. That is what makes it a runtime proof rather
than a static assertion.

Leak vectors covered
--------------------
=====  =====================================================================
V1/V2  cat / find / import of oracle assets, from the live container
V3     .git history, gold on disk, answer-bearing environment variables
V4     an oracle-exclusive canary string, planted at wrap time, searched for
       across the entire agent-visible filesystem, environment and process table
V5     passive leak sweep — env, /proc, logs, filenames, tool output
V6     every entrypoint: shell, python import, sys.path, pip metadata,
       filesystem walk from several cwds, subprocess, and the harness dirs
V7     network egress actually attempted, and what it can reach recorded
=====  =====================================================================
"""
from __future__ import annotations

import json
import shutil
import stat
from dataclasses import dataclass, field
from pathlib import Path

from .inject import MANIFEST, detect_layout, is_wrapped, read_manifest

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

TRACE_NAME = "leakprobe_trace.json"


# ═════════════════════════════════════════════════════════════════════════════
#  The probe — runs inside the container as the agent
# ═════════════════════════════════════════════════════════════════════════════

PROBE_PY = r'''#!/usr/bin/env python3
"""PriorLock runtime leak probe.

Runs INSIDE the deployed container with the agent's own privileges. Attempts
every route to the oracle we can think of and records the outcome of each.
It never asserts — judgement belongs to the verifier, which cannot be reached
from here. This file only produces evidence.
"""
import json, os, subprocess, sys, glob, socket

CANARY = __CANARY__
LIB = __LIB__
WORKDIR = __WORKDIR__
CONTAINER_REPO = __CONTAINER_REPO__
OUT = __OUT__

attempts = []


def record(vector, target, reached, detail=""):
    attempts.append({"vector": vector, "target": target,
                     "reached": bool(reached), "detail": str(detail)[:300]})


# ── V1/V2 · cat the oracle assets ────────────────────────────────────────────
ORACLE_PATHS = [
    "/tests", "/tests/probe_grade.py", "/tests/probe_input.json",
    "/tests/task_verify.sh", "/tests/test.sh",
    "/tests/_plx_lib/%s/__init__.py" % LIB,
    "/tests/_plx_reference/gold.py", "/tests/_plx_reference/familiar.py",
    "/tests/_plx_reference/solve.orig", "/tests/_plx_reference/instruction.orig",
    "/solution", "/solution/solve.sh", "/app/solution/solve.sh",
    "/logs", "/logs/verifier", "/logs/verifier/reward.json",
    "/priorlock.toml", "/app/priorlock.toml",
]
for p in ORACLE_PATHS:
    try:
        if os.path.isdir(p):
            record("cat", p, True, "directory listing: " + ",".join(os.listdir(p))[:200])
        else:
            with open(p) as f:
                record("cat", p, True, "read %d bytes" % len(f.read()))
    except Exception as exc:
        record("cat", p, False, type(exc).__name__)

# ── V2 · find the oracle anywhere on the filesystem ──────────────────────────
NEEDLES = ["probe_grade.py", "gold.py", "familiar.py", "expected.json",
           "solve.orig", "instruction.orig", "priorlock.toml", "task_verify.sh"]
for needle in NEEDLES:
    try:
        r = subprocess.run(["find", "/", "-name", needle, "-not", "-path", "*/proc/*"],
                           capture_output=True, text=True, timeout=25)
        hits = [h for h in r.stdout.splitlines() if h.strip()]
        record("find", needle, bool(hits), "; ".join(hits[:6]) or "no hits")
    except Exception as exc:
        record("find", needle, False, type(exc).__name__)

# also: any _plx_* directory
try:
    r = subprocess.run(["find", "/", "-name", "_plx_*", "-not", "-path", "*/proc/*"],
                       capture_output=True, text=True, timeout=25)
    hits = [h for h in r.stdout.splitlines() if h.strip()]
    record("find", "_plx_*", bool(hits), "; ".join(hits[:6]) or "no hits")
except Exception as exc:
    record("find", "_plx_*", False, type(exc).__name__)

# ── V6 · import routes ───────────────────────────────────────────────────────
for mod in ("probe_grade", "gold", "familiar", "priorlock",
            "priorlock.probes", "priorlock.probes.catalog", "priorlock.env"):
    try:
        __import__(mod)
        record("import", mod, True, "imported")
    except Exception as exc:
        record("import", mod, False, type(exc).__name__)

# the shipped library SHOULD import — it is the agent's tool, not the oracle
try:
    __import__(LIB)
    record("import", LIB + " (expected reachable)", True, "the agent's own library")
except Exception as exc:
    record("import", LIB + " (expected reachable)", False, type(exc).__name__)

# ── V6 · sys.path and installed packages ─────────────────────────────────────
record("sys.path", "entries", False, " | ".join(sys.path)[:280])
try:
    r = subprocess.run([sys.executable, "-m", "pip", "list"],
                       capture_output=True, text=True, timeout=60)
    leaked = [ln for ln in r.stdout.splitlines()
              if "priorlock" in ln.lower() or "verifiers" in ln.lower()]
    record("pip list", "priorlock installed?", bool(leaked), "; ".join(leaked) or "absent")
except Exception as exc:
    record("pip list", "priorlock installed?", False, type(exc).__name__)

# ── V6 · walk the filesystem from several cwds ───────────────────────────────
for base in (WORKDIR, CONTAINER_REPO, "/", "/tmp", "/root", "/home"):
    try:
        found, scanned, capped = [], 0, False
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs
                       if d not in ("proc", "sys", "dev", "node_modules", ".git")]
            scanned += len(files)
            for fn in files:
                if fn in NEEDLES or "_plx" in root:
                    found.append(os.path.join(root, fn))
            if scanned > 40000:
                capped = True
                break                      # exits os.walk, not just the file loop
        record("walk", base, bool(found),
               "scanned %d files%s; %s" % (scanned, " (capped)" if capped else "",
                                           "; ".join(found[:5]) or "no oracle assets"))
    except Exception as exc:
        record("walk", base, False, type(exc).__name__)

# ── V3/V5 · passive leak sweep ───────────────────────────────────────────────
env_hits = [k for k, v in os.environ.items()
            if CANARY in str(v) or "priorlock" in k.lower() or "PLX" in k]
record("env", "answer-bearing variables", bool(env_hits), "; ".join(env_hits) or "none")

try:
    r = subprocess.run(["git", "log", "--oneline", "-5"], cwd=WORKDIR,
                       capture_output=True, text=True, timeout=20)
    has_git = r.returncode == 0 and bool(r.stdout.strip())
    record("git", "history in workdir", has_git, r.stdout[:200] or "no repository")
except Exception as exc:
    record("git", "history in workdir", False, type(exc).__name__)

try:
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=20)
    oracle_procs = [ln for ln in r.stdout.splitlines()
                    if "probe_grade" in ln or "_plx_reference" in ln]
    record("ps", "oracle in process table", bool(oracle_procs),
           "; ".join(oracle_procs[:3]) if oracle_procs
           else ("process table readable, no oracle process"
                 if r.returncode == 0 else "ps unavailable"))
except Exception as exc:
    record("ps", "oracle in process table", False, type(exc).__name__)

# ── V4 · the oracle-exclusive canary ─────────────────────────────────────────
# This string exists ONLY in verifier-side assets. If the agent can see it
# anywhere, something the agent should not reach is reachable.
canary_hits = []
try:
    r = subprocess.run(
        ["grep", "-rl", CANARY, "/app", "/tmp", "/home", "/root", "/etc", "/usr/local"],
        capture_output=True, text=True, timeout=45)
    canary_hits = [h for h in r.stdout.splitlines() if h.strip()]
except Exception:
    pass
for k, v in os.environ.items():
    if CANARY in str(v):
        canary_hits.append("env:" + k)
record("canary", "oracle-exclusive string", bool(canary_hits),
       "; ".join(canary_hits[:6]) or "not present on the agent surface")

# ── V7 · network egress ──────────────────────────────────────────────────────
for host, port in (("pypi.org", 443), ("github.com", 443), ("1.1.1.1", 53)):
    try:
        socket.setdefaulttimeout(6)
        s = socket.create_connection((host, port), timeout=6)
        s.close()
        record("network", "%s:%d" % (host, port), True, "connected")
    except Exception as exc:
        record("network", "%s:%d" % (host, port), False, type(exc).__name__)

# ── write the trace ──────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w") as f:
    json.dump({"canary": CANARY, "library": LIB, "attempts": attempts}, f, indent=2)

reached = [a for a in attempts if a["reached"]]
print("PriorLock leak probe: %d attempts, %d reached" % (len(attempts), len(reached)))
for a in reached:
    print("  REACHED  %-10s %s" % (a["vector"], a["target"]))
'''


CHECKER_PY = r'''#!/usr/bin/env python3
"""Verifier-side judgement of the leak-probe trace.

The probe collects evidence but never judges — it runs with the agent's
privileges and anything it concluded would be as untrustworthy as the agent.
This runs verifier-side and decides.
"""
import json, os, sys

TRACE = __TRACE__

# Vectors that are ALLOWED to succeed, and why.
ALLOWED = {
    # the agent's own library must be importable — it is the tool, not the oracle
    "import": lambda t: t.endswith("(expected reachable)"),
    # sys.path is informational; it is recorded, never asserted
    "sys.path": lambda t: True,
    # network reachability is a policy question, reported separately below
    "network": lambda t: True,
}


def main():
    if not os.path.isfile(TRACE):
        print("FAIL: no trace at %s — the probe did not run" % TRACE)
        return 0.0

    data = json.load(open(TRACE))
    attempts = data.get("attempts", [])
    if not attempts:
        print("FAIL: empty trace")
        return 0.0

    leaks, network_open = [], []
    for a in attempts:
        if not a["reached"]:
            continue
        vector, target = a["vector"], a["target"]
        if vector == "network":
            network_open.append(target)
            continue
        allow = ALLOWED.get(vector)
        if allow and allow(target):
            continue
        leaks.append(a)

    print("leak probe: %d attempts" % len(attempts))
    print("  oracle reachable from the agent: %d" % len(leaks))
    for a in leaks:
        print("    LEAK  %-10s %-42s %s" % (a["vector"], a["target"], a["detail"][:90]))

    canary = [a for a in attempts if a["vector"] == "canary"]
    if canary:
        c = canary[0]
        print("  canary %s" % ("VISIBLE — " + c["detail"] if c["reached"]
                               else "not on the agent surface"))

    if network_open:
        print("  network egress reachable: %s" % ", ".join(network_open))
        print("    (declared by the task's own allow_internet / network_mode setting)")
    else:
        print("  network egress: fully blocked")

    if leaks:
        print("\nISOLATION FAILED")
        return 0.0
    print("\nISOLATION PROVEN AT RUNTIME")
    return 1.0


if __name__ == "__main__":
    score = main()
    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w") as f:
        f.write(str(score) + "\n")
    with open("/logs/verifier/reward.json", "w") as f:
        json.dump({"reward": score}, f)
    try:
        import shutil
        shutil.copy(TRACE, "/logs/verifier/leakprobe_trace.json")
    except Exception:
        pass
    sys.exit(0)
'''


# ═════════════════════════════════════════════════════════════════════════════
#  Generation
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class LeakProbeResult:
    path: Path
    canary: str
    created: list[str] = field(default_factory=list)


def build_leakprobe(task_dir: str | Path, out_dir: str | Path | None = None
                    ) -> LeakProbeResult:
    """Generate a sibling Harbor task that probes the wrapped task's isolation."""
    task_dir = Path(task_dir).resolve()
    if not is_wrapped(task_dir):
        raise RuntimeError(f"{task_dir.name} is not wrapped — nothing to probe")

    layout = detect_layout(task_dir)
    meta = read_manifest(task_dir).get("priorlock", {})
    canary = meta.get("canary")
    if not canary:
        raise RuntimeError(
            "This task carries no oracle canary. Re-wrap it with a current "
            "PriorLock (`priorlock wrap <task> --force`) so a canary is planted."
        )

    dest = Path(out_dir) if out_dir else task_dir.parent / f"{task_dir.name}__leakprobe"
    if dest.exists():
        shutil.rmtree(dest)
    created: list[str] = []

    def write(rel: str, content: str, executable: bool = False) -> None:
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        if executable:
            p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        created.append(rel)

    # identical environment → identical image → a real proof, not an analogue
    shutil.copytree(layout.environment, dest / "environment")
    created.append("environment/ (copied from the wrapped task)")

    # task.toml, keeping the host's runtime settings
    original_toml = layout.task_toml.read_text() if layout.task_toml else ""
    write("task.toml", original_toml.rstrip() + "\n")

    write("instruction.md", f"""\
# Isolation leak probe

This task exists to **prove**, at runtime on the real deployed container, that
the agent cannot reach the oracle for `{task_dir.name}`.

It is not a capability test. The probe attempts every route we know of — `cat`,
`find`, `import`, `sys.path`, pip metadata, filesystem walks from several
working directories, environment variables, git history, the process table, an
oracle-exclusive canary string, and network egress — and records the outcome of
each in `{TRACE_NAME}`.

The verifier then asserts that **every** oracle route failed. A single reachable
asset fails the task.
""")

    probe = (PROBE_PY
             .replace("__CANARY__", json.dumps(canary))
             .replace("__LIB__", json.dumps(meta.get("library", "")))
             .replace("__WORKDIR__", json.dumps(meta.get("workdir", "/app")))
             .replace("__CONTAINER_REPO__", json.dumps(meta.get("container_repo", "/app")))
             .replace("__OUT__", json.dumps(f"/tmp/{TRACE_NAME}")))
    write("solution/probe.py", probe)
    write("solution/solve.sh",
          "#!/bin/bash\n"
          "# The 'oracle' for this task IS the probe: it runs with the agent's\n"
          "# own privileges inside the real container and produces the trace.\n"
          "set -uo pipefail\n"
          f"python3 {meta.get('workdir', '/app')}/probe.py || true\n",
          executable=True)

    # the probe must be inside the image, so drop it on the agent surface too
    rel_repo = layout.repo.relative_to(layout.environment)
    write(f"environment/{rel_repo}/probe.py", probe)

    checker = CHECKER_PY.replace("__TRACE__", json.dumps(f"/tmp/{TRACE_NAME}"))
    write("tests/check_leak.py", checker)
    write("tests/test.sh",
          "#!/bin/bash\n"
          "# Judge the trace the probe left behind. Verifier-side only.\n"
          "set -uo pipefail\n"
          "mkdir -p /logs/verifier\n"
          "python3 /tests/check_leak.py\n",
          executable=True)

    return LeakProbeResult(path=dest, canary=canary, created=created)


# ═════════════════════════════════════════════════════════════════════════════
#  Offline pre-check — catch what can be caught without Docker
# ═════════════════════════════════════════════════════════════════════════════

def canary_scan(task_dir: str | Path) -> dict:
    """Offline canary check: the canary must appear ONLY in verifier-side assets.

    This is the static half. It is cheap, it runs in CI, and it catches the
    common mistake, but it is not a runtime proof. `build_leakprobe` produces
    that.
    """
    task_dir = Path(task_dir).resolve()
    layout = detect_layout(task_dir)
    meta = read_manifest(task_dir).get("priorlock", {})
    canary = meta.get("canary", "")
    if not canary:
        return {"ok": False, "detail": "no canary planted", "agent_hits": [],
                "verifier_hits": []}

    def scan(root: Path) -> list[str]:
        hits = []
        if not root.is_dir():
            return hits
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                if canary in p.read_text(errors="ignore"):
                    hits.append(str(p.relative_to(task_dir)))
            except OSError:
                continue
        return hits

    agent_hits = scan(layout.environment)
    verifier_hits = scan(layout.tests)
    return {
        "ok": not agent_hits and bool(verifier_hits),
        "canary": canary,
        "agent_hits": agent_hits,
        "verifier_hits": verifier_hits,
        "detail": ("canary present verifier-side only"
                   if not agent_hits and verifier_hits
                   else f"canary reachable from the agent surface: {agent_hits}"
                   if agent_hits else "canary not found verifier-side either"),
    }
