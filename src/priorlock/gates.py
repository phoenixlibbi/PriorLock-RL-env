"""Stage-0 offline gates for wrapped tasks.

Runs with no Docker, no network, and no API key. Everything here executes the
*generated* grader against *generated* reference solutions, so it validates the
artefact that will actually run in the container rather than a model of it.

Gate suite
----------
============  ==========================================================
G1 gold       a doc-reading solution scores exactly 1.0
G2 familiar   a prior-locked solution scores exactly 0.40
G3 stub       a solution that raises scores 0.0
G4 ladder     0.0 < 0.40 < 1.0, strictly
G5 visible    shape-only smoke tests pass for BOTH gold and familiar
G6 canary     no verifier asset is reachable from the agent surface
G7 bypass     hand-rolling the familiar answer scores 0.0, not 0.40
G8 tamper     editing the shipped library is flagged and changes no score
G9 discrim    every individual probe separates gold from familiar
============  ==========================================================

G7 and G8 are the anti-reward-hacking gates and are the reason a wrapped task
cannot be farmed. G7 makes bypassing the library strictly worse than using it
naively; G8 makes editing the library pointless because the verifier grades
against its own pristine copy.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .inject import (
    INPUT_REL,
    PRISTINE_DIR,
    REFERENCE_DIR,
    SOLUTION_NAME,
    detect_layout,
    is_wrapped,
    read_manifest,
)
from .probes.base import FAMILIAR_BASELINE

EPS = 1e-6

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"


@dataclass
class GateResult:
    id: str
    name: str
    passed: bool
    detail: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class Stage0Report:
    task_id: str
    library: str
    probes: list[str]
    gates: list[GateResult] = field(default_factory=list)
    scores: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(g.passed for g in self.gates)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "library": self.library,
            "probes": self.probes,
            "passed": self.passed,
            "scores": self.scores,
            "gates": [
                {"id": g.id, "name": g.name, "passed": g.passed,
                 "detail": g.detail, "data": g.data}
                for g in self.gates
            ],
        }


# ═════════════════════════════════════════════════════════════════════════════
#  Sandbox construction
# ═════════════════════════════════════════════════════════════════════════════

class _Sandbox:
    """An isolated copy of a wrapped task's repo + tests, for one grading run."""

    def __init__(self, layout, keep: bool = False):
        self.tmp = Path(tempfile.mkdtemp(prefix="plx-stage0-"))
        self.keep = keep
        self.submission = self.tmp / "submission"
        self.tests = self.tmp / "tests"
        shutil.copytree(layout.repo, self.submission, dirs_exist_ok=True)
        shutil.copytree(layout.tests, self.tests, dirs_exist_ok=True)

    def install_solution(self, source: Path | str, name: str = SOLUTION_NAME) -> None:
        target = self.submission / name
        if isinstance(source, Path) and source.is_file():
            shutil.copy2(source, target)
        else:
            target.write_text(str(source), encoding="utf-8")

    def run_grader(self) -> dict:
        grader = self.tests / "probe_grade.py"
        proc = subprocess.run(
            [sys.executable, str(grader),
             "--submission", str(self.submission),
             "--tests-dir", str(self.tests)],
            capture_output=True, text=True, timeout=180,
        )
        if not proc.stdout.strip():
            return {"gap_score": 0.0, "probes": [],
                    "flags": ["grader_no_output"], "stderr": proc.stderr[-800:]}
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"gap_score": 0.0, "probes": [],
                    "flags": ["grader_bad_json"], "stdout": proc.stdout[-800:]}

    def run_visible_tests(self) -> tuple[bool, str]:
        test_file = self.submission / "tests" / "test_probe_visible.py"
        if not test_file.is_file():
            return False, "test_probe_visible.py missing"
        env = dict(os.environ)
        env["PYTHONPATH"] = str(self.submission) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q", "--no-header"],
            capture_output=True, text=True, cwd=str(self.submission),
            env=env, timeout=180,
        )
        return proc.returncode == 0, (proc.stdout or proc.stderr)[-600:]

    def cleanup(self) -> None:
        if not self.keep:
            shutil.rmtree(self.tmp, ignore_errors=True)


