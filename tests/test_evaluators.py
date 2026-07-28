"""Automated evaluator API: gold/familiar scores and success criteria."""
from __future__ import annotations

from pathlib import Path

from priorlock.evaluators import (
    CheckResult,
    EvaluatorReport,
    evaluate_submission,
    meets_success_criteria,
)
from priorlock.inject import wrap_task


def test_evaluate_gold_and_familiar(mini_task: Path):
    wrap_task(mini_task, count=3)

    gold = evaluate_submission(mini_task, reference="gold")
    assert gold.gap_score == 1.0
    assert all(c.verdict == "override" for c in gold.checks)
    assert meets_success_criteria(gold, require_all_override=True)

    familiar = evaluate_submission(mini_task, reference="familiar")
    assert familiar.gap_score == 0.4
    assert all(c.verdict == "prior_locked" for c in familiar.checks)
    assert meets_success_criteria(familiar) is True
    assert meets_success_criteria(familiar, require_all_override=True) is False


def test_meets_success_criteria_flags_fail_closed():
    report = EvaluatorReport(
        task_id="t",
        library="lib",
        deterministic=True,
        gap_score=1.0,
        flags=["probe_grader_failed"],
        success_criteria=["x"],
        checks=[
            CheckResult(
                id="p1",
                criterion="c",
                passed=True,
                verdict="override",
                score=1.0,
            )
        ],
        host_evaluator={},
        probe_evaluator={},
    )
    assert meets_success_criteria(report) is False
    assert meets_success_criteria(report, allow_flags=True) is True


def test_meets_success_criteria_default_vs_require_all_override():
    mixed = {
        "flags": [],
        "checks": [
            {"verdict": "override"},
            {"verdict": "prior_locked"},
        ],
    }
    assert meets_success_criteria(mixed) is True
    assert meets_success_criteria(mixed, require_all_override=True) is False

    empty = {"flags": [], "checks": []}
    assert meets_success_criteria(empty) is False
