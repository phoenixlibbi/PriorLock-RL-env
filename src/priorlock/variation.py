"""Per-seed task variation: new input data, answers recomputed from the library.

Every catalog probe ships one fixed input payload with hand-checked gold and
familiar outputs. Left as is, two tasks that share a probe share its answer, so
a solution leaked from one task scores on every other. ``vary`` gives each seed
its own data:

- integers that are data (ids, quantities, scores, sequence values) are shifted
  by a per-seed offset, so order and ties are preserved,
- label-like words (categories, regions, names) are relabelled consistently,
- amounts are scaled by a per-seed positive factor,

while field names, argument strings, sizes and order are left alone so the
instruction still describes the task. The gold and familiar answers are then
recomputed by running the reference solutions against the installed library,
and any probe whose two answers no longer differ keeps its original data.
"""
from __future__ import annotations

import dataclasses
import json
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import templates as T
from .probes.base import Probe

_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,15}$")
# integer arguments that are positions or sizes, not data
_INDEX_KEYS = {"start", "end", "size", "k", "n", "width", "places", "count", "limit", "index",
               "page", "per_page", "qs"}
_SYLLABLES = ("ka", "lo", "mi", "ren", "tu", "sa", "vo", "zel", "pa", "ni", "dor", "ve")


def _keys(value, acc: set[str]) -> set[str]:
    if isinstance(value, dict):
        for k, v in value.items():
            acc.add(k)
            _keys(v, acc)
    elif isinstance(value, list):
        for v in value:
            _keys(v, acc)
    return acc


def _perturb(value, rng: random.Random, ctx: dict, key: str = ""):
    if isinstance(value, dict):
        return {k: _perturb(v, rng, ctx, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_perturb(v, rng, ctx, key) for v in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value if key in _INDEX_KEYS else value + ctx["offset"]
    if isinstance(value, float):
        return round(value * ctx["scale"], 6)
    if isinstance(value, str) and _WORD.match(value) and value not in ctx["protected"]:
        table = ctx["labels"]
        if value not in table:
            word = ""
            while not word or word in table.values():
                word = "".join(rng.choice(_SYLLABLES) for _ in range(2))
            table[value] = word.capitalize() if value[0].isupper() else word
        return table[value]
    return value


def _run_references(lib: str, lib_source: str, probes: list[Probe]) -> dict[str, dict]:
    """Run each probe's gold and familiar reference against the library."""
    results: dict[str, dict] = {"gold": {}, "familiar": {}}
    with tempfile.TemporaryDirectory(prefix="plx-vary-") as tmp:
        root = Path(tmp)
        (root / lib).mkdir()
        (root / lib / "__init__.py").write_text(lib_source)
        for i, p in enumerate(probes):
            (root / f"in{i}.json").write_text(T.render_input([p]))
            for variant in ("gold", "familiar"):
                mod = f"{variant}{i}"
                (root / f"{mod}.py").write_text(T.render_reference_solution(lib, [p], variant))
                code = (f"import json, sys\nsys.path.insert(0, {str(root)!r})\n"
                        f"import {mod} as m\n"
                        f"out = m.run({str(root / f'in{i}.json')!r}, {str(root / (mod + '.out'))!r})\n"
                        f"print(json.dumps(out.get({p.output_key!r}), default=str))")
                proc = subprocess.run([sys.executable, "-I", "-c", code],
                                      capture_output=True, text=True, timeout=30)
                try:
                    value = json.loads(proc.stdout) if proc.returncode == 0 else None
                except json.JSONDecodeError:
                    value = None
                results[variant][p.id] = value
    return results


def vary(probes: list[Probe], lib: str, seed: str) -> list[Probe]:
    """Return copies of *probes* with per-seed data and recomputed answers."""
    rng = random.Random("vary:" + seed)
    protected: set[str] = set()
    for p in probes:
        _keys(p.input_payload, protected)
        protected.update(str(v) for v in p.gold_kwargs.values())
        protected.update(str(v) for v in p.familiar_kwargs.values())
        if p.param:
            protected.add(p.param)
    ctx = {"offset": rng.randrange(100, 900), "scale": rng.choice((2.0, 3.0, 4.0, 5.0)),
           "labels": {}, "protected": protected}
    varied = [dataclasses.replace(p, input_payload=_perturb(p.input_payload, rng, ctx))
              for p in probes]

    lib_source = T.render_library(lib, varied, hide_defaults=False)
    outs = _run_references(lib, lib_source, varied)
    result = []
    for orig, new in zip(probes, varied):
        gold = outs["gold"].get(new.id)
        familiar = outs["familiar"].get(new.id)
        if gold is None or familiar is None or gold == familiar:
            result.append(orig)
            continue
        result.append(dataclasses.replace(new, gold_output=gold, familiar_output=familiar))
    return result
