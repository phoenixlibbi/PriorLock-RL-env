"""Shared pytest fixtures and env pins for PriorLock unit tests."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

# Pin hash randomization so selection / set iteration stays stable across runs.
os.environ.setdefault("PYTHONHASHSEED", "0")

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MINI_TASK = FIXTURES / "mini_task"


@pytest.fixture
def mini_task(tmp_path: Path) -> Path:
    """Fresh copy of the minimal Harbor fixture for wrap/unwrap tests."""
    dest = tmp_path / "mini_task"
    shutil.copytree(MINI_TASK, dest)
    return dest
