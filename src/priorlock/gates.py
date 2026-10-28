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
G10 host      the task's original verifier survived migration intact
G11 oracle    the shipped oracle actually scores 1.0 on the probes
G12 canary    the oracle-exclusive canary never reaches the agent surface
============  ==========================================================

G7 and G8 are the anti-reward-hacking gates (the cheat battery covers the rest).
G7 makes bypassing the library strictly worse than using it
naively; G8 makes editing the library pointless because the verifier grades
against its own pristine copy.
"""
from __future__ import annotations

import hashlib
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
from . import progress

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
        # cwd MUST be the sandbox. Cheat solutions deliberately write to
        # relative paths ("probe_details.json", "../tests/probe_grade.py") to
        # test grader tampering; without a contained cwd those land in whatever
        # directory the harness happened to be invoked from — i.e. the user's
        # repo. Observed: probe_details.json appearing at the repo root.
        from .grading import run_grader
        report, proc = run_grader(
            [sys.executable, str(grader),
             "--submission", str(self.submission),
             "--tests-dir", str(self.tests)],
            timeout=180, cwd=str(self.tmp),
        )
        if report is None:
            return {"gap_score": 0.0, "probes": [], "flags": ["grader_no_report"],
                    "stdout": proc.stdout[-800:], "stderr": proc.stderr[-800:]}
        return report

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
    """Run all ten gates, reporting each one live as it completes.

    Every gate here spawns subprocesses — four reference gradings, two pytest
    runs and a tamper re-grade. That is tens of seconds of silence if results
    are batched to the end, which reads as a hang. Each gate therefore announces
    itself before it starts and prints its own result with an elapsed time.
    """
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

    if verbose:
        print(f"=== Stage-0 · {report.task_id} ===")
        print(f"{DIM}library {report.library} · {len(probe_ids)} probes: "
              f"{', '.join(probe_ids)}{RESET}")
        print(f"{DIM}12 gates · no Docker, no network, no API key{RESET}\n")

    total = 12
    n = [0]

    def gate(gid: str, name: str):
        """Context manager yielding a setter for one gate's result."""
        n[0] += 1
        label = f"{gid:<4}{name}"
        if verbose:
            return progress.Step(f"[{n[0]:>2}/{total}] {label}", width=42)
        return _NullStep()

    def record(gid, name, ok, detail, data=None) -> GateResult:
        r = GateResult(gid, name, ok, detail, data or {})
        report.gates.append(r)
        return r

    # ── G1 / G2 / G3 / G7 — score the four reference solutions ───────────────
    # Grade all four up front (they share setup cost), but announce each.
    with gate("G1", "gold score") as st:
        gold = _grade_variant(layout, "gold")
        g = float(gold.get("gap_score", 0.0))
        ok = abs(g - 1.0) < EPS
        record("G1", "gold score", ok, f"gap_score={g}",
               {"verdicts": gold.get("verdict_counts", {}), "flags": gold.get("flags", [])})
        st.done(ok, f"gap_score={g}  (want 1.0)")

    with gate("G2", "familiar score") as st:
        familiar = _grade_variant(layout, "familiar")
        f = float(familiar.get("gap_score", 0.0))
        ok = abs(f - FAMILIAR_BASELINE) < EPS
        record("G2", "familiar score", ok, f"gap_score={f} (want {FAMILIAR_BASELINE})",
               {"verdicts": familiar.get("verdict_counts", {}),
                "flags": familiar.get("flags", [])})
        st.done(ok, f"gap_score={f}  (want {FAMILIAR_BASELINE})")

    with gate("G3", "stub score") as st:
        stub = _grade_variant(layout, "stub")
        s = float(stub.get("gap_score", 0.0))
        ok = abs(s) < EPS
        record("G3", "stub score", ok, f"gap_score={s}", {"flags": stub.get("flags", [])})
        st.done(ok, f"gap_score={s}  (want 0.0)")

    with gate("G4", "strict ladder") as st:
        ok = s < f < g
        record("G4", "strict ladder", ok, f"{s} < {f} < {g}")
        st.done(ok, f"{s} < {f} < {g}")

    report.scores = {"gold": g, "familiar": f, "stub": s, "bypass": 0.0}

    # ── G5 — visible tests must not discriminate ─────────────────────────────
    with gate("G5", "visible tests non-discriminating") as st:
        vis_results = {}
        for variant in ("gold", "familiar"):
            ref = layout.tests / REFERENCE_DIR / f"{variant}.py"
            sb = _Sandbox(layout)
            try:
                sb.install_solution(ref)
                passed, out = sb.run_visible_tests()
                vis_results[variant] = {"passed": passed, "output": out}
            finally:
                sb.cleanup()
        ok = all(v["passed"] for v in vis_results.values())
        detail = " ".join(f"{k}={'pass' if v['passed'] else 'FAIL'}"
                          for k, v in vis_results.items())
        record("G5", "visible tests non-discriminating", ok, detail, vis_results)
        st.done(ok, detail)

    # ── G6 — canary: no verifier asset on the agent surface ──────────────────
    with gate("G6", "canary clean") as st:
        leaks = _canary(layout)
        ok = not leaks
        detail = "no oracle assets in environment/" if ok else f"{len(leaks)} leak(s)"
        record("G6", "canary clean", ok, detail, {"leaks": leaks})
        st.done(ok, detail)

    # ── G7 — bypassing the library must score 0.0, not 0.40 ──────────────────
    with gate("G7", "bypass scores zero") as st:
        bypass = _grade_variant(layout, "bypass")
        b = float(bypass.get("gap_score", 0.0))
        report.scores["bypass"] = b
        verdicts = bypass.get("verdict_counts", {})
        ok = abs(b) < EPS and verdicts.get("bypassed", 0) == len(probe_ids)
        detail = f"gap_score={b} verdicts={verdicts}"
        record("G7", "bypass scores zero", ok, detail, {"verdicts": verdicts})
        st.done(ok, detail)

    # ── G8 — tampering is detected and cannot change the score ───────────────
    with gate("G8", "tamper-proof grading") as st:
        tamper = _tamper_check(layout)
        detail = f"score={tamper['score']} flags={tamper['flags']}"
        record("G8", "tamper-proof grading", tamper["ok"], detail, tamper)
        st.done(tamper["ok"], detail)

    # ── G9 — every probe individually discriminates ──────────────────────────
    with gate("G9", "all probes discriminate") as st:
        dead = _dead_probes(gold, familiar, probe_ids)
        ok = not dead
        detail = ("every probe separates gold from familiar" if ok
                  else f"non-discriminating: {', '.join(dead)}")
        record("G9", "all probes discriminate", ok, detail, {"dead": dead})
        st.done(ok, detail)

    # ── G10 — the host task survived migration intact ────────────────────────
    with gate("G10", "host task preserved") as st:
        host = _host_preserved(layout, meta)
        record("G10", "host task preserved", host["ok"], host["detail"], host)
        st.done(host["ok"], host["detail"])

    # ── G11 — the shipped oracle actually solves the probes ──────────────────
    with gate("G11", "oracle solves the probes") as st:
        oracle = _oracle_solves_probes(layout)
        record("G11", "oracle solves the probes", oracle["ok"], oracle["detail"], oracle)
        st.done(oracle["ok"], oracle["detail"])

    # ── G12 — the oracle canary never reaches the agent surface ──────────────
    # The offline half of the canary check. It scans file contents rather than
    # filenames, so it catches a leak G6 cannot see. It is not a runtime proof;
    # `priorlock leakprobe` produces that.
    with gate("G12", "oracle canary contained") as st:
        from .leakprobe import canary_scan
        scan = canary_scan(task_dir)
        record("G12", "oracle canary contained", scan["ok"], scan["detail"], scan)
        st.done(scan["ok"], scan["detail"])

    if verbose:
        _summary(report)
    return report


