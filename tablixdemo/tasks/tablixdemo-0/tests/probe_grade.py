#!/usr/bin/env python3
"""PriorLock probe grader — generated, do not edit by hand.

Scores prior-override capability on the structural ladder {0.0, 0.40, 1.0}.

Threat model and why this design resists reward hacking
-------------------------------------------------------
1. **The verifier owns the library.** Grading imports the pristine copy shipped
   in ``_plx_lib/`` and places it first on ``sys.path``. Whatever the agent did
   to the repo copy is irrelevant to the measurement; tampering is reported as a
   flag but cannot change which code runs.

2. **The solution never runs inside the grader.** It runs in a child process
   (``python -I``, empty environment) that only records which arguments each
   probed function received. The grader ignores everything the child prints and
   reads its own report from memory. While the child runs, every answer-bearing
   file (this grader, the reference solutions) is removed from disk, and when the
   grader runs as root the child drops to ``nobody`` and the tests directory is
   made private. A solution therefore cannot patch the scorer, print a report,
   or read the expected answers.

   Arguments the solution *explicitly supplied* are recovered via
   ``inspect.Signature.bind``, which excludes defaults.

3. **Bypass scores zero, not 0.40.** An agent that reimplements the function
   instead of calling it never reaches the prior-locked rung. Hand-rolling the
   familiar behaviour is strictly worse than calling the library naively.

4. **Both signals must agree for full credit.** 1.0 requires the correct call,
   made *consistently* (every call to the probed function passes the same value
   for the probed argument), *and* the correct output. Trying several values and
   keeping whichever works is scored 0. A correct output reached some other way
   earns the 0.40 baseline, never more, so hand-writing the answer is no better
   than not reading the docs at all.
"""

import argparse
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import sys
import traceback

LIB = "datakit"
PROBES = json.loads("[{\"id\": \"tie_inclusive_topk\", \"family\": \"result_shape\", \"category\": \"collection\", \"fn\": \"top_k\", \"param\": null, \"gold_kwargs\": {}, \"familiar_kwargs\": {}, \"output_key\": \"topIds\", \"gold_output\": [403, 404, 405, 407], \"familiar_output\": [403, 404, 405], \"weight\": 1.0}, {\"id\": \"null_key_policy\", \"family\": \"default_flip\", \"category\": \"collection\", \"fn\": \"bucket\", \"param\": \"nulls\", \"gold_kwargs\": {\"nulls\": \"drop\"}, \"familiar_kwargs\": {}, \"output_key\": \"bucketCounts\", \"gold_output\": {\"renvo\": 2, \"miren\": 1}, \"familiar_output\": {\"renvo\": 2, \"__unset__\": 2, \"miren\": 1}, \"weight\": 1.0}, {\"id\": \"merge_precedence_remap\", \"family\": \"value_remap\", \"category\": \"mapping\", \"fn\": \"merge\", \"param\": \"on_conflict\", \"gold_kwargs\": {\"on_conflict\": \"keep_left\"}, \"familiar_kwargs\": {\"on_conflict\": \"keep\"}, \"output_key\": \"merged\", \"gold_output\": {\"a\": 401, \"b\": 402, \"c\": 403}, \"familiar_output\": {\"a\": 401, \"b\": 499, \"c\": 403}, \"weight\": 1.0}]")
VISIBLE_LIB_SHA256 = "546aa2684043e3eff5171b9231712df12f1663a3f9082ff4427209ac6185d9c1"
SOLUTION_NAME = "probe_solution.py"
INPUT_NAME = "data/probe_input.json"
FAMILIAR_BASELINE = 0.40


# ── helpers ──────────────────────────────────────────────────────────────────

def sha256_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def canon(value):
    """Normalise for comparison: JSON round-trip collapses tuples and int/float."""
    return json.loads(json.dumps(value, sort_keys=True, default=str))


