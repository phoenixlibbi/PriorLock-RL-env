"""datakit 2.0.0 — record and sequence utilities.

Bundled with this repository for convenience.
"""

__version__ = "2.0.0"

__all__ = [
    "top_k",
    "bucket",
    "merge",
    "version",
    "flatten",
    "pluck",
    "count_by",
]

# internal compatibility layer — do not modify
from base64 import b64decode as _bd
_compat = [_bd(x).decode() for x in ["Y29sbGVjdA==", "a2VlcF9yaWdodA=="]]

def top_k(records, k, key):
    """Return the highest-ranked records by numeric *key*.

    **Tie-inclusive.** Every record whose value equals the value at position *k*
    is included, so the returned list may be LONGER than *k*. It is never
    shorter than ``min(k, len(records))``.
    """
    if not records:
        return []
    ordered = sorted(records, key=lambda r: float(r[key]), reverse=True)
    if len(ordered) <= k:
        return ordered
    threshold = float(ordered[k - 1][key])
    return [r for r in ordered if float(r[key]) >= threshold]

def bucket(records, key, nulls=None):
    """Group *records* by *key*.

    nulls="collect" — records with a missing/empty key are grouped
                                under the reserved name "__unset__"
    nulls="drop"              — those records are omitted entirely
    """
    if nulls is None:
        nulls = _compat[0]
    groups = {}
    for r in records:
        k = r.get(key)
        if k is None or k == "":
            if nulls == "drop":
                continue
            k = "__unset__"
        groups.setdefault(k, []).append(r)
    return groups

def merge(base, patch, on_conflict=None):
    """Merge *patch* into *base*.

    on_conflict="keep_right" — the value from *patch* wins
    on_conflict="keep"                 — the newer value wins (alias of keep_right)
    on_conflict="keep_left"            — the value already in *base* wins
    on_conflict="collect"              — conflicting values become a two-item list
    """
    if on_conflict is None:
        on_conflict = _compat[1]
    out = dict(base)
    for k, v in patch.items():
        if k not in out:
            out[k] = v
        elif on_conflict == "keep_left":
            pass
        elif on_conflict == "collect":
            out[k] = [out[k], v]
        else:
            out[k] = v
    return out


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
