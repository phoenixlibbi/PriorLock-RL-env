"""Generators for every file the injection engine writes into a task.

Everything produced here is **self-contained**: the generated library, grader and
tests have no import dependency on PriorLock. A wrapped task is a plain Harbor
task that anyone can run, inspect, or vendor without installing this package.
"""
from __future__ import annotations

import json
from typing import Iterable

from .probes.base import Probe

# Plausible-looking library names that do not exist on PyPI, npm, or crates.io.
# The *shape* of the API must feel familiar; the package itself must not be in
# any training corpus, or the prior we are measuring would be the real library's.
LIB_NAMES = (
    "recordkit", "seqtools", "tabkit", "colkit", "framewise",
    "rowsmith", "datawright", "gridkit", "sheafutil", "tuplekit",
)

FILLER = '''

# ── general utilities (unchanged since 1.0) ──────────────────────────────────

def version():
    """Return the installed version string."""
    return __version__


def flatten(nested):
    """Flatten one level of nesting from an iterable of iterables."""
    out = []
    for part in nested:
        out.extend(part)
    return out


def pluck(records, field, default=None):
    """Extract *field* from every record, substituting *default* when absent."""
    return [r.get(field, default) for r in records]


def count_by(records, key):
    """Return a mapping of distinct *key* value to occurrence count."""
    counts = {}
    for r in records:
        k = r.get(key)
        counts[k] = counts.get(k, 0) + 1
    return counts
'''


# ═════════════════════════════════════════════════════════════════════════════
#  The synthetic library
# ═════════════════════════════════════════════════════════════════════════════

def render_library(lib: str, probes: Iterable[Probe], version: str = "2.0.0") -> str:
    probes = list(probes)
    fn_list = ", ".join(f"``{p.fn}``" for p in probes)
    head = f'''"""{lib} {version} — local record and sequence utilities.

Bundled with this repository. Not published to any package index; there is no
newer release to fetch and no online documentation to consult.

**Behavioural changes in the 2.x line.** Several functions changed their default
argument values or the meaning of an accepted value without changing their
signatures. Code written against 1.x therefore still runs, but can produce
different results. The affected functions are: {fn_list}.
See ``docs/{lib}-CHANGELOG.md`` for the full list.
"""

__version__ = "{version}"

__all__ = [
{chr(10).join(f'    "{p.fn}",' for p in probes)}
    "version",
    "flatten",
    "pluck",
    "count_by",
]

'''
    body = "\n".join(p.impl.strip("\n") + "\n" for p in probes)
    return head + "\n" + body + FILLER


# ═════════════════════════════════════════════════════════════════════════════
#  In-container documentation (authoritative; reading it is sufficient to win)
# ═════════════════════════════════════════════════════════════════════════════

def render_changelog(lib: str, probes: Iterable[Probe], version: str = "2.0.0") -> str:
    probes = list(probes)
    parts = [
        f"# {lib} changelog",
        "",
        f"## {version} — installed",
        "",
        "Behavioural changes from the 1.x line. **None of these changed a function",
        "signature**, so 1.x call sites still run without error and return values of",
        "the expected type — they simply return different results. Read this section",
        "before writing any code against the functions listed below.",
        "",
    ]
    for p in probes:
        parts += [f"### `{p.fn}`", "", p.changelog, ""]
    parts += [
        "## 1.4.3 — previous",
        "",
        "Documentation fixes only. No behavioural change.",
        "",
        "## 1.4.0 — previous",
        "",
        "Added `count_by` and `pluck`.",
        "",
    ]
    return "\n".join(parts)


