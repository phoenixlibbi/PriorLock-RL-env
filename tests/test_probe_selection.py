"""Deterministic probe selection (QA selection / E2 seed surface)."""
from __future__ import annotations

from priorlock.probes import FAMILIES, select_probes


def test_same_task_id_identical_ids():
    a = [p.id for p in select_probes("task-alpha", count=3)]
    b = [p.id for p in select_probes("task-alpha", count=3)]
    assert a == b
    assert len(a) == 3


def test_family_diversity_at_count_three():
    probes = select_probes("diversity-check", count=3, require_family_diversity=True)
    families = {p.family for p in probes}
    assert families == set(FAMILIES)
    assert len(probes) == 3


def test_different_task_ids_different_mixes():
    a = [p.id for p in select_probes("task-one", count=3)]
    b = [p.id for p in select_probes("task-two", count=3)]
    assert a != b
