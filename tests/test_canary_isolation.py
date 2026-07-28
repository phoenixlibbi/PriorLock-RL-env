"""G12 static half: oracle canary present verifier-side only after wrap."""
from __future__ import annotations

from pathlib import Path

from priorlock.inject import wrap_task
from priorlock.leakprobe import canary_scan


def test_canary_verifier_side_only(mini_task: Path):
    wrap_task(mini_task, count=3)
    scan = canary_scan(mini_task)
    assert scan["ok"] is True
    assert scan["canary"].startswith("PLXCANARY-")
    assert not scan["agent_hits"]
    assert "verifier" in scan["detail"] or "verifier-side" in scan["detail"]
