"""
Scaffolding templates for `priorlock new-domain <name>`.

Each TMPL_* constant is a string template. Use .format(lib=..., Lib=..., task=...)
where lib = library name (lowercase), Lib = title-cased, task = first task id.
"""

import os
import stat

# ── deviation_spec.yaml ──────────────────────────────────────────────────────

TMPL_DEVIATION_SPEC = """\
# PriorLock deviation spec for domain: {lib}
#
# Fill in the two required deviations (minimum). Each deviation must be:
#   - Silent: wrong VALUES, not wrong types or crashes
#   - Documented: in environment/repo/docs/CHANGELOG.md
#   - Testable: grade.py can score correct vs incorrect numerically
#
# The familiar_score (G2) must land at 0.40 after you implement
# grade.py weights. Adjust weights so core=0.40, each deviation=0.30.

library: {lib}
installed_version: "2.0"
familiar_version: "1.x"
expected_familiar_score: 0.40

deviations:
  - id: dev_001
    function: FUNCTION_NAME_HERE
    trigger: "DESCRIBE: what input condition triggers the deviation"
    familiar_behavior: "DESCRIBE: what v1.x does"
    installed_behavior: "DESCRIBE: what v2.0 does differently"
    grade_weight: 0.30
    trap_data: "DESCRIBE: what you put in test data to trigger this"

  - id: dev_002
    function: ANOTHER_FUNCTION_HERE
    trigger: "DESCRIBE: what input condition triggers the deviation"
    familiar_behavior: "DESCRIBE: what v1.x does"
    installed_behavior: "DESCRIBE: what v2.0 does differently"
    grade_weight: 0.30
    trap_data: "DESCRIBE: what you put in test data to trigger this"

# Score formula (must sum to 1.0):
#   reward = 0.40 * core_ok + 0.30 * dev_001_ok + 0.30 * dev_002_ok
#
# If you add a third deviation, adjust weights: e.g. 0.40 + 0.20 + 0.20 + 0.20 = 1.0
"""

# ── src/<lib>/__init__.py  (installed — deviations present) ──────────────────

TMPL_LIB_INSTALLED = '''\
"""
{Lib} v2.0 — the INSTALLED library (deviations from v1.x present).

This file is what the agent imports. It must:
  1. Look familiar — same function names and signatures as v1.x
  2. Deviate silently — wrong values on edge cases, not crashes or type errors
  3. Be documented — deviations are listed in environment/repo/docs/CHANGELOG.md

Agent can read this file. Do NOT put expected values or grading logic here.
"""


def load_csv(path: str) -> list[dict]:
    """Load a CSV file and return a list of row dicts."""
    import csv
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# TODO: implement your first deviation here
def function_one(records, key):
    """
    v2.0 behaviour (DEVIATION from v1.x):
      DESCRIBE WHAT IS DIFFERENT HERE
    """
    raise NotImplementedError("implement with v2.0 semantics")


# TODO: implement your second deviation here
def function_two(records, n, key, reverse=True):
    """
    v2.0 behaviour (DEVIATION from v1.x):
      DESCRIBE WHAT IS DIFFERENT HERE
    """
    raise NotImplementedError("implement with v2.0 semantics")


def sum_field(records: list[dict], field: str) -> float:
    """Return the sum of a numeric field across records."""
    return round(sum(float(r[field]) for r in records), 10)
'''

# ── src/<lib>_familiar/__init__.py  (v1.x — Stage-0 baseline only) ──────────

TMPL_LIB_FAMILIAR = '''\
"""
{Lib} v1.x — FAMILIAR semantics (Stage-0 baseline ONLY).

This file is NEVER shipped to the agent container.
It is used by scripts/stage0.py to verify that G2 (familiar score = 0.40)
holds: code that uses the old semantics must score exactly 0.40.

Copy the installed library here, then REVERT the deviations to v1.x behaviour.
"""


def load_csv(path: str) -> list[dict]:
    import csv
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# TODO: implement with v1.x semantics (no deviations)
def function_one(records, key):
    raise NotImplementedError("implement with v1.x semantics")


def function_two(records, n, key, reverse=True):
    raise NotImplementedError("implement with v1.x semantics")


def sum_field(records: list[dict], field: str) -> float:
    return round(sum(float(r[field]) for r in records), 10)
'''

