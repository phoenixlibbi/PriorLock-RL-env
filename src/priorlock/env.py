"""PriorLock as a `verifiers` RL environment — the trainable packaging.

Why this module exists
----------------------
In the format the field has settled on (the open-source ``verifiers``
package), an RL environment is a self-contained Python module exposing
``load_environment``, installable as a wheel, so the same unit serves both
evaluation and training.

Everything else PriorLock ships is *evaluation* packaging: a Harbor task, run
in Docker, graded by a composite verifier. That is the right shape for a
leaderboard and it is proven end-to-end. It is the wrong shape for **training**,
because you cannot put a six-minute container build inside an RL loop.

This module is the other half. It exposes the same measurement — the
{0.00, 0.40, 1.00} prior-override ladder — as a single-turn, pure-Python,
Docker-free environment that a lab can `pip install` and train against.

Why the probe half can be Docker-free
-------------------------------------
The probe sub-task is genuinely self-contained: a synthetic library, its
documentation, one JSON input, and one function to write. No repo to build, no
services, no filesystem state. The whole interaction is text in, code out. That
is exactly the shape `verifiers` is built for, and it is why the prior-override
signal can be trained on cheaply even though the host task it normally rides on
cannot.

    Harbor task     evaluation   Docker, composite reward, leaderboard
    verifiers env   training     pure Python, single turn, RL loop

Both grade with the same rule from ``probes.base``, so a score means the same
thing in either.

Usage
-----
::

    import verifiers as vf
    env = vf.load_environment("priorlock")           # via entry point
    # or
    from priorlock.env import load_environment
    env = load_environment(num_instances=200, probes_per_instance=3)
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from . import templates as T
from .probes import ALL_PROBES, BY_ID, select_probes
from .probes import all_probes_by_id, all_probes_list
from .probes.base import FAMILIAR_BASELINE, Probe, gap_score

DEFAULT_INSTANCES = 200
DEFAULT_PROBES = 3
GRADE_TIMEOUT = 30


# ═════════════════════════════════════════════════════════════════════════════
#  Prompt construction
# ═════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
You are given a local Python library and its documentation, plus a small data \
task. Write one function that solves the task using the bundled library.

The library's documentation is authoritative. It is a 2.x release, and several \
functions changed behaviour from the 1.x line without changing their \
signatures — defaults were inverted, and some accepted values were given new \
meanings. Code written against 1.x still runs and still returns the right \
types; it simply returns different results.

Read the CHANGELOG before you rely on any default.\
"""


def _instance_prompt(lib: str, probes: list[Probe], payload: dict) -> str:
    """The full agent-visible surface for one instance, as text."""
    checks = "\n".join(
        f"{i}. `{p.output_key}` — {p.task_clause}"
        for i, p in enumerate(probes, 1)
    )
    fn_list = ", ".join(f"`{lib}.{p.fn}`" for p in probes)

    return f"""\
# `{lib}` 2.0.0

A local library bundled with this task. It is not published to any package \
index — there is no newer release to fetch and no online documentation. The \
documentation below is the only source of truth.

## API reference

{T.render_api(lib, probes).split('## Functions', 1)[-1].strip()}

## CHANGELOG

{T.render_changelog(lib, probes).split('## 1.4.3', 1)[0].split('---', 1)[-1].strip()}

## Input data

```json
{json.dumps(payload, indent=2, ensure_ascii=False)}
```

## What to write

A single Python function:

```python
def solve(data):
    ...
    return out
```

`data` is the JSON object above. Use {fn_list} — do not reimplement them. \
Return a dict with one key per check below.

### Checks

{checks}

Reply with the function in a single ```python code block. No other output.
"""


# ═════════════════════════════════════════════════════════════════════════════
#  Dataset
# ═════════════════════════════════════════════════════════════════════════════