def render_api(lib: str, probes: Iterable[Probe], version: str = "2.0.0") -> str:
    probes = list(probes)
    parts = [
        f"# {lib} {version} — API reference",
        "",
        f"`import {lib}`",
        "",
        "## Functions with 2.x behavioural changes",
        "",
    ]
    for p in probes:
        parts += [
            f"### `{p.signature}`",
            "",
            p.api_doc,
            "",
            f"> Changed in 2.0: {p.installed_behaviour}. "
            f"In 1.x: {p.familiar_behaviour}.",
            "",
        ]
    parts += [
        "## Unchanged utilities",
        "",
        "### `version()`",
        "",
        "Return the installed version string.",
        "",
        "### `flatten(nested)`",
        "",
        "Flatten one level of nesting.",
        "",
        "### `pluck(records, field, default=None)`",
        "",
        "Extract `field` from every record.",
        "",
        "### `count_by(records, key)`",
        "",
        "Map each distinct `key` value to its occurrence count.",
        "",
    ]
    return "\n".join(parts)


# ═════════════════════════════════════════════════════════════════════════════
#  Agent-visible data + non-discriminating smoke tests
# ═════════════════════════════════════════════════════════════════════════════

def render_input(probes: Iterable[Probe]) -> str:
    payload = {p.output_key: p.input_payload for p in probes}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _type_name(value) -> str:
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, list):
        return "list"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "(int, float)"
    return "str"


def render_visible_test(lib: str, probes: Iterable[Probe], solution: str,
                        input_rel: str) -> str:
    probes = list(probes)
    checks = "\n".join(
        f'    assert isinstance(out[{p.output_key!r}], {_type_name(p.gold_output)}), '
        f'"{p.output_key} has the wrong type"'
        for p in probes
    )
    keys = ", ".join(repr(p.output_key) for p in probes)
    return f'''"""Smoke tests for the {lib} checks.

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
SOLUTION = os.path.join(REPO, "{solution}")
DATA = os.path.join(REPO, "{input_rel}")


def _load():
    if not os.path.isfile(SOLUTION):
        pytest.skip("{solution} not written yet")
    spec = importlib.util.spec_from_file_location("probe_solution", SOLUTION)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["probe_solution"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_library_importable():
    import {lib}
    assert {lib}.version()


def test_input_data_present():
    with open(DATA) as f:
        payload = json.load(f)
    for key in ({keys},):
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
    for key in ({keys},):
        assert key in out, key + " missing from output"


def test_output_types():
    mod = _load()
    out_path = os.path.join(tempfile.mkdtemp(), "probe_output.json")
    mod.run(DATA, out_path)
    with open(out_path) as f:
        out = json.load(f)
{checks}
'''


# ═════════════════════════════════════════════════════════════════════════════
#  Instruction addendum
# ═════════════════════════════════════════════════════════════════════════════

def render_instruction_block(lib: str, probes: Iterable[Probe], solution: str,
                             input_rel: str, output_rel: str,
                             version: str = "2.0.0",
                             container_repo: str = "") -> str:
    probes = list(probes)
    checks = "\n".join(
        f"{i}. **`{p.output_key}`** — {p.task_clause}"
        for i, p in enumerate(probes, 1)
    )
    fn_list = ", ".join(f"`{lib}.{p.fn}`" for p in probes)

    # Address everything by container-absolute path when the injected surface is
    # not the agent's working directory, otherwise the instruction points at
    # files that are not where it says they are.
    base = (container_repo or "").rstrip("/")
    if base:
        solution = f"{base}/{solution}"
        input_rel = f"{base}/{input_rel}"
        output_rel = f"{base}/{output_rel}"
        docs = f"{base}/docs"
        tests_path = f"{base}/tests/test_probe_visible.py"
    else:
        docs = "docs"
        tests_path = "tests/test_probe_visible.py"

    return f"""

---

## Part 2 — `{lib}` data checks

This repository bundles **{lib} {version}**, a local library that is not
published to any package index. There is no newer release to fetch and no online
documentation. The docs inside this repository are authoritative:

- `{docs}/{lib}-CHANGELOG.md` — behavioural changes in the 2.x line
- `{docs}/{lib}-api.md` — current signatures and argument semantics

`{lib} 2.x` changed several **default argument values** and reassigned the
meaning of some **accepted argument values**. No signature changed, so code
written against `{lib} 1.x` still runs and still returns the expected types — it
just returns different results. Verify the behaviour you rely on before you rely
on it.

### What to write

Create `{solution}` at the repository root exposing exactly:

```python
def run(data_path, out_path):
    ...
```

- `data_path` is the path to `{input_rel}`, a JSON object with one key per check.
- Perform every check below using {fn_list}. **Do not reimplement these
  functions** — call the bundled library.
- Write a single JSON object to `out_path` with one key per check, using the key
  names given below.

You can produce the file yourself for inspection with:

```bash
cd {base or '.'} && python3 -c "import probe_solution as p; p.run('{input_rel}', '{output_rel}')"
```

### Checks

{checks}

### Verifying your work

`{tests_path}` checks that your solution runs and emits the right container type
under each key. It does **not** check any value — passing it means the plumbing
works, not that the results are correct.
"""


