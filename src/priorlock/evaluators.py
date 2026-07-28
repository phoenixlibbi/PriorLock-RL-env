"""Automated Evaluators — deterministic success-criteria checkers.

PriorLock's reward is objective because two independent evaluators grade the
agent submission:

1. **Host evaluator** — the Harbor task's original verifier
   (``tests/task_verify.sh``). Runs inside Docker via Harbor; produces
   ``task_score``.
2. **Probe evaluator** — generated ``tests/probe_grade.py``. Observes call
   arguments via ``inspect.Signature.bind`` (not self-reported output).
   Produces ``gap_score`` and per-probe verdicts.

This module is the public API for (2) offline. It does **not** reimplement
grading — it wraps the same sandbox + generated grader Harbor uses.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .gates import _Sandbox
from .inject import REFERENCE_DIR, detect_layout, is_wrapped, read_manifest

# Verdict that counts as meeting the prior-override success criterion.
_OVERRIDE = "override"


@dataclass
class CheckResult:
    """One automated check against a single success criterion."""

    id: str
    criterion: str
    passed: bool
    verdict: str
    score: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluatorReport:
    """Normalized, deterministic evaluator report for a probe submission."""

    task_id: str
    library: str
    deterministic: bool
    gap_score: float
    flags: list[str]
    success_criteria: list[str]
    checks: list[CheckResult]
    host_evaluator: dict[str, Any]
    probe_evaluator: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "library": self.library,
            "deterministic": self.deterministic,
            "gap_score": self.gap_score,
            "flags": list(self.flags),
            "success_criteria": list(self.success_criteria),
            "checks": [c.to_dict() for c in self.checks],
            "host_evaluator": dict(self.host_evaluator),
            "probe_evaluator": dict(self.probe_evaluator),
        }


def grade_probes(
    task_dir: str | Path,
    *,
    solution: str | Path | None = None,
    reference: str | None = None,
) -> dict[str, Any]:
    """Run the generated probe grader against a solution.

    Exactly one of ``solution`` or ``reference`` must be provided.
    ``reference`` is one of ``gold``, ``familiar``, ``stub``, ``bypass``.
    """
    task = Path(task_dir).resolve()
    if not is_wrapped(task):
        raise ValueError(f"{task} is not a wrapped PriorLock task")

    layout = detect_layout(task)
    source = _resolve_solution(layout, solution=solution, reference=reference)

    sandbox = _Sandbox(layout)
    try:
        sandbox.install_solution(source)
        return sandbox.run_grader()
    finally:
        sandbox.cleanup()


def evaluate_submission(
    task_dir: str | Path,
    *,
    solution: str | Path | None = None,
    reference: str | None = None,
) -> EvaluatorReport:
    """Grade a probe submission and return a structured evaluator report.

    Maps each probe to an explicit success criterion (installed behaviour) and
    records whether the agent met it (``verdict == override``), with call-arg
    evidence from the grader.
    """
    task = Path(task_dir).resolve()
    if not is_wrapped(task):
        raise ValueError(f"{task} is not a wrapped PriorLock task")

    manifest = read_manifest(task)
    plx = manifest.get("priorlock") if isinstance(manifest.get("priorlock"), dict) else {}
    raw = grade_probes(task, solution=solution, reference=reference)

    # TOML [[probe]] → key "probe"; some callers may use "probes".
    probe_rows = manifest.get("probe") or manifest.get("probes") or []
    probe_meta = {p.get("id"): p for p in probe_rows if p.get("id")}
    criteria: list[str] = []
    checks: list[CheckResult] = []

    for p in raw.get("probes") or []:
        pid = p.get("id", "")
        meta = probe_meta.get(pid) or {}
        criterion = (
            meta.get("installed_behaviour")
            or meta.get("summary")
            or f"probe {pid} must use installed (gold) call arguments"
        )
        criteria.append(f"{pid}: {criterion}")
        verdict = str(p.get("verdict") or "absent")
        score = float(p.get("score") or 0.0)
        detail = p.get("detail") if isinstance(p.get("detail"), dict) else {}
        checks.append(
            CheckResult(
                id=pid,
                criterion=criterion,
                passed=(verdict == _OVERRIDE),
                verdict=verdict,
                score=score,
                evidence={
                    "supplied": detail.get("supplied", []),
                    "gold_call": detail.get("gold_call"),
                    "output_matches": detail.get("output_matches"),
                    "familiar_behaviour": meta.get("familiar_behaviour"),
                    "installed_behaviour": meta.get("installed_behaviour"),
                },
            )
        )

    flags = list(raw.get("flags") or [])
    return EvaluatorReport(
        task_id=str(plx.get("task_id") or manifest.get("task_id") or task.name),
        library=str(plx.get("library") or manifest.get("library") or ""),
        deterministic=True,
        gap_score=float(raw.get("gap_score") or 0.0),
        flags=flags,
        success_criteria=criteria,
        checks=checks,
        host_evaluator={
            "name": "host_task_verifier",
            "entrypoint": "tests/task_verify.sh",
            "produces": "task_score",
            "runs_offline": False,
            "note": (
                "Host success criteria (schemas, metrics, required outputs) are "
                "checked by the original Harbor verifier inside Docker. "
                "Use `harbor run -p <task> -a …` to obtain task_score."
            ),
        },
        probe_evaluator={
            "name": "probe_grade",
            "entrypoint": "tests/probe_grade.py",
            "produces": "gap_score",
            "runs_offline": True,
            "method": "call_argument_interception",
            "note": (
                "Prior-override success criteria are checked by observing "
                "explicit call arguments via inspect.Signature.bind against "
                "a verifier-owned pristine library copy."
            ),
        },
        raw=raw,
    )


def meets_success_criteria(
    report: EvaluatorReport | dict[str, Any],
    *,
    require_all_override: bool = False,
    allow_flags: bool = False,
) -> bool:
    """Objective pass/fail over an evaluator report.

    Default: no grader failure flags, and at least one probe check present.
    With ``require_all_override=True``, every probe must have verdict
    ``override`` (gold-equivalent prior override).
    """
    if isinstance(report, EvaluatorReport):
        flags = report.flags
        checks = report.checks
    else:
        flags = list(report.get("flags") or [])
        checks = report.get("checks") or []

    if flags and not allow_flags:
        return False
    if not checks:
        return False
    if require_all_override:
        for c in checks:
            verdict = c.verdict if isinstance(c, CheckResult) else c.get("verdict")
            if verdict != _OVERRIDE:
                return False
    return True


def write_report(report: EvaluatorReport, path: str | Path) -> Path:
    """Write ``EvaluatorReport`` JSON to ``path``."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out


def _resolve_solution(
    layout,
    *,
    solution: str | Path | None,
    reference: str | None,
) -> Path:
    if reference and solution:
        raise ValueError("pass only one of solution= or reference=")
    if reference:
        allowed = {"gold", "familiar", "stub", "bypass"}
        if reference not in allowed:
            raise ValueError(f"reference must be one of {sorted(allowed)}")
        ref = layout.tests / REFERENCE_DIR / f"{reference}.py"
        if not ref.is_file():
            raise FileNotFoundError(f"reference solution missing: {ref}")
        return ref
    if solution is None:
        raise ValueError("provide solution= path or reference= name")
    path = Path(solution).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"solution not found: {path}")
    return path
