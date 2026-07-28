"""D4: grader re-run flaky-rate — N identical regrades of gold/familiar."""
from __future__ import annotations

from pathlib import Path

from priorlock.inject import wrap_task
from priorlock.repro import assert_reproducible_grade


def test_grader_determinism_flaky_rate_zero(mini_task: Path):
    wrap_task(mini_task, count=3)
    # Bar: < 2% mismatches; we require exact identity (0 mismatches).
    gold = assert_reproducible_grade(mini_task, "gold", n=20)
    familiar = assert_reproducible_grade(mini_task, "familiar", n=20)
    assert gold["gap_score"] == 1.0
    assert familiar["gap_score"] == 0.4
    assert gold["mismatches"] == 0
    assert familiar["mismatches"] == 0
    assert gold["flaky_rate"] == 0.0
    assert familiar["flaky_rate"] == 0.0