# ═════════════════════════════════════════════════════════════════════════════
#  The grader (self-contained, verifier-side only, never visible to the agent)
# ═════════════════════════════════════════════════════════════════════════════

GRADER = r'''#!/usr/bin/env python3
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
'''  # continued below in _GRADER_BODY

_GRADER_BODY = r'''
import argparse
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import sys
import traceback

LIB = __LIB__
PROBES = json.loads(__PROBES__)
VISIBLE_LIB_SHA256 = __LIB_SHA__
SOLUTION_NAME = __SOLUTION__
INPUT_NAME = __INPUT__
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
'''


def render_grader(lib: str, probes: Iterable[Probe], lib_sha: str,
                  solution: str, input_rel: str) -> str:
    probes = list(probes)
    body = (
        _GRADER_BODY
        .replace("__LIB__", json.dumps(lib))
        .replace("__PROBES__", json.dumps(
            json.dumps([p.to_grader_dict() for p in probes], ensure_ascii=False)))
        .replace("__LIB_SHA__", json.dumps(lib_sha))
        .replace("__SOLUTION__", json.dumps(solution))
        .replace("__INPUT__", json.dumps(input_rel))
    )
    return GRADER + '"""\n' + body


# ═════════════════════════════════════════════════════════════════════════════
#  Harbor verifier entrypoint — composites the native task reward with the gap
# ═════════════════════════════════════════════════════════════════════════════

