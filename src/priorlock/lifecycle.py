"""Task lifecycle — preflight, baseline capture, and post-wrap health check.

The model here is deliberately the same one Harbor used for Terminal-Bench 1.0
tasks: **you don't author twice, you migrate.** A task is built and validated as
an ordinary Harbor task first. Only once it is known-good does it get converted.

    build → validate → oracle → calibrate → PREFLIGHT → wrap → gates → re-run → DOCTOR

`priorlock wrap` is the migration step. This module supplies the two checks that
bracket it:

``preflight``
    Runs *before* wrapping. Answers "is this host task actually healthy and
    wrap-ready?" — offline, no Docker. Catches the mistakes that would otherwise
    surface as a confusing gate failure twenty minutes later.

``doctor``
    Runs *after* wrapping and re-running. Answers "did wrapping damage the host
    task?" by comparing the post-wrap ``task_score`` against the oracle reward
    recorded at wrap time. This is the check that makes migration safe: without
    it, a wrap that quietly broke the original verifier would look like a model
    regression rather than a harness bug.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .inject import MANIFEST, detect_layout, is_wrapped, read_manifest

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Names `wrap` will write into the agent surface. A collision means the host task
# already owns that path and wrapping would clobber real content.
RESERVED_PATHS = (
    "probe_solution.py",
    "data/probe_input.json",
    "tests/test_probe_visible.py",
)
RESERVED_TESTS = ("probe_grade.py", "probe_input.json", "task_verify.sh",
                  "_plx_lib", "_plx_reference")


# ═════════════════════════════════════════════════════════════════════════════
#  Preflight
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class Check:
    id: str
    name: str
    ok: bool
    level: str          # "error" | "warn"
    detail: str = ""

    @property
    def blocking(self) -> bool:
        return not self.ok and self.level == "error"


@dataclass
class PreflightReport:
    task_id: str
    checks: list[Check] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not any(c.blocking for c in self.checks)

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and c.level == "warn"]

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "ready": self.ready,
            "checks": [
                {"id": c.id, "name": c.name, "ok": c.ok,
                 "level": c.level, "detail": c.detail}
                for c in self.checks
            ],
        }


_NETWORK_RE = re.compile(r'network_mode\s*=\s*["\']([^"\']+)["\']')
_SCHEMA_RE = re.compile(r'schema_version\s*=\s*["\']([^"\']+)["\']')


def preflight(task_dir: str | Path) -> PreflightReport:
    """Validate that a Harbor task is well-formed and safe to wrap. Offline."""
    layout = detect_layout(task_dir)
    root = layout.root
    checks: list[Check] = []

    def add(cid, name, ok, level="error", detail=""):
        checks.append(Check(cid, name, ok, level, detail))

    # ── P1 task.toml ─────────────────────────────────────────────────────────
    toml_ok = layout.task_toml is not None
    raw = layout.task_toml.read_text() if toml_ok else ""
    add("P1", "task.toml present", toml_ok,
        detail=str(layout.task_toml.relative_to(root)) if toml_ok else "missing task.toml")

    if toml_ok:
        m = _SCHEMA_RE.search(raw)
        add("P2", "schema_version declared", bool(m), "warn",
            f"schema_version = {m.group(1)}" if m else "not declared")
    else:
        add("P2", "schema_version declared", False, "warn", "no task.toml")

    # ── P3 instruction ───────────────────────────────────────────────────────
    instr = layout.instruction
    instr_ok = instr is not None and instr.is_file() and len(instr.read_text().strip()) > 40
    add("P3", "instruction file present", instr_ok,
        detail=(f"{instr.name} ({len(instr.read_text())} chars)" if instr and instr.is_file()
                else "no instruction.md / task.md found"))

    # ── P4 environment + Dockerfile ──────────────────────────────────────────
    dockerfiles = list(layout.environment.rglob("Dockerfile")) if layout.environment.is_dir() else []
    add("P4", "environment/ with Dockerfile", bool(dockerfiles),
        detail=(str(dockerfiles[0].relative_to(root)) if dockerfiles
                else "no Dockerfile under environment/"))

    # ── P5 agent workdir resolves ────────────────────────────────────────────
    repo_ok = layout.repo.is_dir()
    add("P5", "agent workdir resolves", repo_ok,
        detail=f"{layout.workdir} → {layout.repo.relative_to(root) if repo_ok else '?'}")

    # ── P6 verifier entrypoint ───────────────────────────────────────────────
    ver_ok = layout.verifier_entry is not None and layout.verifier_entry.is_file()
    add("P6", "verifier entrypoint present", ver_ok,
        detail=(str(layout.verifier_entry.relative_to(root)) if ver_ok
                else "no tests/test.sh or run-tests.sh"))

    # ── P7 verifier writes reward.json ───────────────────────────────────────
    if ver_ok:
        vtext = layout.verifier_entry.read_text()
        writes_reward = "reward.json" in vtext
        add("P7", "verifier writes reward.json", writes_reward, "error",
            "found reward.json reference" if writes_reward
            else "wrap composites on reward.json — the verifier must write it")
    else:
        add("P7", "verifier writes reward.json", False, "error", "no verifier")

    # ── P8 oracle solution present ───────────────────────────────────────────
    sol_dir = root / "solution"
    sol_files = [p for p in sol_dir.iterdir() if p.is_file()] if sol_dir.is_dir() else []
    add("P8", "oracle solution present", bool(sol_files), "warn",
        (", ".join(p.name for p in sol_files[:3]) if sol_files
         else "no solution/ — you cannot capture a baseline without one"))

    # ── P9 not already wrapped ───────────────────────────────────────────────
    add("P9", "not already wrapped", not is_wrapped(root),
        detail=("already wrapped — use --force to regenerate, or unwrap first"
                if is_wrapped(root) else "clean"))

    # ── P10 no path collisions ───────────────────────────────────────────────
    collisions = [p for p in RESERVED_PATHS if (layout.repo / p).exists()]
    collisions += [f"tests/{p}" for p in RESERVED_TESTS if (layout.tests / p).exists()]
    add("P10", "no reserved-path collisions", not collisions,
        detail="clean" if not collisions else "would clobber: " + ", ".join(collisions))

    # ── P11 network disabled ─────────────────────────────────────────────────
    net = _NETWORK_RE.search(raw)
    net_ok = bool(net) and net.group(1) == "no-network"
    add("P11", "network disabled", net_ok, "warn",
        f'network_mode = "{net.group(1)}"' if net
        else 'network_mode not set — recommend "no-network" so priors cannot be refreshed online')

    # ── P12 python available in image ────────────────────────────────────────
    py_ok = True
    if dockerfiles:
        dtext = "\n".join(d.read_text() for d in dockerfiles).lower()
        py_ok = "python" in dtext
    add("P12", "python present in image", py_ok, "warn",
        "python referenced in Dockerfile" if py_ok
        else "probe grader needs python3 in the verifier image")

    return PreflightReport(task_id=layout.task_id, checks=checks)


def print_preflight(report: PreflightReport) -> None:
    print(f"=== Preflight · {report.task_id} ===\n")
    for c in report.checks:
        if c.ok:
            mark = f"{GREEN}PASS{RESET}"
        elif c.level == "warn":
            mark = f"{YELLOW}WARN{RESET}"
        else:
            mark = f"{RED}FAIL{RESET}"
        print(f"{c.id:<4} {c.name:<32} {mark}  {DIM}{c.detail}{RESET}")

    print()
    if report.ready:
        warn = len(report.warnings)
        suffix = f" ({warn} warning{'s' if warn != 1 else ''})" if warn else ""
        print(f"{GREEN}READY TO WRAP{RESET}{suffix}")
    else:
        blocking = [c.id for c in report.checks if c.blocking]
        print(f"{RED}NOT READY{RESET}  blocking: {', '.join(blocking)}")


# ═════════════════════════════════════════════════════════════════════════════
#  Baseline capture
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class Baseline:
    reward: float
    agent: str
    trial: str
    task_checksum: str = ""
    captured_at: str = ""

    def to_toml(self) -> str:
        return "\n".join([
            "[baseline]",
            "# Oracle reward recorded BEFORE wrapping. `priorlock doctor` compares",
            "# the post-wrap task_score against this to prove wrapping did no harm.",
            f"reward = {self.reward}",
            f'agent = "{self.agent}"',
            f'trial = "{self.trial}"',
            f'task_checksum = "{self.task_checksum}"',
            f'captured_at = "{self.captured_at}"',
            "",
        ])


def find_baseline(trials_dir: str | Path, task_id: str | None = None,
                  agent: str = "oracle") -> Baseline | None:
    """Find the most recent successful `agent` run for `task_id` in a trials tree.

    Reads Harbor's ``result.json``: ``verifier_result.rewards.reward`` plus
    ``agent_info.name`` and ``task_checksum``.
    """
    root = Path(trials_dir)
    if not root.is_dir():
        return None

    best: Baseline | None = None
    best_time = ""
    for trial in sorted(p for p in root.iterdir() if p.is_dir()):
        result = trial / "result.json"
        if not result.is_file():
            continue
        try:
            data = json.loads(result.read_text())
        except json.JSONDecodeError:
            continue

        name = (data.get("agent_info") or {}).get("name", "")
        if agent and name != agent:
            continue
        if task_id and data.get("task_name") not in (task_id, None):
            continue

        rewards = (data.get("verifier_result") or {}).get("rewards") or {}
        if "reward" not in rewards:
            continue

        finished = data.get("finished_at", "") or ""
        if best is None or finished > best_time:
            best_time = finished
            best = Baseline(
                reward=float(rewards["reward"]),
                agent=name,
                trial=data.get("trial_name", trial.name),
                task_checksum=data.get("task_checksum", ""),
                captured_at=finished,
            )
    return best


def attach_baseline(task_dir: str | Path, baseline: Baseline) -> None:
    """Append or replace the ``[baseline]`` block in priorlock.toml."""
    path = Path(task_dir) / MANIFEST
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found — wrap the task first")
    text = path.read_text()
    if "[baseline]" in text:
        head, _, rest = text.partition("[baseline]")
        # drop the old block: everything up to the next top-level section
        after = ""
        for marker in ("\n[weights]", "\n[categories]", "\n[[probe]]", "\n[priorlock]"):
            idx = rest.find(marker)
            if idx != -1:
                after = rest[idx:]
                break
        text = head.rstrip() + "\n\n" + baseline.to_toml() + after
    else:
        text = text.rstrip() + "\n\n" + baseline.to_toml()
    path.write_text(text, encoding="utf-8")


# ═════════════════════════════════════════════════════════════════════════════
#  Doctor — post-wrap health check
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class DoctorReport:
    task_id: str
    baseline: float | None
    observed: float | None
    gap_score: float | None
    drift: float | None
    verdict: str
    notes: list[str] = field(default_factory=list)
    probes: list[dict] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return self.verdict == "healthy"

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "baseline": self.baseline,
            "observed_task_score": self.observed,
            "gap_score": self.gap_score,
            "drift": self.drift,
            "verdict": self.verdict,
            "healthy": self.healthy,
            "notes": self.notes,
            "probes": self.probes,
        }


def doctor(task_dir: str | Path, trials_dir: str | Path,
           tolerance: float = 1e-6) -> DoctorReport:
    """Compare the post-wrap oracle ``task_score`` against the recorded baseline.

    A healthy migration leaves ``task_score`` exactly where it was. Any drift
    means wrapping perturbed the host task — almost always a workdir or verifier
    path problem, not a model problem.
    """
    task_dir = Path(task_dir)
    manifest = read_manifest(task_dir)
    meta = manifest.get("priorlock", {})
    base_block = manifest.get("baseline", {})
    task_id = meta.get("task_id", task_dir.name)

    notes: list[str] = []
    baseline = float(base_block["reward"]) if "reward" in base_block else None
    if baseline is None:
        notes.append("no baseline recorded — capture one with "
                     "`priorlock wrap <task> --baseline-from <trials-dir>`")

    # find the newest post-wrap oracle run
    observed = gap = None
    probes: list[dict] = []
    root = Path(trials_dir)
    newest = ""
    if root.is_dir():
        for trial in sorted(p for p in root.iterdir() if p.is_dir()):
            summary = trial / "verifier" / "priorlock_summary.json"
            result = trial / "result.json"
            if not summary.is_file():
                continue
            finished = ""
            if result.is_file():
                try:
                    finished = json.loads(result.read_text()).get("finished_at", "") or ""
                except json.JSONDecodeError:
                    pass
            if finished < newest:
                continue
            try:
                data = json.loads(summary.read_text())
            except json.JSONDecodeError:
                continue
            newest = finished
            comps = data.get("components", {})
            observed = float(comps.get("task_score", 0.0))
            gap = float(comps.get("gap_score", 0.0))
            probes = data.get("probes", [])
            if data.get("flags"):
                notes.append("verifier flags: " + ", ".join(data["flags"]))

    if observed is None:
        notes.append("no post-wrap run found — run "
                     "`harbor trial start -p <task> -a oracle` after wrapping")
        return DoctorReport(task_id, baseline, None, None, None, "no-data", notes, probes)

    if baseline is None:
        return DoctorReport(task_id, None, observed, gap, None, "no-baseline", notes, probes)

    drift = round(observed - baseline, 6)
    if abs(drift) <= tolerance:
        verdict = "healthy"
        notes.append("task_score is unchanged — wrapping did not perturb the host task")
    elif drift < 0:
        verdict = "regressed"
        notes.append("task_score DROPPED after wrapping. Check the composite verifier's "
                     "workdir and that tests/task_verify.sh still resolves its paths.")
    else:
        verdict = "inflated"
        notes.append("task_score ROSE after wrapping, which should be impossible for an "
                     "oracle run. Check that the original verifier is actually executing.")

    return DoctorReport(task_id, baseline, observed, gap, drift, verdict, notes, probes)


def print_doctor(report: DoctorReport) -> None:
    print(f"=== Doctor · {report.task_id} ===\n")

    def fmt(v):
        return "—" if v is None else f"{v:.4f}"

    print(f"  baseline task_score  {fmt(report.baseline)}   "
          f"{DIM}(oracle, before wrapping){RESET}")
    print(f"  observed task_score  {fmt(report.observed)}   "
          f"{DIM}(oracle, after wrapping){RESET}")
    print(f"  drift                {fmt(report.drift)}")
    print(f"  gap_score            {fmt(report.gap_score)}   "
          f"{DIM}(prior-override, new signal){RESET}")

    if report.probes:
        print()
        for p in report.probes:
            print(f"    {p.get('id', '?'):<28} {p.get('verdict', '?'):<16} "
                  f"{p.get('score', 0):.2f}")

    colour = {"healthy": GREEN, "no-data": YELLOW,
              "no-baseline": YELLOW}.get(report.verdict, RED)
    print(f"\n{colour}{report.verdict.upper()}{RESET}")
    for note in report.notes:
        print(f"  {DIM}{note}{RESET}")
