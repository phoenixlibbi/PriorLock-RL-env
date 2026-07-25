#!/usr/bin/env python3
"""PriorLock probe grader — generated, do not edit by hand.

Scores prior-override capability on the structural ladder {0.0, 0.40, 1.0}.

Threat model and why this design resists reward hacking
-------------------------------------------------------
1. **The verifier owns the library.** Grading imports the pristine copy shipped
   in ``_plx_lib/`` and places it first on ``sys.path``. Whatever the agent did
   to the repo copy is irrelevant to the measurement; tampering is reported as a
   flag but cannot change which code runs.

2. **Call arguments are observed, not self-reported.** Each probe function is
   wrapped and the arguments the solution *explicitly supplied* are recovered via
   ``inspect.Signature.bind``, which excludes defaults. There is no trace file to
   forge and no log the agent can write to.

3. **Bypass scores zero, not 0.40.** An agent that reimplements the function
   instead of calling it never reaches the prior-locked rung. Hand-rolling the
   familiar behaviour is strictly worse than calling the library naively.

4. **Both signals must agree for full credit.** 1.0 requires the correct call
   *and* the correct output. Guessing the expected output without making the
   correct call does not score.
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

LIB = "datawright"
PROBES = json.loads("[{\"id\": \"tie_inclusive_topk\", \"family\": \"result_shape\", \"category\": \"collection\", \"fn\": \"top_k\", \"param\": null, \"gold_kwargs\": {}, \"familiar_kwargs\": {}, \"output_key\": \"topIds\", \"gold_output\": [3, 4, 5, 7], \"familiar_output\": [3, 4, 5], \"weight\": 1.0}, {\"id\": \"null_key_policy\", \"family\": \"default_flip\", \"category\": \"collection\", \"fn\": \"bucket\", \"param\": \"nulls\", \"gold_kwargs\": {\"nulls\": \"drop\"}, \"familiar_kwargs\": {}, \"output_key\": \"bucketCounts\", \"gold_output\": {\"eu\": 2, \"us\": 1}, \"familiar_output\": {\"eu\": 2, \"__unset__\": 2, \"us\": 1}, \"weight\": 1.0}, {\"id\": \"merge_precedence_remap\", \"family\": \"value_remap\", \"category\": \"mapping\", \"fn\": \"merge\", \"param\": \"on_conflict\", \"gold_kwargs\": {\"on_conflict\": \"keep_left\"}, \"familiar_kwargs\": {\"on_conflict\": \"keep\"}, \"output_key\": \"merged\", \"gold_output\": {\"a\": 1, \"b\": 2, \"c\": 3}, \"familiar_output\": {\"a\": 1, \"b\": 99, \"c\": 3}, \"weight\": 1.0}]")
VISIBLE_LIB_SHA256 = "98759068345a5a3ff1a9986cb0adbcb5b8441d864f1399c4f8a78603f0bd911a"
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


def instrument(module, probes, recorder):
    """Wrap each probe function so explicitly-supplied arguments are recorded."""
    for spec in probes:
        name = spec["fn"]
        original = getattr(module, name)
        signature = inspect.signature(original)

        def make(name, original, signature):
            def wrapper(*args, **kwargs):
                try:
                    bound = signature.bind(*args, **kwargs)
                    supplied = dict(bound.arguments)
                except TypeError:
                    supplied = dict(kwargs)
                # keep only JSON-safe scalars; container args are not discriminating
                clean = {
                    k: v for k, v in supplied.items()
                    if isinstance(v, (str, int, float, bool, type(None)))
                }
                recorder.setdefault(name, []).append(clean)
                return original(*args, **kwargs)
            wrapper.__name__ = name
            wrapper.__doc__ = original.__doc__
            wrapper.__signature__ = signature
            return wrapper

        setattr(module, name, make(name, original, signature))


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

    # A solution may call a helper more than once; credit the best call.
    any_gold_call = any(call_is_gold(spec, s) for s in invocations)

    detail = {
        "calls": len(invocations),
        "supplied": invocations,
        "gold_call": any_gold_call,
        "output_matches": ("gold" if got == gold else
                           "familiar" if got == familiar else "neither"),
    }

    if got == gold and any_gold_call:
        return 1.0, "override", detail
    if got == familiar:
        return FAMILIAR_BASELINE, "prior_locked", detail
    if any_gold_call:
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
        "lib": LIB,
    }

    # 1. integrity — report tampering, then ignore the agent's copy entirely
    visible_lib = os.path.join(submission, LIB, "__init__.py")
    observed = sha256_file(visible_lib)
    if observed is None:
        report["flags"].append("library_removed")
    elif VISIBLE_LIB_SHA256 and observed != VISIBLE_LIB_SHA256:
        report["flags"].append("library_modified")

    # 2. pristine library wins sys.path
    pristine = os.path.join(tests_dir, "_plx_lib")
    sys.path.insert(0, pristine)
    for stale in [m for m in sys.modules if m == LIB or m.startswith(LIB + ".")]:
        del sys.modules[stale]
    try:
        lib_module = importlib.import_module(LIB)
    except Exception as exc:                                    # pragma: no cover
        report["flags"].append("pristine_import_failed:%s" % exc)
        emit(report)
        return 0
    lib_file = getattr(lib_module, "__file__", "") or ""
    if not os.path.abspath(lib_file).startswith(pristine):
        report["flags"].append("shadowed_library_import")

    # 3. instrument, then load the agent's solution (patch first so that
    #    `from LIB import fn` at solution-import time still resolves to the wrapper)
    calls = {}
    instrument(lib_module, PROBES, calls)

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

    sys.path.insert(1, submission)
    out_path = os.path.join(tests_dir, "_plx_observed_output.json")
    produced = None
    try:
        spec_obj = importlib.util.spec_from_file_location("_plx_solution", solution_path)
        mod = importlib.util.module_from_spec(spec_obj)
        sys.modules["_plx_solution"] = mod
        spec_obj.loader.exec_module(mod)
        if not callable(getattr(mod, "run", None)):
            report["flags"].append("solution_has_no_run")
        else:
            mod.run(data_path, out_path)
            with open(out_path) as f:
                produced = json.load(f)
    except Exception:
        report["flags"].append("solution_crashed")
        report["traceback"] = traceback.format_exc()[-1500:]

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

# oracle canary — verifier-side only: PLXCANARY-868C0937A4E150B6E006EA41