def _grade_variant(layout, variant: str) -> dict:
    """Run the generated grader against a generated reference solution."""
    ref = layout.tests / REFERENCE_DIR / f"{variant}.py"
    sb = _Sandbox(layout)
    try:
        if ref.is_file():
            sb.install_solution(ref)
        return sb.run_grader()
    finally:
        sb.cleanup()


# ═════════════════════════════════════════════════════════════════════════════
#  Gates
# ═════════════════════════════════════════════════════════════════════════════

def run_stage0(task_dir: str | Path, verbose: bool = True) -> Stage0Report:
    task_dir = Path(task_dir).resolve()
    if not is_wrapped(task_dir):
        raise RuntimeError(
            f"{task_dir.name} is not wrapped. Run `priorlock wrap {task_dir}` first."
        )
    layout = detect_layout(task_dir)
    manifest = read_manifest(task_dir)
    meta = manifest.get("priorlock", {})
    probe_ids = [p.get("id", "?") for p in manifest.get("probe", [])]

    report = Stage0Report(
        task_id=meta.get("task_id", layout.task_id),
        library=meta.get("library", "?"),
        probes=probe_ids,
    )

    # ── G1 / G2 / G3 / G7 — score the four reference solutions ───────────────
    gold = _grade_variant(layout, "gold")
    familiar = _grade_variant(layout, "familiar")
    stub = _grade_variant(layout, "stub")
    bypass = _grade_variant(layout, "bypass")

    g = float(gold.get("gap_score", 0.0))
    f = float(familiar.get("gap_score", 0.0))
    s = float(stub.get("gap_score", 0.0))
    b = float(bypass.get("gap_score", 0.0))
    report.scores = {"gold": g, "familiar": f, "stub": s, "bypass": b}

    report.gates.append(GateResult(
        "G1", "gold score", abs(g - 1.0) < EPS,
        f"gap_score={g}", {"verdicts": gold.get("verdict_counts", {}),
                           "flags": gold.get("flags", [])},
    ))
    report.gates.append(GateResult(
        "G2", "familiar score", abs(f - FAMILIAR_BASELINE) < EPS,
        f"gap_score={f} (want {FAMILIAR_BASELINE})",
        {"verdicts": familiar.get("verdict_counts", {}),
         "flags": familiar.get("flags", [])},
    ))
    report.gates.append(GateResult(
        "G3", "stub score", abs(s) < EPS, f"gap_score={s}",
        {"flags": stub.get("flags", [])},
    ))
    report.gates.append(GateResult(
        "G4", "strict ladder", s < f < g, f"{s} < {f} < {g}",
    ))

    # ── G5 — visible tests must not discriminate ─────────────────────────────
    vis_results = {}
    for variant in ("gold", "familiar"):
        ref = layout.tests / REFERENCE_DIR / f"{variant}.py"
        sb = _Sandbox(layout)
        try:
            sb.install_solution(ref)
            ok, out = sb.run_visible_tests()
            vis_results[variant] = {"passed": ok, "output": out}
        finally:
            sb.cleanup()
    g5_ok = all(v["passed"] for v in vis_results.values())
    report.gates.append(GateResult(
        "G5", "visible tests non-discriminating", g5_ok,
        " ".join(f"{k}={'pass' if v['passed'] else 'FAIL'}" for k, v in vis_results.items()),
        vis_results,
    ))

    # ── G6 — canary: no verifier asset on the agent surface ──────────────────
    leaks = _canary(layout)
    report.gates.append(GateResult(
        "G6", "canary clean", not leaks,
        "no oracle assets in environment/" if not leaks else f"{len(leaks)} leak(s)",
        {"leaks": leaks},
    ))

    # ── G7 — bypassing the library must score 0.0, not 0.40 ──────────────────
    bypass_verdicts = bypass.get("verdict_counts", {})
    g7_ok = abs(b) < EPS and bypass_verdicts.get("bypassed", 0) == len(probe_ids)
    report.gates.append(GateResult(
        "G7", "bypass scores zero", g7_ok,
        f"gap_score={b} verdicts={bypass_verdicts}",
        {"verdicts": bypass_verdicts},
    ))

    # ── G8 — tampering is detected and cannot change the score ───────────────
    tamper = _tamper_check(layout)
    report.gates.append(GateResult(
        "G8", "tamper-proof grading", tamper["ok"],
        f"score={tamper['score']} flags={tamper['flags']}", tamper,
    ))

    # ── G9 — every probe individually discriminates ──────────────────────────
    dead = _dead_probes(gold, familiar, probe_ids)
    report.gates.append(GateResult(
        "G9", "all probes discriminate", not dead,
        "every probe separates gold from familiar" if not dead
        else f"non-discriminating: {', '.join(dead)}",
        {"dead": dead},
    ))

    if verbose:
        _print(report)
    return report