# ── task.toml ────────────────────────────────────────────────────────────────

TMPL_TASK_TOML = '''\
schema_version = "1.3"

[task]
name = "priorlock/{task}"
description = "Implement a task using the INSTALLED {lib} library; docs in-container are authoritative."
authors = []
keywords = ["version-grounding", "prior-override", "{lib}"]

[metadata]
difficulty = "medium"
category = "programming"

[agent]
timeout_sec = 1800.0

[verifier]
timeout_sec = 300.0

[environment]
network_mode = "no-network"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
workdir = "/app/repo"
'''

# ── instruction.md ───────────────────────────────────────────────────────────

TMPL_INSTRUCTION = '''\
# Task: TODO — give your task a descriptive title

TODO: describe what the agent needs to implement.
The agent will implement `run(data_dir, out_path)` in `src/pipeline.py`
using the INSTALLED {lib} library. The docs in `docs/` are authoritative
for the installed version and may differ from {lib} versions you know.

## Input

`data_dir` contains TODO_FILENAME with fields:
- `field1` (type): description
- `field2` (type): description

## Output

Write a JSON object to `out_path` with exactly these keys:

- `key1` (type): description — uses {lib}\'s semantics (see `docs/CHANGELOG.md`)
- `key2` (type): description

## Rules

- Edit ONLY `src/pipeline.py`.
- Do not modify `tests/`, `data/`, `docs/`, or the installed {lib} package.
- You may run `python -m pytest tests/` at any time; passing visible tests does
  not guarantee full correctness — grading uses hidden tests with exact values.
- Grading restores canonical {lib} and data before scoring.
'''

# ── Dockerfile ───────────────────────────────────────────────────────────────

TMPL_DOCKERFILE = '''\
FROM python:3.11-slim
ENV PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1
COPY repo /app/repo
# {lib}/ dir contains __init__.py directly (package root = /opt/{lib}/{lib})
COPY {lib} /opt/{lib}/{lib}
# Remove any accidentally nested copy from the build context
RUN rm -rf /opt/{lib}/{lib}/{lib} 2>/dev/null || true
ENV PYTHONPATH=/opt/{lib}:/app/repo
WORKDIR /app/repo
# Agent container: no tests/expected, no oracle, no familiar library.
# Network: no-network (enforced by harness).
'''

# ── pipeline.py stub ─────────────────────────────────────────────────────────

TMPL_PIPELINE = '''\
"""TODO: task description — implement run() below."""
import json


def run(data_dir, out_path):
    """Read input from data_dir, write JSON output to out_path."""
    raise NotImplementedError("implement using the installed {lib} library")
'''

# ── CHANGELOG.md ─────────────────────────────────────────────────────────────

TMPL_CHANGELOG = '''\
# {Lib} Changelog

## v2.0 (current — installed in this environment)

### Breaking changes from v1.x

**`function_one` — TODO: deviation title**
- v1.x behaviour: TODO describe old behaviour
- v2.0 behaviour: TODO describe new behaviour
- Example:
  ```python
  # v1.x result: ...
  # v2.0 result: ...
  ```

**`function_two` — TODO: deviation title**
- v1.x behaviour: TODO describe old behaviour
- v2.0 behaviour: TODO describe new behaviour
- Example:
  ```python
  # v1.x result: ...
  # v2.0 result: ...
  ```

## v1.x (previous)
Initial release.
'''

# ── api_reference.md ─────────────────────────────────────────────────────────

TMPL_API_REFERENCE = '''\
# {Lib} API Reference (v2.0)

## `load_csv(path) -> list[dict]`
Load a CSV file. Returns a list of row dicts with string values.

## `function_one(records, key) -> dict`
TODO: document the function and its v2.0 behaviour.

**Parameters:**
- `records`: list of row dicts
- `key`: field name to group/process by

**Returns:** dict

**v2.0 note:** TODO — document deviation from v1.x.

---

## `function_two(records, n, key, reverse=True) -> list`
TODO: document the function and its v2.0 behaviour.

**Parameters:**
- `records`: list of row dicts
- `n`: number of results requested
- `key`: field to rank by
- `reverse`: descending if True (default)

**Returns:** list of dicts

**v2.0 note:** TODO — document deviation from v1.x.

---

## `sum_field(records, field) -> float`
Return the sum of a numeric field across records.
'''

