"""The starter recipes in examples/ run and print the expected ladder."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).resolve().parent.parent / "examples").glob("*.py"))


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.name)
def test_recipe_runs(script):
    src = str(Path(__file__).resolve().parent.parent / "src")
    env = {**os.environ, "PYTHONHASHSEED": "0",
           "PYTHONPATH": src + os.pathsep + os.environ.get("PYTHONPATH", "")}
    out = subprocess.run([sys.executable, str(script)], capture_output=True,
                         text=True, timeout=300, env=env)
    assert out.returncode == 0, out.stderr[-1500:]
    assert "0.40" in out.stdout
