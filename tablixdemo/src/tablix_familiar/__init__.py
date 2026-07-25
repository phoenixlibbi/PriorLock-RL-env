"""tablix v1.3 — FAMILIAR (pre-v1.4) semantics used for Stage-0 baseline.

NOT shipped into the agent container. Used only by the stage0 script to
demonstrate that a model writing from prior memory scores 0.40 (core only).
"""
import csv as _csv


def load_csv(path):
    with open(path, newline="") as f:
        return list(_csv.DictReader(f))


def group_by(records, key):
    """v1.3 behaviour: records with None/empty key are EXCLUDED (not grouped)."""
    groups = {}
    for r in records:
        k = r.get(key) or None
        if k is None:
            continue  # FAMILIAR: skip; v1.4 maps to "__missing__"
        groups.setdefault(k, []).append(r)
    return groups


def sum_field(records, field):
    return sum(float(r[field]) for r in records)


def top_n(records, n, key, reverse=True):
    """v1.3 behaviour: strict cut — always returns exactly min(n, len) records."""
    if not records:
        return []
    sorted_recs = sorted(records, key=lambda r: float(r[key]), reverse=reverse)
    return sorted_recs[:n]  # FAMILIAR: strict cut; v1.4 includes ties


def sort_records(records, key, reverse=False):
    """v1.3 behaviour: stable original insertion order for ties (no id tiebreak)."""
    def _sort_key(r):
        v = r.get(key, "")
        try:
            v = float(v)
        except (ValueError, TypeError):
            pass
        return v
    return sorted(records, key=_sort_key, reverse=reverse)