class _NullStep:
    """No-op Step used when verbose=False (CI matrices, --json)."""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def done(self, *a, **k):
        pass

    def note(self, *a, **k):
        pass


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


def _host_preserved(layout, meta: dict) -> dict:
    """G10: wrapping must not damage or drop the task's original verifier.

    Three things must hold for a migration to be non-destructive:
      1. the original verifier was copied aside byte-identically
      2. the composite entrypoint actually invokes it
      3. the composite runs it FIRST, so task_score is captured before probes
    """
    original = meta.get("original_verifier", "")
    expected_sha = meta.get("original_verifier_sha256", "")

    if not original:
        # a task that shipped no verifier is legal — nothing to preserve
        return {"ok": True, "detail": "host task had no verifier to preserve",
                "original": None}

    saved = layout.tests / original
    if not saved.is_file():
        return {"ok": False, "detail": f"{original} missing — original verifier was lost",
                "original": original}

    actual_sha = hashlib.sha256(saved.read_bytes()).hexdigest()
    if expected_sha and actual_sha != expected_sha:
        return {"ok": False, "detail": f"{original} was modified after wrapping",
                "original": original, "expected": expected_sha[:12],
                "actual": actual_sha[:12]}

    entry = layout.verifier_entry or (layout.tests / "test.sh")
    if not entry.is_file():
        return {"ok": False, "detail": "composite entrypoint missing",
                "original": original}

    composite = entry.read_text()
    if original not in composite:
        return {"ok": False, "detail": f"composite never invokes {original}",
                "original": original}

    # ordering: the original verifier must run before the probe grader, or its
    # reward.json would be overwritten before we read it
    pos_original = composite.find(original)
    pos_probe = composite.find("probe_grade.py")
    if pos_probe != -1 and pos_original > pos_probe:
        return {"ok": False, "detail": "probe grader runs before the host verifier",
                "original": original}

    return {"ok": True,
            "detail": f"{original} preserved byte-identical and invoked first",
            "original": original, "sha256": actual_sha[:12]}