def build_instances(num_instances: int = DEFAULT_INSTANCES,
                    probes_per_instance: int = DEFAULT_PROBES,
                    seed_prefix: str = "plx",
                    probe_ids: list[str] | None = None,
                    domains: list[str] | None = None,
                    level: int = 1) -> list[dict]:
    """Generate deterministic environment instances.

    Each instance is a distinct synthetic library with a distinct probe mix, so
    instances are disjoint by construction. Seeding on the instance id
    means the same id always yields the same instance, in any process, forever.

    Args:
        domains: when set, instances draw probes from these cartridge domains
            using the cross-domain selector. Disjoint from ``probe_ids``.
        level: maximum probe difficulty level (L1–L4). Default 1.
    """
    if probe_ids:
        extended = all_probes_by_id(domains)
        merged = {**BY_ID, **extended}
        pool = [merged[p] for p in probe_ids]
    else:
        pool = None

    rows: list[dict] = []

    for i in range(num_instances):
        task_id = f"{seed_prefix}-{i:05d}"
        if pool:
            probes = pool[: probes_per_instance]
        elif domains:
            from .cartridges import select_probes_cross
            probes = select_probes_cross(
                task_id=task_id,
                domains=domains,
                count=probes_per_instance,
                level=level,
            )
        else:
            probes = select_probes(task_id, text="", count=probes_per_instance)

        idx = int(hashlib.sha256(("lib:" + task_id).encode()).hexdigest()[:8], 16)
        lib = T.LIB_NAMES[idx % len(T.LIB_NAMES)]

        payload = {p.output_key: p.input_payload for p in probes}
        rows.append({
            "question": _instance_prompt(lib, probes, payload),
            "answer": json.dumps({p.output_key: p.gold_output for p in probes},
                                 sort_keys=True),
            "task": "priorlock",
            "info": {
                "instance_id": task_id,
                "library": lib,
                "library_source": T.render_library(lib, probes),
                "probes": [p.to_grader_dict() for p in probes],
                "payload": payload,
                "familiar": json.dumps(
                    {p.output_key: p.familiar_output for p in probes}, sort_keys=True),
            },
        })
    return rows


# ═════════════════════════════════════════════════════════════════════════════
#  Grading — the same ladder, no Docker
# ═════════════════════════════════════════════════════════════════════════════

_CODE_BLOCK = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)


def extract_code(completion: str) -> str:
    """Pull the python block out of a model completion."""
    blocks = _CODE_BLOCK.findall(completion or "")
    if blocks:
        return max(blocks, key=len)
    return completion or ""


_RUNNER = r'''
import inspect, json, sys

LIB = __LIB__
PROBES = json.loads(__PROBES__)
PAYLOAD = json.loads(__PAYLOAD__)

import importlib
lib = importlib.import_module(LIB)

calls = {}
for spec in PROBES:
    name = spec["fn"]
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
                if isinstance(v, (str, int, float, bool, type(None)))
            })
            return original(*args, **kwargs)
        wrapper.__name__ = name
        wrapper.__signature__ = signature
        return wrapper

    setattr(lib, name, make(name, original, signature))

ns = {}
try:
    exec(open(__SOLUTION__).read(), ns)
    fn = ns.get("solve")
    if fn is None:
        for v in ns.values():
            if callable(v) and getattr(v, "__name__", "") != "<lambda>":
                fn = v
                break
    out = fn(PAYLOAD) if fn else None
except Exception as exc:
    print(json.dumps({"error": type(exc).__name__ + ": " + str(exc)[:200]}))
    sys.exit(0)

print(json.dumps({"output": out, "calls": calls}, default=str))
'''


def grade(completion: str, info: dict) -> dict:
    """Run the completion against a pristine library and score the ladder.

    Identical rule to the Harbor path: the library is written fresh into a
    throwaway directory, the probe functions are instrumented, and the arguments
    the solution *explicitly supplied* are recovered via ``Signature.bind``.
    Nothing the completion writes participates in scoring.
    """
    extended = all_probes_by_id()
    merged = {**BY_ID, **extended}
    probes = [merged[p["id"]] for p in info["probes"] if p["id"] in merged]
    lib = info["library"]

    tmp = Path(tempfile.mkdtemp(prefix="plx-env-"))
    try:
        (tmp / lib).mkdir()
        (tmp / lib / "__init__.py").write_text(info["library_source"], encoding="utf-8")
        (tmp / "solution.py").write_text(extract_code(completion), encoding="utf-8")

        runner = (_RUNNER
                  .replace("__LIB__", json.dumps(lib))
                  .replace("__PROBES__", json.dumps(json.dumps(info["probes"])))
                  .replace("__PAYLOAD__", json.dumps(json.dumps(info["payload"])))
                  .replace("__SOLUTION__", json.dumps(str(tmp / "solution.py"))))
        (tmp / "_runner.py").write_text(runner, encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(tmp / "_runner.py")],
            capture_output=True, text=True, timeout=GRADE_TIMEOUT, cwd=str(tmp),
        )
        if not proc.stdout.strip():
            return {"gap_score": 0.0, "verdicts": {}, "error": proc.stderr[-300:]}
        data = json.loads(proc.stdout)
        if "error" in data:
            return {"gap_score": 0.0, "verdicts": {p.id: "crashed" for p in probes},
                    "error": data["error"]}

        out, calls = data.get("output") or {}, data.get("calls", {})
        scores, weights, verdicts = [], [], {}
        for p in probes:
            invocations = calls.get(p.fn, [])
            value = out.get(p.output_key) if isinstance(out, dict) else None
            score, verdict = p.score(
                invoked=bool(invocations),
                supplied=invocations[0] if invocations else {},
                output=json.loads(json.dumps(value, default=str)) if value is not None else None,
            )
            # credit the best call when a helper is used more than once
            for sup in invocations[1:]:
                s2, v2 = p.score(invoked=True, supplied=sup,
                                 output=json.loads(json.dumps(value, default=str))
                                 if value is not None else None)
                if s2 > score:
                    score, verdict = s2, v2
            scores.append(score)
            weights.append(p.weight)
            verdicts[p.id] = verdict

        return {"gap_score": gap_score(scores, weights), "verdicts": verdicts}
    except subprocess.TimeoutExpired:
        return {"gap_score": 0.0, "verdicts": {p.id: "crashed" for p in probes},
                "error": "timeout"}
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ═════════════════════════════════════════════════════════════════════════════
#  verifiers entry point
# ═════════════════════════════════════════════════════════════════════════════

