"""Two-phase grader for tablixdemo.

Phase A: execute agent's src/pipeline.py in a scratch dir with ONLY canonical
         tablix and data (no expected.json visible during agent code execution).
Phase B: score the emitted report.json against expected.json.

Score breakdown:
  core        (0.40) — all 3 keys present with correct types
  missing_grp (0.30) — "__missing__" present with correct values in both dicts
  top_n_ties  (0.30) — topProductIds contains all 5 tie-inclusive product IDs

Gold: 1.0   Familiar (prior-memory): 0.40   Stub: 0.0
"""
import argparse, json, os, subprocess, sys, tempfile

TESTS_DIR_DEFAULT = os.path.dirname(os.path.abspath(__file__))

EXPECTED = {
    "categorySales": {"Electronics": 599.96, "Home": 600.0,
                      "Tools": 600.0, "__missing__": 89.99},
    "categoryCount": {"Electronics": 4, "Home": 3, "Tools": 2, "__missing__": 1},
    "topProductIds": [3, 4, 5, 8, 9],   # all 5 tied records (>=200.00)
}


def _close(a, b, tol=1e-6):
    return abs(float(a) - float(b)) < tol


def phase_a(submission_dir, tests_dir, timeout=60):
    """Execute pipeline.py in an isolated subprocess; return path to report."""
    out_file = os.path.join(tempfile.mkdtemp(), "report.json")
    data_dir = os.path.join(tests_dir, "data")
    tablix_dir = os.path.dirname(os.path.join(tests_dir, "tablix", "__init__.py"))
    tablix_pkg_parent = os.path.dirname(tablix_dir)

    runner = f"""
import sys, os
sys.path.insert(0, {repr(tablix_pkg_parent)})
sys.path.insert(0, {repr(submission_dir)})
# Confirm oracle assets not on path before import
import importlib.util
spec = importlib.util.spec_from_file_location(
    "pipeline", os.path.join({repr(submission_dir)}, "src", "pipeline.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.run({repr(data_dir)}, {repr(out_file)})
"""
    result = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        return None, f"execution error: {result.stderr[-400:]}"
    if not os.path.exists(out_file):
        return None, "pipeline did not write output file"
    return out_file, None


def phase_b(report_path):
    """Grade the report against expected; return (reward, details dict)."""
    with open(report_path) as f:
        got = json.load(f)

    details = {}

    # --- core (0.40) ---
    core_ok = (
        isinstance(got.get("categorySales"), dict)
        and isinstance(got.get("categoryCount"), dict)
        and isinstance(got.get("topProductIds"), list)
        and all(isinstance(i, int) for i in got.get("topProductIds", []))
    )
    details["core"] = {"pass": core_ok, "weight": 0.40}

    # --- missing_grp (0.30) ---
    cs = got.get("categorySales", {})
    cc = got.get("categoryCount", {})
    missing_ok = (
        core_ok
        and "__missing__" in cs
        and _close(cs["__missing__"], EXPECTED["categorySales"]["__missing__"])
        and "__missing__" in cc
        and cc["__missing__"] == EXPECTED["categoryCount"]["__missing__"]
    )
    # Also verify the non-missing categories are correct
    if missing_ok:
        for cat in ("Electronics", "Home", "Tools"):
            if not _close(cs.get(cat, -1), EXPECTED["categorySales"][cat]):
                missing_ok = False
            if cc.get(cat) != EXPECTED["categoryCount"][cat]:
                missing_ok = False
    details["missing_grp"] = {"pass": missing_ok, "weight": 0.30}

    # --- top_n_ties (0.30) ---
    got_ids = sorted(got.get("topProductIds", []))
    topn_ok = (core_ok and got_ids == EXPECTED["topProductIds"])
    details["top_n_ties"] = {
        "pass": topn_ok, "weight": 0.30,
        "got": got_ids, "expected": EXPECTED["topProductIds"],
    }

    reward = (0.40 * core_ok + 0.30 * missing_ok + 0.30 * topn_ok)
    reward = round(reward, 4)
    strict_pass = reward >= 0.95

    return reward, {
        "reward": reward,
        "strict_pass": strict_pass,
        "reason": "all groups pass" if strict_pass else
                  f"failed: {[k for k,v in details.items() if not v['pass']]}",
        "groups": details,
        "got_summary": {k: got.get(k) for k in ("categorySales","categoryCount","topProductIds")},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True)
    ap.add_argument("--tests-dir", default=TESTS_DIR_DEFAULT)
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    report_path, err = phase_a(args.submission, args.tests_dir, args.timeout)
    if err:
        result = {"reward": 0.0, "strict_pass": False, "reason": err, "groups": {}}
    else:
        _, result = phase_b(report_path)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