def _canary(layout) -> list[str]:
    """Verifier-only assets that must never be reachable from environment/."""
    forbidden_files = {
        "probe_grade.py", "probe_expected.json", "expected.json", "grade.py",
        "gold.py", "familiar.py", "bypass.py", "task_verify.sh",
    }
    forbidden_dirs = {PRISTINE_DIR, REFERENCE_DIR}
    leaks: list[str] = []
    env = layout.environment
    if not env.is_dir():
        return leaks
    for root, dirs, files in os.walk(env):
        rel_root = Path(root).relative_to(env)
        for d in list(dirs):
            if d in forbidden_dirs:
                leaks.append(str(rel_root / d) + "/")
        for fn in files:
            if fn in forbidden_files:
                leaks.append(str(rel_root / fn))
    return leaks


def _tamper_check(layout) -> dict:
    """Rewrite the shipped library to return the familiar answers, then grade gold.

    A correct harness ignores the agent's copy entirely: the score must stay 1.0
    and the run must carry a ``library_modified`` flag.
    """
    meta = read_manifest(layout.root).get("priorlock", {})
    lib = meta.get("library", "")
    ref = layout.tests / REFERENCE_DIR / "gold.py"
    sb = _Sandbox(layout)
    try:
        sb.install_solution(ref)
        target = sb.submission / lib / "__init__.py"
        if target.is_file():
            original = target.read_text()
            target.write_text(
                original + "\n\n# tampered by Stage-0 G8\n_PLX_TAMPERED = True\n"
            )
        result = sb.run_grader()
        score = float(result.get("gap_score", 0.0))
        flags = result.get("flags", [])
        return {
            "ok": abs(score - 1.0) < EPS and "library_modified" in flags,
            "score": score,
            "flags": flags,
        }
    finally:
        sb.cleanup()


def _dead_probes(gold: dict, familiar: dict, probe_ids: list[str]) -> list[str]:
    """Probes that failed to separate the two reference solutions."""
    gmap = {p["id"]: p for p in gold.get("probes", [])}
    fmap = {p["id"]: p for p in familiar.get("probes", [])}
    dead: list[str] = []
    for pid in probe_ids:
        gp, fp = gmap.get(pid), fmap.get(pid)
        if not gp or not fp:
            dead.append(pid)
            continue
        if gp["verdict"] != "override" or fp["verdict"] != "prior_locked":
            dead.append(pid)
    return dead


# ═════════════════════════════════════════════════════════════════════════════
#  Reporting
# ═════════════════════════════════════════════════════════════════════════════

def _print(report: Stage0Report) -> None:
    print(f"=== Stage-0 · {report.task_id} ===")
    print(f"{DIM}library {report.library} · probes: {', '.join(report.probes)}{RESET}\n")
    for gate in report.gates:
        mark = f"{GREEN}PASS{RESET}" if gate.passed else f"{RED}FAIL{RESET}"
        print(f"{gate.id} {gate.name:<34} {mark}  {DIM}{gate.detail}{RESET}")
        if not gate.passed and gate.data:
            snippet = json.dumps(gate.data, ensure_ascii=False)[:400]
            print(f"   {DIM}{snippet}{RESET}")
    print()
    scores = report.scores
    print(f"ladder  stub {scores.get('stub')}  bypass {scores.get('bypass')}  "
          f"familiar {scores.get('familiar')}  gold {scores.get('gold')}")
    print(f"\n{GREEN if report.passed else RED}"
          f"{'ALL GATES PASS' if report.passed else 'SOME GATES FAILED'}{RESET}")