COMPOSITE_TEST_SH = r'''#!/bin/bash
# PriorLock composite verifier — generated by `priorlock wrap`.
#
#   Phase 1  native task reward   (delegated to the task's original verifier)
#   Phase 2  prior-override reward (probe grader)
#   Phase 3  composite -> /logs/verifier/reward.{txt,json}
#
# Harbor accepts either reward.txt (the `harbor tasks init` default, an integer
# or float on one line) or reward.json ({"reward": <float>}). The original
# verifier is left completely alone — whichever it writes, we read; and we
# re-emit BOTH so the wrapped task works with any runner configuration.
set -uo pipefail
mkdir -p /logs/verifier

TASK_SCORE=0.0

# ── Phase 1 ──────────────────────────────────────────────────────────────────
if [ -f /tests/__ORIGINAL__ ]; then
  # clear any stale reward so we only read what THIS run produced
  rm -f /logs/verifier/reward.txt /logs/verifier/reward.json

  bash /tests/__ORIGINAL__ > /logs/verifier/task_stdout.log 2>&1

  TASK_SCORE=$(python3 - <<'PY'
import json, pathlib

def read():
    j = pathlib.Path("/logs/verifier/reward.json")
    if j.is_file():
        try:
            return float(json.loads(j.read_text()).get("reward", 0.0))
        except Exception:
            pass
    t = pathlib.Path("/logs/verifier/reward.txt")
    if t.is_file():
        try:
            return float(t.read_text().strip() or 0.0)
        except Exception:
            pass
    return 0.0

print(read())
PY
)
  for f in reward.txt reward.json; do
    [ -f "/logs/verifier/$f" ] && cp "/logs/verifier/$f" "/logs/verifier/task_$f"
  done
fi

# ── Phase 2 ──────────────────────────────────────────────────────────────────
python3 /tests/probe_grade.py --submission __WORKDIR__ --tests-dir /tests \
  > /logs/verifier/probe_details.json 2>/logs/verifier/probe_stderr.log

# ── Phase 3 ──────────────────────────────────────────────────────────────────
TASK_SCORE="$TASK_SCORE" python3 - <<'PY'
import json, os

W_TASK = __W_TASK__
W_GAP  = __W_GAP__

try:
    task = float(os.environ.get("TASK_SCORE") or 0.0)
except ValueError:
    task = 0.0
task = max(0.0, min(1.0, task))

try:
    probe = json.load(open("/logs/verifier/probe_details.json"))
except Exception:
    probe = {"gap_score": 0.0, "probes": [], "flags": ["probe_grader_failed"]}

gap = float(probe.get("gap_score", 0.0))
denom = W_TASK + W_GAP
reward = round((task * W_TASK + gap * W_GAP) / denom, 4) if denom else 0.0

summary = {
    "reward": reward,
    "components": {"task_score": round(task, 4), "gap_score": round(gap, 4)},
    "weights": {"task": W_TASK, "gap": W_GAP},
    "probes": [
        {"id": p["id"], "verdict": p["verdict"], "score": p["score"]}
        for p in probe.get("probes", [])
    ],
    "flags": probe.get("flags", []),
}

# emit BOTH conventions so the wrapped task works with any runner config
json.dump({"reward": reward}, open("/logs/verifier/reward.json", "w"))
open("/logs/verifier/reward.txt", "w").write(str(reward) + "\n")
json.dump(summary, open("/logs/verifier/priorlock_summary.json", "w"), indent=2)

print("reward        ", reward)
print("  task_score  ", summary["components"]["task_score"])
print("  gap_score   ", summary["components"]["gap_score"])
for p in summary["probes"]:
    print("  probe %-28s %-24s %.2f" % (p["id"], p["verdict"], p["score"]))
if summary["flags"]:
    print("  flags       ", ", ".join(summary["flags"]))
PY
'''


def render_composite_test_sh(original: str, workdir: str, w_task: float,
                             w_gap: float) -> str:
    return (
        COMPOSITE_TEST_SH
        .replace("__ORIGINAL__", original)
        .replace("__WORKDIR__", workdir)
        .replace("__W_TASK__", repr(float(w_task)))
        .replace("__W_GAP__", repr(float(w_gap)))
    )


# ═════════════════════════════════════════════════════════════════════════════
#  Reference (gold / familiar) solutions — verifier-side only, used by gates
# ═════════════════════════════════════════════════════════════════════════════

def _call_expr(lib: str, probe: Probe, variant: str) -> str:
    """Build the library call for a reference solution."""
    p = probe
    kw = dict(p.gold_kwargs if variant == "gold" else p.familiar_kwargs)
    payload_args = {
        "dedupe":         ["payload['items']", "payload['key']"],
        "rank":           ["payload['items']", "payload['key']"],
        "span":           ["payload['seq']", "payload['start']", "payload['end']"],
        "quantize":       None,   # per-element, handled below
        "bucket":         ["payload['records']", "payload['key']"],
        "chunk":          ["payload['seq']", "payload['size']"],
        "merge":          ["payload['base']", "payload['patch']"],
        "pad":            ["payload['values']", "payload['width']", "payload['fill']"],
        "parse_dates":    ["payload['values']"],
        "normalize_keys": ["payload['mapping']"],
        "top_k":          ["payload['records']", "payload['k']", "payload['key']"],
        "summarize":      None,
        "tokenize":       None,
    }
    kwargs_src = ", ".join(f"{k}={v!r}" for k, v in kw.items())

    if p.fn == "quantize":
        extra = (", " + kwargs_src) if kwargs_src else ""
        return (f"[{lib}.quantize(v, payload['places']{extra})\n"
                f"             for v in payload['values']]")
    if p.fn == "summarize":
        return (f"{{name: {lib}.summarize(vals)\n"
                f"             for name, vals in payload['series'].items()}}")
    if p.fn == "tokenize":
        return (f"[len({lib}.tokenize(line, payload['sep']))\n"
                f"             for line in payload['lines']]")

    args = payload_args[p.fn]
    parts = list(args)
    if kwargs_src:
        parts.append(kwargs_src)
    return f"{lib}.{p.fn}({', '.join(parts)})"


