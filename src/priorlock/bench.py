"""Zero-budget model benchmark — ``priorlock bench``.

Runs the standalone probes against any OpenAI-compatible chat model (a local
Ollama model, a hosted free tier, …) and grades every answer with the task's
own probe grader. No Harbor, no agent framework, no paid API required.

Three conditions separate *not knowing* from *not looking*:

``closed``
    The instruction only. The model cannot see the repository, so it writes
    from memory. This measures the prior: how often the memorized behaviour is
    what the model reaches for.
``open``
    The instruction plus every shipped doc pasted into the prompt. This is the
    ceiling: can the model act on documentation it has been handed?
``agentic``
    The instruction plus ``LIST`` / ``READ`` access to the agent-visible
    repository. Nothing is pasted in; the model has to decide to read the docs.
    This is the skill PriorLock rewards.
``agentic_uncued``
    The same, with the instruction's hints removed: no version tag, no pointer
    to ``docs/``, no bold on the required behaviour. Real tasks rarely announce
    the trap, so this is the harder and more realistic reading.
``agentic_docs_only``
    Uncued, and the library ships compiled: its folder holds a native binary
    and a one-line ``__init__.py``, so the code cannot be read. The CHANGELOG
    and API reference are the only places the change is written, as for many
    real packages. This separates agents that read documentation from agents
    that read code.

Every condition sees the task's input file, so a gap between conditions is not
about guessing the input layout.

The gap between ``open`` and ``agentic`` is the cost of not looking. The gap
between ``closed`` and ``open`` is how much the docs are worth at all.

Every model-written solution is graded inside a throwaway Docker container
with no network (``--sandbox docker``, the default when Docker is available),
so untrusted code never runs on the host.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .probes import BY_ID
from .standalone import generate

CONDITIONS = ("closed", "open", "agentic", "agentic_uncued", "agentic_docs_only")
NATIVE = "_native.cpython-311-x86_64-linux-gnu.so"

# Verdicts where the solution made the call the installed version requires.
# ``correct_call_bad_output`` used the new behaviour but mishandled the task's
# input/output plumbing, which is a different failure from prior lock.
RIGHT_CALL = ("override", "correct_call_bad_output")

PROVIDERS = {
    "ollama": ("http://localhost:11434/v1", None),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
}

# Neutral on purpose: no hint that the library changed or that docs matter.
SYSTEM = "You are a Python engineer. You write complete, working code."

FINAL_HINT = (
    "Reply with the complete contents of `{sol}` in a single ```python code "
    "block and nothing else after it."
)

AGENT_PROTOCOL = """\
You are at the root of the repository described above. You cannot run code, but
you can look at files. Each turn, reply with exactly one of:

  LIST <directory>     list a directory (use `.` for the root)
  READ <path>          show a file