def _oracle_solves_probes(layout) -> dict:
    """G11: the oracle Harbor will actually run must score 1.0 on the probes.

    Everything the wrapped task ships — the library, the CHANGELOG, the gold
    call arguments — is generated from the same ``Probe`` objects, so in
    principle they cannot disagree. That is an argument, not evidence. This gate
    turns it into evidence: extract the gold solution **as embedded in
    ``solution/solve.sh``** (not the copy in ``_plx_reference/``) and grade it.

    Without this, a stale or mis-rendered oracle patch would ship silently:
    G1 grades ``_plx_reference/gold.py``, which is a different file.
    """
    from .inject import _find_oracle
    from . import templates as T

    solve = _find_oracle(layout)
    if solve is None or not solve.is_file():
        return {"ok": True, "detail": "task ships no oracle — nothing to check",
                "skipped": True}

    text = solve.read_text()
    if T.SOLUTION_MARKER_BEGIN not in text:
        return {"ok": False, "detail": "oracle was never patched — it cannot score 1.0"}

    marker = "<<'PRIORLOCK_GOLD_EOF'\n"
    if marker not in text or "\nPRIORLOCK_GOLD_EOF" not in text:
        return {"ok": False, "detail": "cannot extract the embedded gold solution"}
    embedded = text.split(marker, 1)[1].split("\nPRIORLOCK_GOLD_EOF", 1)[0]

    sb = _Sandbox(layout)
    try:
        sb.install_solution(embedded + "\n")
        result = sb.run_grader()
    finally:
        sb.cleanup()

    score = float(result.get("gap_score", 0.0))
    verdicts = result.get("verdict_counts", {})
    ok = abs(score - 1.0) < EPS

    # Cross-check: the oracle's gold must be the same source the gates graded.
    # The canary comment (canary check) is stamped onto the verifier-side copy only, so
    # normalise it out — it is provenance metadata, not solution logic.
    def _strip_canary(src: str) -> str:
        return "\n".join(l for l in src.splitlines()
                          if "PLXCANARY-" not in l and "oracle canary" not in l).strip()

    ref = layout.tests / REFERENCE_DIR / "gold.py"
    same = ref.is_file() and _strip_canary(ref.read_text()) == _strip_canary(embedded)

    return {
        "ok": ok and same,
        "detail": (f"gap_score={score} verdicts={verdicts}"
                   + ("" if same else "  MISMATCH: differs from _plx_reference/gold.py")),
        "score": score,
        "matches_reference": same,
    }


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

def _summary(report: Stage0Report) -> None:
    """Printed after the live gate lines — failures in full, then the ladder."""
    failed = [g for g in report.gates if not g.passed]
    if failed:
        print(f"\n{RED}failures{RESET}")
        for gate in failed:
            print(f"  {gate.id} {gate.name}: {gate.detail}")
            if gate.data:
                snippet = json.dumps(gate.data, ensure_ascii=False)[:400]
                print(f"     {DIM}{snippet}{RESET}")

    s = report.scores
    print(f"\n{DIM}ladder{RESET}  "
          f"stub {s.get('stub')}  bypass {s.get('bypass')}  "
          f"familiar {s.get('familiar')}  gold {s.get('gold')}")
    passed = sum(1 for g in report.gates if g.passed)
    colour = GREEN if report.passed else RED
    verdict = "ALL GATES PASS" if report.passed else "SOME GATES FAILED"
    print(f"{colour}{verdict}{RESET}  {DIM}({passed}/{len(report.gates)}){RESET}")


# kept for backwards compatibility with anything importing _print
_print = _summary
