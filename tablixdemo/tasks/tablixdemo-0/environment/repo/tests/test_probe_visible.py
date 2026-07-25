"""Smoke tests for the datawright checks.

These are SHAPE tests only — they assert that the solution runs, emits valid
JSON, and produces the right container type under each key. They deliberately do
not assert any value, so passing them tells you the plumbing works and nothing
about whether the results are correct.
"""
import importlib.util
import json
import os
import sys
import tempfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOLUTION = os.path.join(REPO, "probe_solution.py")
DATA = os.path.join(REPO, "data/probe_input.json")


def _load():
    if not os.path.isfile(SOLUTION):
        pytest.skip("probe_solution.py not written yet")
    spec = importlib.util.spec_from_file_location("probe_solution", SOLUTION)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["probe_solution"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_library_importable():
    import datawright
    assert datawright.version()


def test_input_data_present():
    with open(DATA) as f:
        payload = json.load(f)
    for key in ('topIds', 'bucketCounts', 'merged',):
        assert key in payload, key + " missing from input data"


def test_solution_exposes_run():
    mod = _load()
    assert callable(getattr(mod, "run", None)), "probe_solution must define run(data_path, out_path)"


def test_solution_emits_all_keys():
    mod = _load()
    out_path = os.path.join(tempfile.mkdtemp(), "probe_output.json")
    mod.run(DATA, out_path)
    with open(out_path) as f:
        out = json.load(f)
    for key in ('topIds', 'bucketCounts', 'merged',):
        assert key in out, key + " missing from output"


def test_output_types():
    mod = _load()
    out_path = os.path.join(tempfile.mkdtemp(), "probe_output.json")
    mod.run(DATA, out_path)
    with open(out_path) as f:
        out = json.load(f)
    assert isinstance(out['topIds'], list), "topIds has the wrong type"
    assert isinstance(out['bucketCounts'], dict), "bucketCounts has the wrong type"
    assert isinstance(out['merged'], dict), "merged has the wrong type"