# ── test_visible.py ──────────────────────────────────────────────────────────

TMPL_TEST_VISIBLE = '''\
"""
Visible smoke tests. Passing these does NOT guarantee full correctness.

IMPORTANT: These tests must pass for BOTH the familiar (v1.x) solution
and the gold (v2.0) solution. They check SHAPE only — not exact values.
If your tests discriminate (i.e. fail for familiar but pass for gold),
G5 will fail. Check shape, types, and non-negativity only.
"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.pipeline import run

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _report():
    out = os.path.join(tempfile.mkdtemp(), "report.json")
    run(os.path.join(BASE, "data"), out)
    with open(out) as f:
        return json.load(f)


def test_schema_and_types():
    r = _report()
    # TODO: check that required keys exist and have correct types
    assert "key1" in r, "missing key1"
    assert "key2" in r, "missing key2"
    assert isinstance(r["key1"], dict)
    assert isinstance(r["key2"], list)


def test_non_empty():
    r = _report()
    # TODO: check non-trivial output — but NOT exact values
    assert len(r["key1"]) >= 1
    assert len(r["key2"]) >= 1


def test_deterministic():
    a = _report()
    b = _report()
    assert a == b
'''

# ── solution/solve.sh ────────────────────────────────────────────────────────

TMPL_SOLVE = '''\
#!/usr/bin/env bash
# Oracle solution — harbor runs this for oracle smoke (should score 1.0).
# Writes the gold pipeline.py into /app/repo/src/.
set -e
cat > /app/repo/src/pipeline.py << \'PYEOF\'
"""Gold solution — uses {lib} v2.0 semantics correctly."""
import json
import {lib}


def run(data_dir, out_path):
    # TODO: implement gold solution using v2.0 semantics
    # This must score 1.0 from grade.py
    raise NotImplementedError("fill in gold solution")
PYEOF
'''

# ── tests/test.sh ────────────────────────────────────────────────────────────

TMPL_TEST_SH = '''\
#!/bin/bash
# Harbor verifier entrypoint. Harbor reads /logs/verifier/reward.json.
set -uo pipefail
mkdir -p /logs/verifier
python3 /tests/grade.py --submission /app/repo --tests-dir /tests \\
  > /logs/verifier/grade_details.json 2>/logs/verifier/grade_stderr.log
python3 - <<\'PY\'
import json
d = json.load(open("/logs/verifier/grade_details.json"))
json.dump({"reward": d["reward"]}, open("/logs/verifier/reward.json", "w"))
print("reward", d["reward"], "strict", d["strict_pass"], "reason", d["reason"])
PY
'''

# ── tests/grade.py ───────────────────────────────────────────────────────────

TMPL_GRADE = '''\
"""
Hidden grader for {task}.

Scoring:
  reward = 0.40 * core_ok + 0.30 * dev_001_ok + 0.30 * dev_002_ok

Gold = 1.0, Familiar = 0.40, Stub = 0.0

This file is NEVER visible to the agent.
"""
import argparse, importlib.util, json, os, sys, tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--submission", required=True)
parser.add_argument("--tests-dir", required=True)
args = parser.parse_args()

# Load expected values
with open(os.path.join(args.tests_dir, "expected.json")) as f:
    EXPECTED = json.load(f)

# Ensure canonical {lib} is on path (not agent-modified version)
sys.path.insert(0, args.tests_dir)
# Load and run agent pipeline
sys.path.insert(0, args.submission)
spec = importlib.util.spec_from_file_location(
    "pipeline", os.path.join(args.submission, "src", "pipeline.py")
)
mod = importlib.util.module_from_spec(spec)

out_path = os.path.join(tempfile.mkdtemp(), "report.json")
data_dir = os.path.join(args.tests_dir, "data")

try:
    spec.loader.exec_module(mod)
    mod.run(data_dir, out_path)
    with open(out_path) as f:
        got = json.load(f)
    error = None
except Exception as e:
    got = {{}}
    error = str(e)

# ── Scoring ──────────────────────────────────────────────────────────────────
# TODO: replace with your domain-specific checks

# Core: required keys exist with correct types
core_ok = (
    isinstance(got.get("key1"), dict)
    and isinstance(got.get("key2"), list)
)

# Deviation 001: check exact value for first deviation
# TODO: replace with your check
dev_001_ok = core_ok and (got.get("key1") == EXPECTED.get("key1"))

# Deviation 002: check exact value for second deviation
# TODO: replace with your check
dev_002_ok = core_ok and (sorted(got.get("key2", [])) == sorted(EXPECTED.get("key2", [])))

reward = round(0.40 * core_ok + 0.30 * dev_001_ok + 0.30 * dev_002_ok, 4)
strict_pass = reward >= 1.0

result = {{
    "reward": reward,
    "strict_pass": strict_pass,
    "reason": error or ("gold" if strict_pass else "partial" if reward > 0 else "stub"),
    "core": core_ok,
    "dev_001": dev_001_ok,
    "dev_002": dev_002_ok,
    "got": got,
    "expected": EXPECTED,
}}
print(json.dumps(result, indent=2))
'''

