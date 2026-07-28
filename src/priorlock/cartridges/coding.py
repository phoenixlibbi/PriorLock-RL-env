"""Coding domain cartridge — Python API prior override.

This is the original PriorLock domain, extracted into cartridge form. The 13
archetypes from ``probes.catalog`` are re-exported here with ``domain="coding"``.
"""
from __future__ import annotations

from ..probes.catalog import ALL_PROBES
from ..probes.base import Probe
from . import CartridgeSpec, register, SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE

# Re-tag existing probes with domain="coding" (they default to it, but be explicit)
CODING_PROBES = tuple(
    Probe(
        id=p.id, family=p.family, category=p.category, summary=p.summary,
        fn=p.fn, signature=p.signature, impl=p.impl,
        api_doc=p.api_doc, changelog=p.changelog,
        param=p.param, gold_kwargs=p.gold_kwargs,
        familiar_kwargs=p.familiar_kwargs,
        familiar_behaviour=p.familiar_behaviour,
        installed_behaviour=p.installed_behaviour,
        task_clause=p.task_clause, output_key=p.output_key,
        input_payload=p.input_payload,
        gold_output=p.gold_output, familiar_output=p.familiar_output,
        tags=p.tags, weight=p.weight, domain="coding", level=1,
    )
    for p in ALL_PROBES
)

CATEGORIES = (
    "collection", "numeric", "text", "temporal", "mapping",
)

LEXICON = {
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
        "percent": 1.5, "tax": 2.0, "accounting": 2.0, "float": 1.5,
        "precision": 2.0,
    },
    "text": {
        "string": 2.0, "text": 1.5, "parse": 1.5, "format": 1.5, "log": 1.5,
        "regex": 2.0, "encode": 1.5, "decode": 1.5, "template": 1.5,
        "unicode": 2.5, "token": 2.0, "align": 2.0, "pad": 2.0, "case": 1.5,
    },
    "temporal": {
        "date": 2.5, "time": 1.5, "timestamp": 2.5, "timezone": 2.5,
        "schedule": 2.0, "calendar": 2.0, "cron": 2.0, "duration": 2.0,
        "iso8601": 2.5, "utc": 2.0,
    },
    "mapping": {
        "config": 2.5, "dict": 2.0, "yaml": 2.0, "toml": 2.0, "json": 1.0,
        "settings": 2.0, "merge": 2.5, "override": 1.5, "env": 1.5,
        "manifest": 2.0, "schema": 1.5, "key": 1.0,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="coding",
    display_name="Python API",
    description="Prior override on synthetic Python library functions — the original PriorLock domain.",
    probes=CODING_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    information_sources=(SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE),
    max_level=1,
)

register(CARTRIDGE)