CHILD_SOURCE = """
import importlib, importlib.util, inspect, json, os, sys, traceback
lib_dir, lib_name, sol_path, data_path, out_path, rec_path, fns = sys.argv[1:8]
fns = json.loads(fns)
sys.path.insert(0, lib_dir)
calls, error = {}, None
try:
    lib = importlib.import_module(lib_name)
    for name in fns:
        original = getattr(lib, name)
        signature = inspect.signature(original)
        def make(name, original, signature):
            def wrapper(*args, **kwargs):
                try:
                    supplied = dict(signature.bind(*args, **kwargs).arguments)
                except TypeError:
                    supplied = dict(kwargs)
                calls.setdefault(name, []).append({
                    k: v for k, v in supplied.items()
                    if isinstance(v, (str, int, float, bool, type(None)))})
                return original(*args, **kwargs)
            wrapper.__name__ = name
            wrapper.__doc__ = original.__doc__
            wrapper.__signature__ = signature
            return wrapper
        setattr(lib, name, make(name, original, signature))
    sys.path.insert(1, os.path.dirname(sol_path))
    spec = importlib.util.spec_from_file_location("_plx_solution", sol_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_plx_solution"] = mod
    spec.loader.exec_module(mod)
    mod.run(data_path, out_path)
except BaseException:
    error = traceback.format_exc()[-1500:]
finally:
    with open(rec_path, "w") as f:
        json.dump({"calls": calls, "error": error}, f, default=str)
"""


ANSWER_FILES = ("probe_grade.py", "_plx_reference")
CHILD_TIMEOUT = float(os.environ.get("PLX_CHILD_TIMEOUT", "60"))


def hide_answers(tests_dir):
    # Read every answer-bearing file into memory and remove it from disk.
    hidden = []
    for name in ANSWER_FILES:
        root = os.path.join(tests_dir, name)
        paths = [root] if os.path.isfile(root) else [
            os.path.join(d, f) for d, _s, fs in os.walk(root) for f in fs]
        for path in paths:
            try:
                with open(path, "rb") as f:
                    data = f.read()
                mode = os.stat(path).st_mode
                os.remove(path)
                hidden.append((path, data, mode))
            except OSError:
                pass
    return hidden


def restore_answers(hidden):
    for path, data, mode in hidden:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        os.chmod(path, mode & 0o7777)


def run_isolated(tests_dir, submission, solution_path, data_path, flags, notes):
    # Run the solution in a child process; return (output, calls).
    import shutil, subprocess, tempfile
    work = tempfile.mkdtemp(prefix="plx-run-")
    os.chmod(work, 0o777)
    lib_dir = os.path.join(work, "lib")
    shutil.copytree(os.path.join(tests_dir, "_plx_lib"), lib_dir)
    child = os.path.join(work, "child.py")
    with open(child, "w") as f:
        f.write(CHILD_SOURCE)
    sol_copy = os.path.join(work, "sol", os.path.basename(solution_path))
    os.makedirs(os.path.dirname(sol_copy))
    shutil.copy2(solution_path, sol_copy)
    out_path = os.path.join(work, "out", "observed.json")
    rec_path = os.path.join(work, "out", "record.json")
    os.makedirs(os.path.dirname(out_path))
    for d, ds, fs in os.walk(work):
        for x in ds:
            os.chmod(os.path.join(d, x), 0o777)
        for x in fs:
            os.chmod(os.path.join(d, x), 0o666)

    as_root = hasattr(os, "geteuid") and os.geteuid() == 0
    tests_mode = os.stat(tests_dir).st_mode
    preexec = None
    if as_root:
        os.chmod(tests_dir, 0o700)
        def preexec():
            os.setgid(65534)
            os.setuid(65534)
    else:
        notes.append("unprivileged_grading: answers hidden from disk, child runs as the same user")
    hidden = hide_answers(tests_dir)
    try:
        subprocess.run(
            [sys.executable, "-I", child, lib_dir, LIB, sol_copy, data_path,
             out_path, rec_path, json.dumps(sorted({p["fn"] for p in PROBES}))],
            cwd=submission, env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0"},
            stdout=subprocess.DEVNULL,       # never part of the report
            timeout=CHILD_TIMEOUT, preexec_fn=preexec)
    except subprocess.TimeoutExpired:
        flags.append("solution_timeout")
    finally:
        restore_answers(hidden)
        if as_root:
            os.chmod(tests_dir, tests_mode & 0o7777)

    calls, produced = {}, None
    try:
        with open(rec_path) as f:
            rec = json.load(f)
        calls = rec.get("calls") or {}
        if rec.get("error"):
            flags.append("solution_crashed")
    except (OSError, ValueError):
        flags.append("no_record")
    try:
        with open(out_path) as f:
            produced = json.load(f)
    except (OSError, ValueError):
        pass
    shutil.rmtree(work, ignore_errors=True)
    if not isinstance(calls, dict):
        calls = {}
    return produced, calls


def call_is_gold(spec, supplied):
    if spec["family"] == "result_shape":
        return True
    param = spec["param"]
    want = spec["gold_kwargs"][param]
    return param in supplied and supplied[param] == want