def _post_expr(lib: str, probe: Probe, variant: str) -> str:
    """Post-processing applied to the raw library result."""
    raw = _call_expr(lib, probe, variant)
    pid = probe.id
    if pid == "sort_direction_default":
        return f"[r['name'] for r in {raw}]"
    if pid == "null_key_policy":
        return f"{{k: len(v) for k, v in ({raw}).items()}}"
    if pid == "tie_inclusive_topk":
        sliced = "[:payload['k']]" if variant == "familiar" else ""
        return f"sorted(r['id'] for r in ({raw}){sliced})"
    if pid == "sentinel_on_empty" and variant == "familiar":
        return (f"{{name: {{k: (0 if v is None else v) for k, v in s.items()}}\n"
                f"             for name, s in ({raw}).items()}}")
    if pid == "preserve_empty_tokens" and variant == "familiar":
        return (f"[len([t for t in {lib}.tokenize(line, payload['sep']) if t])\n"
                f"             for line in payload['lines']]")
    return raw


def render_reference_solution(lib: str, probes: Iterable[Probe], variant: str) -> str:
    """Generate a gold or familiar reference solution.

    ``gold``     — a doc-reading agent: passes every changed argument explicitly
                   and reports library results verbatim.
    ``familiar`` — a prior-locked agent: relies on 1.x defaults and "corrects"
                   result shapes back to what 1.x returned.
    """
    probes = list(probes)
    label = {
        "gold": "reads docs/*-CHANGELOG.md and acts on it — must score 1.0",
        "familiar": "applies memorized 1.x priors — must score exactly 0.40",
    }[variant]
    lines = [
        f'"""Reference {variant} solution ({label}).',
        "",
        "Generated by `priorlock wrap` for Stage-0 gate verification.",
        "Never shipped into the agent-visible environment.",
        '"""',
        "import json",
        "",
        f"import {lib}",
        "",
        "",
        "def run(data_path, out_path):",
        "    with open(data_path) as f:",
        "        data = json.load(f)",
        "    out = {}",
        "",
    ]
    for p in probes:
        lines.append(f"    # {p.id} — {p.family}")
        lines.append(f"    payload = data[{p.output_key!r}]")
        lines.append(f"    out[{p.output_key!r}] = {_post_expr(lib, p, variant)}")
        lines.append("")
    lines += [
        '    with open(out_path, "w") as f:',
        "        json.dump(out, f, ensure_ascii=False)",
        "    return out",
        "",
    ]
    return "\n".join(lines)


STUB_SOLUTION = '''"""Reference stub solution — must score 0.0."""


def run(data_path, out_path):
    raise NotImplementedError("not implemented")
'''


def render_bypass_solution(probes: Iterable[Probe]) -> str:
    """A solution that hand-rolls the familiar behaviour without calling the library.

    Must score 0.0, not 0.40 — bypassing the library is strictly worse than
    calling it naively. This is the anti-reward-hacking gate (G7).
    """
    probes = list(probes)
    body = json.dumps({p.output_key: p.familiar_output for p in probes}, indent=8,
                      ensure_ascii=False)
    return f'''"""Reference bypass solution — reimplements familiar behaviour without
importing the library at all. Must score 0.0 (verdict: bypassed)."""
import json


def run(data_path, out_path):
    out = {body}
    with open(out_path, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    return out
'''
