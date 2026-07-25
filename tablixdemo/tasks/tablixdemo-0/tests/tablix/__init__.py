"""tablix v1.4 — synthetic data-aggregation library.

Two silent behavioral changes from v1.3 (documented in docs/CHANGELOG.md):
  1. group_by: None/empty keys map to "__missing__" group (v1.3: excluded)
  2. top_n:    ties at position n are ALL returned (v1.3: strict cut at n)
"""
import csv as _csv


def load_csv(path):
    """Load a CSV file and return a list of row dicts (all values are strings)."""
    with open(path, newline="") as f:
        return list(_csv.DictReader(f))


def group_by(records, key):
    """Group records by the string value of *key*.

    Records where records[key] is None, absent, or an empty string are
    collected under the special key ``"__missing__"``.  This group always
    appears in the output when such records exist.

    Returns a dict mapping group name → list of records.
    """
    groups = {}
    for r in records:
        k = r.get(key) or None   # treat "" same as None
        if k is None:
            k = "__missing__"
        groups.setdefault(k, []).append(r)
    return groups


def sum_field(records, field):
    """Return the sum of *field* (cast to float) across all *records*."""
    return sum(float(r[field]) for r in records)


def top_n(records, n, key, reverse=True):
    """Return the top-*n* records by numeric field *key*.

    **Tie-inclusive**: if multiple records share the value at position *n*,
    ALL of them are included.  The returned list may be longer than *n*.

    Returns a list of records (length >= min(n, len(records))).
    """
    if not records:
        return []
    sorted_recs = sorted(records, key=lambda r: float(r[key]), reverse=reverse)
    if len(sorted_recs) <= n:
        return sorted_recs
    threshold = float(sorted_recs[n - 1][key])
    if reverse:
        return [r for r in sorted_recs if float(r[key]) >= threshold]
    else:
        return [r for r in sorted_recs if float(r[key]) <= threshold]


def sort_records(records, key, reverse=False):
    """Sort records by *key*. Ties broken by record ``id`` field descending."""
    def _sort_key(r):
        v = r.get(key, "")
        try:
            v = float(v)
        except (ValueError, TypeError):
            pass
        rid = -int(r.get("id", 0))
        return (v, rid)
    return sorted(records, key=_sort_key, reverse=reverse)