def score_probe(spec, calls, output_present, output):
    """Return (score, verdict, detail)."""
    invocations = calls.get(spec["fn"], [])
    if not invocations:
        return 0.0, "bypassed", {"calls": 0}
    if not output_present:
        return 0.0, "absent", {"calls": len(invocations)}

    gold = canon(spec["gold_output"])
    familiar = canon(spec["familiar_output"])
    got = canon(output)

    # Every call must agree on the probed argument: trying several values and
    # keeping whichever works is not reading the docs.
    gold_call = all(call_is_gold(spec, s) for s in invocations)
    detail = {
        "calls": len(invocations),
        "supplied": invocations,
        "gold_call": gold_call,
        "output_matches": ("gold" if got == gold else
                           "familiar" if got == familiar else "neither"),
    }
    if spec["family"] != "result_shape":
        values = {json.dumps(s.get(spec["param"], "<default>"), sort_keys=True)
                  for s in invocations}
        if len(values) > 1:
            return 0.0, "inconsistent_calls", detail

    if got == gold and gold_call:
        return 1.0, "override", detail
    if got == familiar:
        return FAMILIAR_BASELINE, "prior_locked", detail
    if got == gold:
        # correct output by another route: never below the baseline, never above
        return FAMILIAR_BASELINE, "correct_output_other_call", detail
    if gold_call:
        return 0.0, "correct_call_bad_output", detail
    return 0.0, "incorrect", detail


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True, help="agent repo root")
    ap.add_argument("--tests-dir", required=True, help="verifier tests dir")
    args = ap.parse_args()

    tests_dir = os.path.abspath(args.tests_dir)
    submission = os.path.abspath(args.submission)

    report = {
        "gap_score": 0.0,
        "probes": [],
        "flags": [],
        "notes": [],
        "lib": LIB,
    }

    # 1. integrity — report tampering, then ignore the agent's copy entirely
    visible_lib = os.path.join(submission, LIB, "__init__.py")
    observed = sha256_file(visible_lib)
    if observed is None:
        report["flags"].append("library_removed")
    elif VISIBLE_LIB_SHA256 and observed != VISIBLE_LIB_SHA256:
        report["flags"].append("library_modified")

    # 2. the pristine library must import cleanly (the child imports it again)
    pristine = os.path.join(tests_dir, "_plx_lib")
    if not os.path.isfile(os.path.join(pristine, LIB, "__init__.py")):
        report["flags"].append("pristine_library_missing")

    solution_path = os.path.join(submission, SOLUTION_NAME)
    data_path = os.path.join(submission, INPUT_NAME)
    if not os.path.isfile(data_path):
        data_path = os.path.join(tests_dir, os.path.basename(INPUT_NAME))

    if not os.path.isfile(solution_path):
        report["flags"].append("solution_missing")
        for spec in PROBES:
            report["probes"].append({
                "id": spec["id"], "score": 0.0, "verdict": "absent",
                "family": spec["family"], "weight": spec["weight"], "detail": {},
            })
        finish(report)
        return 0

    # 3. run the solution in an isolated child process
    produced, calls = run_isolated(tests_dir, submission, solution_path,
                                   data_path, report["flags"], report["notes"])

    # 4. score
    for spec in PROBES:
        key = spec["output_key"]
        present = isinstance(produced, dict) and key in produced
        value = produced.get(key) if present else None
        score, verdict, detail = score_probe(spec, calls, present, value)
        report["probes"].append({
            "id": spec["id"],
            "family": spec["family"],
            "category": spec["category"],
            "output_key": key,
            "score": score,
            "verdict": verdict,
            "weight": spec["weight"],
            "detail": detail,
        })

    finish(report)
    return 0


def finish(report):
    weights = [p["weight"] for p in report["probes"]] or [1.0]
    total_w = sum(weights) or 1.0
    report["gap_score"] = round(
        sum(p["score"] * p["weight"] for p in report["probes"]) / total_w, 4
    )
    verdicts = [p["verdict"] for p in report["probes"]]
    report["verdict_counts"] = {v: verdicts.count(v) for v in sorted(set(verdicts))}
    report["prior_locked_probes"] = [
        p["id"] for p in report["probes"] if p["verdict"] == "prior_locked"
    ]
    report["overridden_probes"] = [
        p["id"] for p in report["probes"] if p["verdict"] == "override"
    ]
    emit(report)


def emit(report):
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    sys.exit(main())

# oracle canary — verifier-side only: PLXCANARY-8D38A2DB47E803441660F7C8
