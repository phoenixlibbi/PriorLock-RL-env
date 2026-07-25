"""Stage-0 offline gate verification for tablixdemo.

Checks (no Docker, no API key needed):
  G1 gold score == 1.0
  G2 familiar score == 0.40  (model-free OOD proxy)
  G3 stub score == 0.0
  G4 strict ladder: 0.0 < 0.40 < 1.0
  G5 visible tests pass for BOTH gold and familiar pipelines
  G6 "__missing__" canary absent from environment/ (agent-visible surface)

Usage:  cd tablixdemo && python3 scripts/stage0.py
"""
import json, os, subprocess, sys, tempfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK = os.path.join(ROOT, "tasks", "tablixdemo-0")
TESTS_DIR = os.path.join(TASK, "tests")
REPO = os.path.join(TASK, "environment", "repo")
SRC_TABLIX = os.path.join(ROOT, "src", "tablix")
SRC_FAMILIAR = os.path.join(ROOT, "src", "tablix_familiar")

GOLD_CODE = '''
import json
import tablix

def run(data_dir, out_path):
    records = tablix.load_csv(f"{data_dir}/transactions.csv")
    groups = tablix.group_by(records, "category")
    categorySales = {cat: tablix.sum_field(recs, "amount") for cat, recs in groups.items()}
    categoryCount = {cat: len(recs) for cat, recs in groups.items()}
    top = tablix.top_n(records, 3, "amount")
    topProductIds = sorted(int(r["id"]) for r in top)
    with open(out_path, "w") as f:
        json.dump({"categorySales": categorySales, "categoryCount": categoryCount,
                   "topProductIds": topProductIds}, f)
'''

FAMILIAR_CODE = '''
import json
import tablix

def run(data_dir, out_path):
    records = tablix.load_csv(f"{data_dir}/transactions.csv")
    groups = tablix.group_by(records, "category")
    categorySales = {cat: tablix.sum_field(recs, "amount") for cat, recs in groups.items()}
    categoryCount = {cat: len(recs) for cat, recs in groups.items()}
    top = tablix.top_n(records, 3, "amount")
    topProductIds = sorted(int(r["id"]) for r in top)
    with open(out_path, "w") as f:
        json.dump({"categorySales": categorySales, "categoryCount": categoryCount,
                   "topProductIds": topProductIds}, f)
'''

STUB_CODE = '''
import json
def run(data_dir, out_path):
    raise NotImplementedError
'''