When you are ready, reply with the complete contents of `{sol}` in a single
```python code block. You have at most {steps} turns."""

READ_LIMIT = 12_000
HIDDEN = (".priorlock",)


# ── model client ────────────────────────────────────────────────────────────

class QuotaExhausted(RuntimeError):
    """The endpoint's daily quota is used up; retrying today is pointless."""


@dataclass
class Model:
    """An OpenAI-compatible chat endpoint."""

    name: str
    base_url: str
    api_key: str | None = None
    rpm: float = 0.0            # requests per minute cap; 0 = unlimited
    max_tokens: int = 2048
    _last: float = field(default=0.0, repr=False)

    def chat(self, messages: list[dict]) -> str:
        if self.rpm:
            wait = 60.0 / self.rpm - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
        body = json.dumps({
            "model": self.name,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.max_tokens,
        }).encode()
        # Some gateways (Cloudflare) reject the default Python-urllib agent.
        headers = {"Content-Type": "application/json", "User-Agent": "priorlock-bench"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = self.base_url.rstrip("/") + "/chat/completions"
        for attempt in range(6):
            self._last = time.time()
            req = urllib.request.Request(url, data=body, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=600) as resp:
                    data = json.load(resp)
                return data["choices"][0]["message"].get("content") or ""
            except urllib.error.HTTPError as exc:
                err = exc.read()
                if exc.code == 429 and re.search(rb"per[ -]?day|PerDay", err, re.I):
                    raise QuotaExhausted(f"daily quota exhausted for {self.name}") from exc
                if exc.code in (429, 500, 502, 503) and attempt < 5:
                    time.sleep(min(60, 5 * 2 ** attempt))
                    continue
                raise RuntimeError(f"{exc.code} from {url}: {err[:300]!r}") from exc
        raise RuntimeError("unreachable")


def make_model(provider: str, name: str, *, base_url: str | None = None,
               api_key_env: str | None = None, rpm: float = 0.0) -> Model:
    default_url, default_env = PROVIDERS.get(provider, (None, None))
    url = base_url or default_url
    if not url:
        raise ValueError(f"unknown provider {provider!r}; pass --base-url")
    env = api_key_env or default_env
    key = os.environ.get(env) if env else None
    if env and not key:
        raise ValueError(f"set {env} for provider {provider!r}")
    return Model(name=name, base_url=url, api_key=key, rpm=rpm)


# ── task plan ───────────────────────────────────────────────────────────────

def probe_groups(size: int = 3) -> list[list[str]]:
    """Partition the coding catalog so every archetype appears exactly once."""
    ids = list(BY_ID)
    groups = [ids[i:i + size] for i in range(0, len(ids), size)]
    if len(groups) > 1 and len(groups[-1]) < size:
        groups[-2].extend(groups.pop())
    return groups


def _ladder_ok(task: Path) -> bool:
    """A task is usable only if it ships a CHANGELOG and its references score
    exactly gold 1.0, familiar 0.40."""
    from .standalone import grade
    if not list((task / "docs").glob("*CHANGELOG.md")):
        return False                     # the change must be findable in the docs
    try:
        return (grade(task, reference="gold")["gap_score"] == 1.0
                and abs(grade(task, reference="familiar")["gap_score"] - 0.4) < 1e-9)
    except Exception:
        return False


def build_tasks(out: Path, repeats: int, domains: list[str] | None = None,
                log=print) -> list[Path]:
    """Coding archetype tasks, plus one task per extra domain per repeat.

    Every task must pass its own reference ladder or it is left out, so a
    broken probe can never reach the results.
    """
    tasks = []
    for r in range(repeats):
        for g, ids in enumerate(probe_groups()):
            path = out / f"r{r}-g{g}"
            if not (path / ".priorlock").is_dir():
                generate(path, probe_ids=ids, seed=f"bench-r{r}-g{g}")
            tasks.append(path)
        for d in domains or []:
            path = out / f"r{r}-{d}"
            if not (path / ".priorlock").is_dir():
                generate(path, domains=[d], count=3, seed=f"bench-r{r}-{d}")
            if _ladder_ok(path):
                tasks.append(path)
            else:
                log(f"  skipped domain task {path.name}: reference ladder is not exact")
    return tasks


# ── prompting ───────────────────────────────────────────────────────────────

def _solution_name(task: Path) -> str:
    return json.loads((task / ".priorlock" / "manifest.json").read_text())["solution"]


def _docs(task: Path) -> str:
    parts = []
    for doc in sorted((task / "docs").glob("*.md")):
        parts.append(f"### docs/{doc.name}\n\n{doc.read_text()}")
    return "\n\n".join(parts)


def _input(task: Path) -> str:
    data = task / "data" / "probe_input.json"
    return f"### data/probe_input.json\n\n```json\n{data.read_text()}\n```"


def uncue(instruction: str) -> str:
    """Strip the hints a real task would not give: version tag, docs pointer, bold."""
    text = re.sub(r"\s*\(v\d+\)", "", instruction)
    text = re.sub(r"\s*There are docs in `[^`]+`(?: and usage examples in `utils/`)?\.", "", text)
    text = re.sub(r"\s*There are usage examples in `utils/`\.", "", text)
    return text.replace("**", "")


def _signatures(task: Path) -> str:
    """Probed function signatures with every default value hidden."""
    from .probes import BY_ID, all_probes_by_id
    from .probes.catalog_v2 import EXTENDED_BY_ID
    merged = {**BY_ID, **EXTENDED_BY_ID, **all_probes_by_id(None)}
    lib = _lib_dir(task)
    lines = []
    for pid in _probe_ids(task):
        sig = getattr(merged.get(pid), "signature", "") or ""
        sig = re.sub(r"=\s*(\"[^\"]*\"|'[^']*'|[^,)]+)", "=...", sig)
        if sig:
            lines.append(f"    {lib}.{sig}")
    return "\n".join(lines)


def _lib_dir(task: Path) -> str:
    return json.loads((task / ".priorlock" / "manifest.json").read_text())["lib"]


def extract_code(reply: str) -> str | None:
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", reply, re.S)
    if blocks:
        return blocks[-1]
    return None


def _visible(task: Path, rel: str) -> Path | None:
    """Resolve *rel* inside the agent-visible surface, or None."""
    target = (task / rel).resolve()
    try:
        parts = target.relative_to(task.resolve()).parts
    except ValueError:
        return None
    if parts and parts[0] in HIDDEN:
        return None
    return target if target.exists() else None


def _compiled_view(task: Path, target: Path, verb: str) -> str | None:
    """What a compiled library looks like from inside the repo, or None."""
    lib_dir = (task / _lib_dir(task)).resolve()
    if target != lib_dir and lib_dir not in target.parents:
        return None
    lib = lib_dir.name
    if verb == "LIST":
        return "__init__.py\n" + NATIVE if target == lib_dir else f"{target.name}: not a directory"
    if target.name == "__init__.py":
        return (f'"""{lib} 2.0.0."""\nfrom ._native import *  # compiled extension\n'
                f'__version__ = "2.0.0"\n')
    return f"{target.name}: binary file, cannot display"


def _act(task: Path, line: str, compiled: bool = False) -> tuple[str, str | None]:
    """Run one LIST/READ action. Returns (observation, path read or None)."""
    m = re.match(r"\s*(LIST|READ)\s+(\S+)", line)
    if not m:
        return ("Reply with LIST <dir>, READ <path>, or the final ```python block.", None)
    verb, rel = m.groups()
    lib_native = (task / _lib_dir(task) / NATIVE).resolve()
    target = _visible(task, rel)
    if target is None and compiled and (task / rel).resolve() == lib_native:
        target = lib_native
    if target is None:
        return (f"{rel}: no such file or directory", None)
    if compiled:
        view = _compiled_view(task, target, verb)
        if view is not None:
            return (view, str(target.relative_to(task.resolve())) if verb == "READ" else None)
    if verb == "LIST":
        if not target.is_dir():
            return (f"{rel}: not a directory", None)
        names = sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir()
                       if p.name not in HIDDEN and p.name != "__pycache__")
        return ("\n".join(names) or "(empty)", None)
    if target.is_dir():
        return (f"{rel}: is a directory", None)
    text = target.read_text(errors="replace")
    if len(text) > READ_LIMIT:
        text = text[:READ_LIMIT] + "\n… (truncated)"
    return (text, str(target.relative_to(task.resolve())))