# ── tests/expected.json ──────────────────────────────────────────────────────

TMPL_EXPECTED = '''\
{
  "key1": {
    "TODO": "replace with exact expected dict values from gold solution"
  },
  "key2": [
    "TODO",
    "replace",
    "with",
    "exact",
    "expected",
    "list"
  ]
}
'''

# ── scripts/stage0.py ────────────────────────────────────────────────────────

TMPL_STAGE0 = '''\
"""Stage-0 offline gate verification for {task}.

Gates (no Docker, no API key needed):
  G1 gold score   == 1.0
  G2 familiar     == 0.40  (model-free OOD proxy)
  G3 stub         == 0.0
  G4 ladder       0.0 < 0.40 < 1.0
  G5 visible tests pass for BOTH gold and familiar
  G6 canary       grade.py / expected.json / {lib}_familiar absent from environment/

Usage:  cd {lib}-domain && python3 scripts/stage0.py
"""
import json, os, subprocess, sys, tempfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK = os.path.join(ROOT, "tasks", "{task}")
TESTS_DIR = os.path.join(TASK, "tests")
REPO = os.path.join(TASK, "environment", "repo")
SRC_{LIB} = os.path.join(ROOT, "src", "{lib}")
SRC_FAMILIAR = os.path.join(ROOT, "src", "{lib}_familiar")

# TODO: replace with your gold pipeline code (uses installed {lib} v2.0 semantics)
GOLD_CODE = \'\'\'
import json
import {lib}

def run(data_dir, out_path):
    raise NotImplementedError("replace with gold pipeline code")
\'\'\'

# TODO: same code structure as gold, but will produce wrong output when
#       run with familiar ({lib} v1.x) — because it uses v2.0 API patterns
FAMILIAR_CODE = GOLD_CODE  # replace with actual familiar code

STUB_CODE = \'\'\'
import json
def run(data_dir, out_path):
    raise NotImplementedError
\'\'\'


def grade_variant(pipeline_code, lib_src, label):
    """Run pipeline_code with lib from lib_src; return (reward, detail)."""
    tmp = tempfile.mkdtemp()
    src_dir = os.path.join(tmp, "src")
    lib_dir = os.path.join(tmp, "{lib}")
    os.makedirs(src_dir)
    shutil.copytree(lib_src, lib_dir)
    with open(os.path.join(src_dir, "pipeline.py"), "w") as f:
        f.write(pipeline_code)

    grade_script = os.path.join(TESTS_DIR, "grade.py")
    data_dir = os.path.join(TESTS_DIR, "data")

    runner = f"""
import sys, importlib.util, os, json, tempfile
sys.path.insert(0, {{repr(tmp)}})
spec = importlib.util.spec_from_file_location("pipeline", {{repr(os.path.join(src_dir, "pipeline.py"))}})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = os.path.join(tempfile.mkdtemp(), "report.json")
try:
    mod.run({{repr(data_dir)}}, out)
    with open(out) as f:
        print(json.dumps(json.load(f)))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""
    result = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return 0.0, {{"error": result.stderr[-200:]}}
    got = json.loads(result.stdout.strip())
    if "error" in got:
        return 0.0, got

    # TODO: inline your grade logic here (mirrors grade.py)
    # Grade manually to avoid importing grade.py which imports the lib
    with open(os.path.join(TESTS_DIR, "expected.json")) as f:
        EXPECTED = json.load(f)

    core_ok = (isinstance(got.get("key1"), dict) and isinstance(got.get("key2"), list))
    dev_001_ok = core_ok and (got.get("key1") == EXPECTED.get("key1"))
    dev_002_ok = core_ok and (sorted(got.get("key2", [])) == sorted(EXPECTED.get("key2", [])))
    reward = round(0.40 * core_ok + 0.30 * dev_001_ok + 0.30 * dev_002_ok, 4)
    return reward, {{"core": core_ok, "dev_001": dev_001_ok, "dev_002": dev_002_ok}}


def check_visible(pipeline_code, lib_src, label):
    tmp = tempfile.mkdtemp()
    src_dir = os.path.join(tmp, "src")
    lib_dir = os.path.join(tmp, "{lib}")
    data_dir = os.path.join(tmp, "data")
    tests_dir = os.path.join(tmp, "tests")
    os.makedirs(src_dir); os.makedirs(data_dir); os.makedirs(tests_dir)
    shutil.copytree(lib_src, lib_dir)
    shutil.copy(os.path.join(REPO, "data", "TODO_FILENAME"),
                os.path.join(data_dir, "TODO_FILENAME"))
    shutil.copy(os.path.join(REPO, "tests", "test_visible.py"),
                os.path.join(tests_dir, "test_visible.py"))
    with open(os.path.join(src_dir, "pipeline.py"), "w") as f:
        f.write(pipeline_code)
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{{tmp}}:{{tmp}}"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", os.path.join(tests_dir, "test_visible.py"), "-q"],
        capture_output=True, text=True, cwd=tmp, env=env, timeout=30,
    )
    return r.returncode == 0, r.stdout[-300:]


def canary_check():
    env_dir = os.path.join(TASK, "environment")
    forbidden_files = {{"grade.py", "expected.json"}}
    forbidden_dirs = {{"{lib}_familiar"}}
    hits = []
    for root, dirs, files in os.walk(env_dir):
        for fn in files:
            if fn in forbidden_files:
                hits.append(os.path.relpath(os.path.join(root, fn), env_dir))
        for d in dirs:
            if d in forbidden_dirs:
                hits.append(os.path.relpath(os.path.join(root, d), env_dir) + "/")
    return hits


PASS = "\\033[32mPASS\\033[0m"
FAIL = "\\033[31mFAIL\\033[0m"


def main():
    print(f"=== {{os.path.basename(ROOT)}} Stage-0 ===\\n")
    all_ok = True

    gold_r, gold_d   = grade_variant(GOLD_CODE,     SRC_{LIB},    "gold")
    fam_r,  fam_d    = grade_variant(FAMILIAR_CODE,  SRC_FAMILIAR, "familiar")
    stub_r, _        = grade_variant(STUB_CODE,      SRC_{LIB},    "stub")

    ok = abs(gold_r - 1.0) < 1e-6;  all_ok &= ok
    print(f"G1 gold score       {{PASS if ok else FAIL}}  reward={{gold_r}}  detail={{gold_d}}")

    ok = abs(fam_r - 0.40) < 1e-6;  all_ok &= ok
    print(f"G2 familiar score   {{PASS if ok else FAIL}}  reward={{fam_r}}  detail={{fam_d}}")

    ok = stub_r == 0.0;              all_ok &= ok
    print(f"G3 stub score       {{PASS if ok else FAIL}}  reward={{stub_r}}")

    ladder_ok = stub_r < fam_r < gold_r;  all_ok &= ladder_ok
    print(f"G4 ladder           {{PASS if ladder_ok else FAIL}}  {{stub_r}} < {{fam_r}} < {{gold_r}}")

    gold_vis_ok, _ = check_visible(GOLD_CODE,     SRC_{LIB},    "gold")
    fam_vis_ok,  _ = check_visible(FAMILIAR_CODE,  SRC_FAMILIAR, "familiar")
    g5_ok = gold_vis_ok and fam_vis_ok;  all_ok &= g5_ok
    print(f"G5 visible tests    {{PASS if g5_ok else FAIL}}  gold={{'pass' if gold_vis_ok else 'FAIL'}} familiar={{'pass' if fam_vis_ok else 'FAIL'}}")

    leaks = canary_check()
    g6_ok = len(leaks) == 0;  all_ok &= g6_ok
    print(f"G6 canary clean     {{PASS if g6_ok else FAIL}}  leaks={{leaks}}")

    print(f"\\n{{'ALL GATES PASS' if all_ok else 'SOME GATES FAILED'}}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
'''