def grade_variant(pipeline_code, tablix_src, label):
    """Run pipeline_code with tablix from tablix_src; return reward."""
    tmp = tempfile.mkdtemp()
    # Set up a mini submission dir
    src_dir = os.path.join(tmp, "src")
    tablix_dir = os.path.join(tmp, "tablix")
    os.makedirs(src_dir)
    shutil.copytree(tablix_src, tablix_dir)
    with open(os.path.join(src_dir, "pipeline.py"), "w") as f:
        f.write(pipeline_code)

    # Run grade.py phase A+B, but with our custom tablix
    grade_script = os.path.join(TESTS_DIR, "grade.py")
    data_dir = os.path.join(TESTS_DIR, "data")

    runner = f"""
import sys, os, json, importlib.util, tempfile
sys.path.insert(0, {repr(tmp)})
sys.path.insert(0, {repr(tmp)})
# patch tablix path to use our variant
spec = importlib.util.spec_from_file_location("pipeline", {repr(os.path.join(src_dir, "pipeline.py"))})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = os.path.join(tempfile.mkdtemp(), "report.json")
try:
    mod.run({repr(data_dir)}, out)
    with open(out) as f:
        got = json.load(f)
    print(json.dumps(got))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""
    result = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return 0.0, {"error": result.stderr[-200:]}
    got = json.loads(result.stdout.strip())
    if "error" in got:
        return 0.0, got

    # Grade manually inline
    EXPECTED_IDS = [3, 4, 5, 8, 9]
    core_ok = (isinstance(got.get("categorySales"), dict)
               and isinstance(got.get("categoryCount"), dict)
               and isinstance(got.get("topProductIds"), list))
    cs = got.get("categorySales", {})
    cc = got.get("categoryCount", {})
    missing_ok = (core_ok
                  and "__missing__" in cs and abs(cs["__missing__"] - 89.99) < 1e-6
                  and "__missing__" in cc and cc["__missing__"] == 1)
    topn_ok = (core_ok and sorted(got.get("topProductIds", [])) == EXPECTED_IDS)
    reward = round(0.40*core_ok + 0.30*missing_ok + 0.30*topn_ok, 4)
    return reward, {"core": core_ok, "missing_grp": missing_ok, "top_n_ties": topn_ok,
                    "topProductIds_got": sorted(got.get("topProductIds", []))}


def check_visible(pipeline_code, tablix_src, label):
    """Run visible pytest; return True if all pass."""
    tmp = tempfile.mkdtemp()
    src_dir = os.path.join(tmp, "src")
    tablix_dir = os.path.join(tmp, "tablix")
    data_dir = os.path.join(tmp, "data")
    tests_dir = os.path.join(tmp, "tests")
    docs_dir = os.path.join(tmp, "docs")
    os.makedirs(src_dir); os.makedirs(data_dir); os.makedirs(tests_dir); os.makedirs(docs_dir)
    shutil.copytree(tablix_src, tablix_dir)
    shutil.copy(os.path.join(TASK, "environment", "repo", "data", "transactions.csv"),
                os.path.join(data_dir, "transactions.csv"))
    # Copy visible test adjusted to use this tmp layout
    shutil.copy(os.path.join(REPO, "tests", "test_visible.py"),
                os.path.join(tests_dir, "test_visible.py"))
    with open(os.path.join(src_dir, "pipeline.py"), "w") as f:
        f.write(pipeline_code)
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{tmp}:{tmp}"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", os.path.join(tests_dir, "test_visible.py"), "-q"],
        capture_output=True, text=True, cwd=tmp, env=env, timeout=30,
    )
    return r.returncode == 0, r.stdout[-300:]


def canary_check():
    """G6: oracle assets (grade.py, expected.json, tablix_familiar) must NOT
    appear in environment/ (the agent-visible surface).
    '__missing__' is a public documented value and is expected in docs/lib.
    """
    env_dir = os.path.join(TASK, "environment")
    forbidden_files = {"grade.py", "expected.json"}
    forbidden_dirs = {"tablix_familiar"}
    hits = []
    for root, dirs, files in os.walk(env_dir):
        for fn in files:
            if fn in forbidden_files:
                hits.append(os.path.relpath(os.path.join(root, fn), env_dir))
        for d in dirs:
            if d in forbidden_dirs:
                hits.append(os.path.relpath(os.path.join(root, d), env_dir) + "/")
    return hits


PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def main():
    print("=== tablixdemo Stage-0 ===\n")
    all_ok = True

    # G1 gold
    gold_r, gold_d = grade_variant(GOLD_CODE, SRC_TABLIX, "gold")
    ok = abs(gold_r - 1.0) < 1e-6
    all_ok &= ok
    print(f"G1 gold score       {PASS if ok else FAIL}  reward={gold_r}  detail={gold_d}")

    # G2 familiar
    fam_r, fam_d = grade_variant(FAMILIAR_CODE, SRC_FAMILIAR, "familiar")
    ok = abs(fam_r - 0.40) < 1e-6
    all_ok &= ok
    print(f"G2 familiar score   {PASS if ok else FAIL}  reward={fam_r}  detail={fam_d}")

    # G3 stub
    stub_r, stub_d = grade_variant(STUB_CODE, SRC_TABLIX, "stub")
    ok = stub_r == 0.0
    all_ok &= ok
    print(f"G3 stub score       {PASS if ok else FAIL}  reward={stub_r}")

    # G4 ladder
    ladder_ok = stub_r < fam_r < gold_r
    all_ok &= ladder_ok
    print(f"G4 ladder           {PASS if ladder_ok else FAIL}  {stub_r} < {fam_r} < {gold_r}")

    # G5 visible tests
    gold_vis_ok, gold_vis_out = check_visible(GOLD_CODE, SRC_TABLIX, "gold")
    fam_vis_ok, fam_vis_out = check_visible(FAMILIAR_CODE, SRC_FAMILIAR, "familiar")
    g5_ok = gold_vis_ok and fam_vis_ok
    all_ok &= g5_ok
    print(f"G5 visible tests    {PASS if g5_ok else FAIL}  gold={'pass' if gold_vis_ok else 'FAIL'} familiar={'pass' if fam_vis_ok else 'FAIL'}")
    if not g5_ok:
        print("   gold:", gold_vis_out[-200:])
        print("   familiar:", fam_vis_out[-200:])

    # G6 canary
    leaks = canary_check()
    g6_ok = len(leaks) == 0
    all_ok &= g6_ok
    print(f"G6 canary clean     {PASS if g6_ok else FAIL}  leaks={leaks}")

    print(f"\n{'ALL GATES PASS' if all_ok else 'SOME GATES FAILED'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
