"""Visible smoke tests. Passing these does NOT guarantee full correctness."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.pipeline import run  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _report():
    out = os.path.join(tempfile.mkdtemp(), "report.json")
    run(os.path.join(BASE, "data"), out)
    with open(out) as f:
        return json.load(f)


def test_schema_and_types():
    r = _report()
    assert "categorySales" in r, "missing categorySales"
    assert "categoryCount" in r, "missing categoryCount"
    assert "topProductIds" in r, "missing topProductIds"
    assert isinstance(r["categorySales"], dict)
    assert isinstance(r["categoryCount"], dict)
    assert isinstance(r["topProductIds"], list)
    assert all(isinstance(i, int) for i in r["topProductIds"])


def test_shapes():
    r = _report()
    # Must have at least one category, at least 3 top products
    assert len(r["categorySales"]) >= 1
    assert len(r["topProductIds"]) >= 3
    # Sales and counts must be non-negative
    assert all(v >= 0 for v in r["categorySales"].values())
    assert all(v >= 0 for v in r["categoryCount"].values())


def test_deterministic():
    a = _report()
    b = _report()
    assert a == b