def prior_override_reward(completion, info, **kwargs) -> float:
    """Primary reward: the prior-override ladder, weighted-mean across probes."""
    text = completion
    if isinstance(completion, list):          # chat-format completion
        text = "\n".join(m.get("content", "") for m in completion
                         if isinstance(m, dict))
    return grade(text, info)["gap_score"]


def called_library_reward(completion, info, **kwargs) -> float:
    """Diagnostic: did the solution call the library at all?

    Not part of the score — reported alongside it so a training run can
    distinguish "prior-locked" from "reimplemented the function", which the
    ladder collapses to 0.40 and 0.00 respectively.
    """
    text = completion
    if isinstance(completion, list):
        text = "\n".join(m.get("content", "") for m in completion
                         if isinstance(m, dict))
    verdicts = grade(text, info)["verdicts"]
    if not verdicts:
        return 0.0
    return sum(v != "bypassed" for v in verdicts.values()) / len(verdicts)


def load_environment(
    num_instances: int = DEFAULT_INSTANCES,
    probes_per_instance: int = DEFAULT_PROBES,
    probe_ids: list[str] | None = None,
    domains: list[str] | None = None,
    level: int = 1,
    seed_prefix: str = "plx",
    eval_fraction: float = 0.2,
    **kwargs,
):
    """Return a `verifiers` environment measuring prior-override capability.

    Args:
        num_instances: total instances to generate.
        probes_per_instance: probes per instance; selection enforces one per
            family, so 3 gives full family coverage.
        probe_ids: pin a specific probe set instead of auto-selecting.
        domains: restrict probes to specific cartridge domains (e.g.
            ``["coding", "sql", "linux"]``). When set, uses the cross-domain
            selector so each instance samples across domains.
        level: maximum probe difficulty level (L1–L4). Default 1.
        seed_prefix: namespaces the seeds. Train and eval use disjoint
            prefixes so the splits cannot overlap.
        eval_fraction: share held out for evaluation.

    The reward is the {0.00, 0.40, 1.00} ladder from ``probes.base``:
    1.00 read the docs, 0.40 applied the memorised default, 0.00 never called
    the library.
    """
    try:
        import verifiers as vf
    except ImportError as exc:                                # pragma: no cover
        raise ImportError(
            "The verifiers package is required for the RL environment.\n"
            "    pip install 'priorlock[rl]'\n"
            "Evaluation via Harbor (`priorlock wrap`) does not need it."
        ) from exc

    try:
        from datasets import Dataset
    except ImportError as exc:                                # pragma: no cover
        raise ImportError("pip install 'priorlock[rl]' (needs `datasets`)") from exc

    n_eval = max(1, int(num_instances * eval_fraction))
    train_rows = build_instances(num_instances, probes_per_instance,
                                 f"{seed_prefix}-train", probe_ids,
                                 domains=domains, level=level)
    eval_rows = build_instances(n_eval, probes_per_instance,
                                f"{seed_prefix}-eval", probe_ids,
                                domains=domains, level=level)

    rubric = vf.Rubric(
        funcs=[prior_override_reward, called_library_reward],
        weights=[1.0, 0.0],          # the second is diagnostic, not scored
    )

    return vf.SingleTurnEnv(
        dataset=Dataset.from_list(train_rows),
        eval_dataset=Dataset.from_list(eval_rows),
        system_prompt=SYSTEM_PROMPT,
        rubric=rubric,
        **kwargs,
    )