def solve(model: Model, task: Path, condition: str, steps: int = 10) -> dict:
    if condition.startswith("repo_"):
        from .repo_v2 import STEPS, solve_v2
        return solve_v2(model, task, condition, max(steps, STEPS))
    instruction = (task / "instruction.md").read_text()
    sol = _solution_name(task)
    final = FINAL_HINT.format(sol=sol)
    read: list[str] = []
    turns = 0

    if condition == "closed":
        prompt = (f"{instruction}\n\nYou do not have access to the repository's docs "
                  f"or library source. The library's signatures (defaults hidden):\n\n"
                  f"```python\n{_signatures(task)}\n```\n\nThe input file is:\n\n"
                  f"{_input(task)}\n\n{final}")
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt}]
        reply, turns = model.chat(messages), 1
    elif condition == "open":
        prompt = (f"{instruction}\n\nThe input file and the repository's documentation "
                  f"follow.\n\n{_input(task)}\n\n{_docs(task)}\n\n{final}")
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt}]
        reply, turns = model.chat(messages), 1
    elif condition in ("agentic", "agentic_uncued", "agentic_docs_only"):
        text = instruction if condition == "agentic" else uncue(instruction)
        compiled = condition == "agentic_docs_only"
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"{text}\n\nThe input file is:\n\n"
                     f"{_input(task)}\n\n" + AGENT_PROTOCOL.format(sol=sol, steps=steps)}]
        reply = ""
        while turns < steps:
            reply = model.chat(messages)
            turns += 1
            if extract_code(reply) is not None:
                break
            obs, path = _act(task, reply.strip().splitlines()[0] if reply.strip() else "",
                             compiled=compiled)
            if path:
                read.append(path)
            messages += [{"role": "assistant", "content": reply},
                         {"role": "user", "content": obs}]
    else:
        raise ValueError(f"unknown condition {condition!r}")

    return {"reply": reply, "code": extract_code(reply), "turns": turns, "read": read}


