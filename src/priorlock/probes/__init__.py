"""Probe registry, category inference, and automatic selection.

The public surface used by the injection engine is:

    infer_categories(text)      -> ranked list of category names
    select_probes(task_id, ...) -> deterministic, family-diverse probe set
    load_calibration()          -> empirical familiar-rates from calibration.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from .base import (
    CATEGORIES,
    FAMILIES,
    FAMILIAR_BASELINE,
    Probe,
    composite_reward,
    gap_score,
)
from .catalog import ALL_PROBES, BY_ID

__all__ = [
    "ALL_PROBES", "BY_ID", "Probe", "CATEGORIES", "FAMILIES", "FAMILIAR_BASELINE",
    "gap_score", "composite_reward",
    "infer_categories", "select_probes", "load_calibration", "save_calibration",
    "calibration_path", "probe_table",
    "all_probes_by_id", "all_probes_list",
]


# ── cartridge-aware probe lookups ────────────────────────────────────────────
#
# The original ALL_PROBES / BY_ID contain only the 13 coding-domain archetypes.
# These helpers extend lookup to every registered cartridge, so inject.py and
# env.py can resolve probe IDs from any domain without importing cartridges
# directly.

def all_probes_list(domains: list[str] | None = None) -> list[Probe]:
    """All probes from the cartridge registry, optionally filtered by domain.

    Falls back to the original coding-only ``ALL_PROBES`` if the cartridge
    system is not importable (defensive — shouldn't happen in practice).
    """
    try:
        from ..cartridges import all_probes
        return all_probes(domains)
    except ImportError:
        return list(ALL_PROBES)


def all_probes_by_id(domains: list[str] | None = None) -> dict[str, Probe]:
    """ID → Probe mapping across all cartridges (or filtered domains)."""
    return {p.id: p for p in all_probes_list(domains)}

_CALIBRATION = Path(__file__).with_name("calibration.json")


# ── category inference ───────────────────────────────────────────────────────
#
# Weighted keyword lexicon. Deliberately broad — the goal is a sensible default
# for an arbitrary Terminal-Bench task, not a perfect classification. Probe
# validity does not depend on getting the category right; category selection
# only makes the injected sub-task feel native to the surrounding work.

_LEXICON: dict[str, dict[str, float]] = {
    "collection": {
        "data": 1.0, "csv": 2.0, "tsv": 2.0, "table": 1.5, "record": 2.0,
        "row": 1.5, "list": 1.0, "sort": 2.0, "filter": 1.5, "group": 2.0,
        "aggregate": 2.0, "etl": 2.0, "pipeline": 1.5, "dataset": 1.5,
        "dedupe": 2.5, "duplicate": 2.0, "batch": 1.5, "rank": 2.0,
        "dataframe": 2.0, "query": 1.0, "index": 1.0, "slice": 1.5,
    },
    "numeric": {
        "math": 2.0, "numeric": 2.5, "statistic": 2.0, "stats": 2.0,
        "compute": 1.5, "calculate": 1.5, "metric": 1.5, "money": 2.0,
        "price": 2.0, "currency": 2.0, "finance": 2.5, "invoice": 2.0,
        "sum": 1.5, "average": 1.5, "mean": 1.5, "round": 2.5, "decimal": 2.5,
        "percent": 1.5, "tax": 2.0, "accounting": 2.0, "benchmark": 1.0,
        "float": 1.5, "precision": 2.0,
    },
    "text": {
        "string": 2.0, "text": 1.5, "parse": 1.5, "format": 1.5, "log": 1.5,
        "regex": 2.0, "encode": 1.5, "decode": 1.5, "template": 1.5,
        "markdown": 1.5, "unicode": 2.5, "token": 2.0, "render": 1.0,
        "report": 1.0, "print": 1.0, "align": 2.0, "pad": 2.0, "case": 1.5,
        "slug": 2.0, "sanitize": 1.5, "escape": 1.5,
    },
    "temporal": {
        "date": 2.5, "time": 1.5, "timestamp": 2.5, "timezone": 2.5,
        "schedule": 2.0, "calendar": 2.0, "cron": 2.0, "duration": 2.0,
        "interval": 1.5, "iso8601": 2.5, "utc": 2.0, "expiry": 1.5,
        "deadline": 1.5, "log rotation": 1.5,
    },
    "mapping": {
        "config": 2.5, "dict": 2.0, "yaml": 2.0, "toml": 2.0, "json": 1.0,
        "settings": 2.0, "merge": 2.5, "override": 1.5, "env": 1.5,
        "manifest": 2.0, "schema": 1.5, "key": 1.0, "namespace": 1.5,
        "environment variable": 2.0, "defaults": 1.5, "preferences": 1.5,
    },
}

_WORD = re.compile(r"[a-z][a-z0-9_\-]+")


def infer_categories(text: str) -> list[tuple[str, float]]:
    """Rank probe categories by relevance to a task's description text.

    Returns ``[(category, score), ...]`` sorted descending. Every category is
    present, so callers can always fall back down the list.
    """
    haystack = (text or "").lower()
    tokens = set(_WORD.findall(haystack))
    scores: dict[str, float] = {}
    for cat, lex in _LEXICON.items():
        total = 0.0
        for kw, weight in lex.items():
            if " " in kw:
                if kw in haystack:
                    total += weight
            elif kw in tokens:
                total += weight
        scores[cat] = round(total, 3)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked


# ── deterministic selection ──────────────────────────────────────────────────

def _seed(task_id: str) -> int:
    return int(hashlib.sha256(task_id.encode()).hexdigest()[:12], 16)


def select_probes(
    task_id: str,
    text: str = "",
    count: int = 3,
    require_family_diversity: bool = True,
    exclude: set[str] | None = None,
    min_confidence: float = 0.0,
) -> list[Probe]:
    """Pick ``count`` probes for a task. Deterministic for a given ``task_id``.

    Selection order of preference:

    1. **Family diversity** — one probe from each of ``default_flip``,
       ``value_remap`` and ``result_shape`` before doubling up on any family.
       A mixed set is harder to game: an agent that learns to always pass every
       keyword argument explicitly still has to handle the result_shape probe.
    2. **Category fit** — within a family, prefer probes whose category ranks
       highest for this task's description.
    3. **Calibration confidence** — prefer probes with a measured discrimination
       rate at or above ``min_confidence``.
    4. **Stable hash rotation** — deterministic per task, but different tasks
       get different probes, so a leaked answer for one task is worthless for
       the next.
    """
    exclude = exclude or set()
    ranked = {cat: i for i, (cat, _) in enumerate(infer_categories(text))}
    calib = load_calibration()

    def confidence(p: Probe) -> float:
        entry = calib.get("probes", {}).get(p.id, {})
        return float(entry.get("discrimination", 0.0))

    pool = [
        p for p in ALL_PROBES
        if p.id not in exclude and confidence(p) >= min_confidence
    ]
    if not pool:
        pool = [p for p in ALL_PROBES if p.id not in exclude]

    rot = _seed(task_id)

    def sort_key(p: Probe) -> tuple:
        # lower is better
        cat_rank = ranked.get(p.category, len(CATEGORIES))
        jitter = (int(hashlib.sha256(f"{task_id}:{p.id}".encode()).hexdigest()[:8], 16)) % 1000
        return (cat_rank, -confidence(p), jitter)

    chosen: list[Probe] = []
    if require_family_diversity:
        fam_order = list(FAMILIES)
        # rotate which family gets first pick so tasks do not all look alike
        shift = rot % len(fam_order)
        fam_order = fam_order[shift:] + fam_order[:shift]
        for fam in fam_order:
            if len(chosen) >= count:
                break
            candidates = sorted((p for p in pool if p.family == fam), key=sort_key)
            if candidates:
                chosen.append(candidates[0])

    remaining = sorted((p for p in pool if p not in chosen), key=sort_key)
    for p in remaining:
        if len(chosen) >= count:
            break
        chosen.append(p)

    return chosen[:count]


# ── calibration store ────────────────────────────────────────────────────────

def calibration_path() -> Path:
    return _CALIBRATION


_EMPTY_CALIBRATION = {
    "schema": 1,
    "note": (
        "Empirical familiar-rates per probe per model family. 'discrimination' is "
        "the fraction of runs where a probe produced a non-ambiguous verdict "
        "(override or prior_locked). 'familiar_rate' is the fraction of those that "
        "were prior_locked. The 0.40 baseline itself is structural and does not "
        "depend on these numbers — calibration only tells you how INFORMATIVE a "
        "probe is for a given model."
    ),
    "probes": {},
    "models": {},
}


def load_calibration() -> dict:
    if not _CALIBRATION.is_file():
        return dict(_EMPTY_CALIBRATION)
    try:
        with _CALIBRATION.open() as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return dict(_EMPTY_CALIBRATION)


def save_calibration(data: dict) -> None:
    _CALIBRATION.parent.mkdir(parents=True, exist_ok=True)
    with _CALIBRATION.open("w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


# ── human-readable listing ───────────────────────────────────────────────────

def probe_table(family: str | None = None, category: str | None = None,
                domain: str | None = None) -> str:
    """Human-readable probe listing, optionally filtered.

    When *domain* is given, shows probes from that cartridge (or all cartridges
    if ``domain="all"``). Without *domain*, shows only the original coding
    archetypes for backward compatibility.
    """
    calib = load_calibration().get("probes", {})

    if domain == "all":
        source = all_probes_list()
    elif domain:
        source = all_probes_list([domain])
    else:
        source = list(ALL_PROBES)

    rows = [
        p for p in source
        if (family is None or p.family == family)
        and (category is None or p.category == category)
    ]
    if not rows:
        return "no probes match that filter"

    show_domain = domain == "all" or (domain is None and len({p.domain for p in rows}) > 1)
    w_id = max(len(p.id) for p in rows)
    w_fam = max(len(p.family) for p in rows)
    w_cat = max(len(p.category) for p in rows)
    w_dom = max(len(p.domain) for p in rows) if show_domain else 0

    header = f"{'ID'.ljust(w_id)}  {'FAMILY'.ljust(w_fam)}  {'CATEGORY'.ljust(w_cat)}"
    sep = f"{'-' * w_id}  {'-' * w_fam}  {'-' * w_cat}"
    if show_domain:
        header = f"{'DOMAIN'.ljust(w_dom)}  " + header
        sep = f"{'-' * w_dom}  " + sep
    header += "  L   CONF   SUMMARY"
    sep += "  --  ----   -------"
    out = [header, sep]

    for p in rows:
        conf = calib.get(p.id, {}).get("discrimination")
        conf_s = f"{conf:.2f}" if isinstance(conf, (int, float)) else "  — "
        line = ""
        if show_domain:
            line += f"{p.domain.ljust(w_dom)}  "
        line += (
            f"{p.id.ljust(w_id)}  {p.family.ljust(w_fam)}  {p.category.ljust(w_cat)}  "
            f"L{p.level}  {conf_s}   {p.summary}"
        )
        out.append(line)
    return "\n".join(out)