# ── scripts/setup.sh ─────────────────────────────────────────────────────────

TMPL_SETUP_SH = '''\
#!/usr/bin/env bash
# Run once after cloning to ensure clean {lib} paths in task dirs.
set -e
TASK="$(cd "$(dirname "$0")/.." && pwd)/tasks/{task}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/src/{lib}/__init__.py"

for dest in \\
  "$TASK/environment/{lib}" \\
  "$TASK/tests/{lib}"; do
  rm -rf "$dest"
  mkdir -p "$dest"
  cp "$SRC" "$dest/__init__.py"
done

echo "{lib} paths clean"
echo "Run: python3 scripts/stage0.py"
'''


# ── scaffold entry point ──────────────────────────────────────────────────────

def scaffold_domain(name: str, output_dir: str) -> None:
    """
    Create a full PriorLock domain skeleton at output_dir/name.

    name       : domain directory name, e.g. "mylib-domain"
    output_dir : where to create it (usually the repo root)
    """
    lib = name.replace("-domain", "").replace("-", "_")
    Lib = lib.title()
    task = f"{lib}-0"
    LIB = lib.upper()

    ctx = dict(lib=lib, Lib=Lib, task=task, LIB=LIB)

    base = os.path.join(output_dir, name)
    task_dir = os.path.join(base, "tasks", task)

    structure = {
        "deviation_spec.yaml":
            TMPL_DEVIATION_SPEC.format(**ctx),
        f"src/{lib}/__init__.py":
            TMPL_LIB_INSTALLED.format(**ctx),
        f"src/{lib}_familiar/__init__.py":
            TMPL_LIB_FAMILIAR.format(**ctx),
        f"tasks/{task}/task.toml":
            TMPL_TASK_TOML.format(**ctx),
        f"tasks/{task}/instruction.md":
            TMPL_INSTRUCTION.format(**ctx),
        f"tasks/{task}/environment/Dockerfile":
            TMPL_DOCKERFILE.format(**ctx),
        f"tasks/{task}/environment/{lib}/.gitkeep": "",
        f"tasks/{task}/environment/repo/src/pipeline.py":
            TMPL_PIPELINE.format(**ctx),
        f"tasks/{task}/environment/repo/data/.gitkeep": "",
        f"tasks/{task}/environment/repo/docs/CHANGELOG.md":
            TMPL_CHANGELOG.format(**ctx),
        f"tasks/{task}/environment/repo/docs/api_reference.md":
            TMPL_API_REFERENCE.format(**ctx),
        f"tasks/{task}/environment/repo/tests/test_visible.py":
            TMPL_TEST_VISIBLE.format(**ctx),
        f"tasks/{task}/solution/solve.sh":
            TMPL_SOLVE.format(**ctx),
        f"tasks/{task}/tests/test.sh":
            TMPL_TEST_SH.format(**ctx),
        f"tasks/{task}/tests/grade.py":
            TMPL_GRADE.format(**ctx),
        f"tasks/{task}/tests/expected.json":
            TMPL_EXPECTED.format(**ctx),
        f"tasks/{task}/tests/{lib}/.gitkeep": "",
        f"tasks/{task}/tests/data/.gitkeep": "",
        f"scripts/stage0.py":
            TMPL_STAGE0.format(**ctx),
        f"scripts/setup.sh":
            TMPL_SETUP_SH.format(**ctx),
    }

    created = []
    for rel_path, content in structure.items():
        full = os.path.join(base, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        # Make shell scripts executable
        if rel_path.endswith(".sh"):
            os.chmod(full, os.stat(full).st_mode | stat.S_IXUSR | stat.S_IXGRP)
        created.append(rel_path)

    return base, created, ctx