# ── grading ─────────────────────────────────────────────────────────────────

def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def grade_code(task: Path, code: str, sandbox: str, image: str) -> dict:
    """Grade *code* against a private copy of *task*."""
    with tempfile.TemporaryDirectory(prefix="plbench-") as tmp:
        work = Path(tmp) / "task"
        shutil.copytree(task, work)
        (work / _solution_name(task)).write_text(code)
        if sandbox == "docker":
            cmd = ["docker", "run", "--rm", "-i", "--network", "none", "--memory", "512m",
                   "-v", f"{work}:/task", image, "python",
                   "/task/.priorlock/probe_grade.py",
                   "--submission", "/task", "--tests-dir", "/task/.priorlock"]
        else:
            cmd = [sys.executable, str(work / ".priorlock" / "probe_grade.py"),
                   "--submission", str(work), "--tests-dir", str(work / ".priorlock")]
        from .grading import run_grader
        try:
            report, res = run_grader(cmd, timeout=120)
        except subprocess.TimeoutExpired:
            return {"gap_score": 0.0, "probes": [], "error": "grader timeout"}
        if report is None:
            return {"gap_score": 0.0, "probes": [],
                    "error": (res.stderr or res.stdout)[-500:]}
        return report


# ── run + summarise ─────────────────────────────────────────────────────────

def run_bench(model: Model, tasks: list[Path], conditions: list[str], out_file: Path,
              *, sandbox: str, image: str, steps: int = 10, log=print) -> None:
    """Append one JSON line per (task, condition) to *out_file*; resumable."""
    done = set()
    if out_file.exists():
        for line in out_file.read_text().splitlines():
            r = json.loads(line)
            done.add((r["model"], r["task"], r["condition"]))
    with out_file.open("a") as fh:
        for task in tasks:
            for cond in conditions:
                key = (model.name, task.name, cond)
                if key in done:
                    continue
                t0 = time.time()
                try:
                    out = solve(model, task, cond, steps)
                    error = None
                except QuotaExhausted as exc:
                    log(f"  {model.name}: {exc}; stopping this model, unfinished cells retry later")
                    return
                except Exception as exc:
                    # An endpoint failure (quota, missing model, network) says
                    # nothing about the model's behaviour: record nothing, so a
                    # later run retries the cell.
                    log(f"  {model.name:<24} {task.name:<7} {cond:<8} skipped: {str(exc)[:120]}")
                    continue
                if out["code"] is None:
                    report = {"gap_score": 0.0, "probes": []}
                    verdicts = {pid: "no_answer" for pid in _probe_ids(task)}
                else:
                    report = grade_code(task, out["code"], sandbox, image)
                    verdicts = {p["id"]: p["verdict"] for p in report.get("probes", [])}
                    for pid in _probe_ids(task):
                        verdicts.setdefault(pid, "crashed")
                lib = _lib_dir(task)
                rec = {
                    "model": model.name, "task": task.name, "condition": cond,
                    "gap_score": report.get("gap_score", 0.0), "verdicts": verdicts,
                    "read": out["read"], "turns": out["turns"],
                    "read_docs": out.get("info_seen",
                                         any(p.startswith("docs/") for p in out["read"])),
                    "read_source": any(p.startswith(f"{lib}/") for p in out["read"]),
                    "code": out["code"],
                    "error": error or report.get("error"),
                    "seconds": round(time.time() - t0, 1),
                }
                for extra in ("greps", "runs", "actions", "replies"):
                    if extra in out:
                        rec[extra] = out[extra]
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                log(f"  {model.name:<24} {task.name:<7} {cond:<8} "
                    f"gap={rec['gap_score']:.2f}  "
                    + " ".join(sorted(set(verdicts.values())))
                    + ("  [read docs]" if rec["read_docs"] else "")
                    + ("  [read source]" if rec["read_source"] else ""))


def _probe_ids(task: Path) -> list[str]:
    m = json.loads((task / ".priorlock" / "manifest.json").read_text())
    return [p["id"] for p in m["probes"]]


def _family(pid: str) -> str:
    from .probes import BY_ID, all_probes_by_id
    from .probes.catalog_v2 import EXTENDED_BY_ID
    probe = {**BY_ID, **EXTENDED_BY_ID, **all_probes_by_id(None)}.get(pid)
    return probe.family if probe else "?"


