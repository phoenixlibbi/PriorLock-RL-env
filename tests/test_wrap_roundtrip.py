"""Wrap → offline grade → unwrap roundtrip on the mini Harbor fixture."""
from __future__ import annotations

from pathlib import Path

from priorlock.evaluators import evaluate_submission
from priorlock.gates import run_stage0
from priorlock.inject import is_wrapped, unwrap_task, wrap_task


def test_wrap_stage0_unwrap_roundtrip(mini_task: Path):
    assert not is_wrapped(mini_task)

    result = wrap_task(mini_task, count=3)
    assert is_wrapped(mini_task)
    assert len(result.probes) == 3

    gold = evaluate_submission(mini_task, reference="gold")
    assert gold.gap_score == 1.0

    report = run_stage0(mini_task, verbose=False)
    assert report.passed, [
        (g.id, g.detail) for g in report.gates if not g.passed
    ]

    removed = unwrap_task(mini_task)
    assert removed
    assert not is_wrapped(mini_task)
    assert not (mini_task / "priorlock.toml").exists()