def cluster_ci(per_arch: dict[str, tuple[int, int]], iters: int = 4000,
               seed: int = 0) -> tuple[float, float]:
    """95% bootstrap interval that resamples archetypes, not probes.

    Repeats of one archetype are correlated (same behaviour change, renamed),
    so the archetype is the unit of resampling.
    """
    import random
    arch = list(per_arch.values())
    if not arch:
        return (0.0, 0.0)
    rng = random.Random(seed)
    rates = []
    for _ in range(iters):
        sample = [arch[rng.randrange(len(arch))] for _ in arch]
        n = sum(x[1] for x in sample)
        rates.append(sum(x[0] for x in sample) / n if n else 0.0)
    rates.sort()
    return (rates[int(0.025 * iters)], rates[int(0.975 * iters) - 1])


def summarise(records: list[dict]) -> dict:
    """Per (model, condition): verdict rates with archetype-clustered 95% intervals."""
    out: dict = {}
    for r in records:
        cell = out.setdefault(r["model"], {}).setdefault(r["condition"], {
            "probes": 0, "verdicts": {}, "tasks": 0, "read_docs": 0, "read_source": 0,
            "grounded": 0, "arch": {}, "family": {}})
        cell["tasks"] += 1
        cell["read_docs"] += int(r.get("read_docs", False))
        cell["read_source"] += int(r.get("read_source", False))
        cell["grounded"] += int(r.get("read_docs", False) or r.get("read_source", False))
        for pid, v in r["verdicts"].items():
            cell["probes"] += 1
            cell["verdicts"][v] = cell["verdicts"].get(v, 0) + 1
            cell["arch"].setdefault(pid, []).append(v)
            fam = cell["family"].setdefault(_family(pid), {"n": 0, "right_call": 0, "prior_locked": 0})
            fam["n"] += 1
            fam["right_call"] += int(v in RIGHT_CALL)
            fam["prior_locked"] += int(v == "prior_locked")
    for conds in out.values():
        for cell in conds.values():
            arch = cell.pop("arch")
            n = cell["probes"]
            groups = {"override": ("override",), "prior_locked": ("prior_locked",),
                      "right_call": RIGHT_CALL}
            for name, verdicts in groups.items():
                per = {pid: (sum(v in verdicts for v in vs), len(vs)) for pid, vs in arch.items()}
                k = sum(x[0] for x in per.values())
                lo, hi = cluster_ci(per)
                cell[name] = {"k": k, "n": n, "rate": k / n if n else 0.0,
                              "ci95": [round(lo, 3), round(hi, 3)]}
            cell["archetypes"] = len(arch)
    return out


def report_markdown(records: list[dict]) -> str:
    summary = summarise(records)
    pct = lambda c: f"{c['rate']:.0%} [{c['ci95'][0]:.0%}, {c['ci95'][1]:.0%}]"
    lines = ["| Model | Condition | Probes | Opened docs / source | Prior-locked "
             "(memorized behaviour) | Right call (installed behaviour) | "
             "Fully correct | Other |",
             "|---|---|---|---|---|---|---|---|"]
    for model, conds in summary.items():
        for cond in CONDITIONS:
            c = conds.get(cond)
            if not c:
                continue
            pl, rc, ov = c["prior_locked"], c["right_call"], c["override"]
            other = c["probes"] - pl["k"] - rc["k"]
            read = (f"{c['read_docs']} / {c['read_source']} of {c['tasks']} tasks"
                    if cond.startswith("agentic") else "—")
            lines.append(f"| {model} | {cond} | {c['probes']} | {read} | {pct(pl)} | "
                         f"{pct(rc)} | {pct(ov)} | {other} |")
    lines += ["", "Right call by probe family (prior-locked in brackets):", "",
              "| Model | Condition | default_flip | value_remap | result_shape |",
              "|---|---|---|---|---|"]
    for model, conds in summary.items():
        for cond in CONDITIONS:
            c = conds.get(cond)
            if not c:
                continue
            cells = []
            for fam in ("default_flip", "value_remap", "result_shape"):
                f = c["family"].get(fam)
                cells.append(f"{f['right_call']}/{f['n']} ({f['prior_locked']})" if f else "—")
            lines.append(f"| {model} | {cond} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def load_records(paths: list[Path]) -> list[dict]:
    recs = []
    for p in paths:
        recs += [json.loads(line) for line in Path(p).read_text().splitlines() if line.strip()]
    return recs
