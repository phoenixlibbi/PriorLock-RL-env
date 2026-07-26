"""Fundamentals domain cartridge — prior override on universal programming concepts.

Ten probes targeting concepts so deeply baked into every model's training data
that even a 3B-parameter model has strong priors: zero-based indexing,
exclusive range ends, falsy empty strings, floor division, mutable default
arguments, stable sort, string concatenation vs joining, truthiness of zero,
dict key overwrite semantics, and modulo sign convention.

These are the "small-model trap" probes — if a model scores 1.0 here, it
genuinely read the docs; if it scores 0.40, prior-lock is confirmed even
at small scale.
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

RANGE_START_INDEX = Probe(
    id="range_start_index",
    family="default_flip",
    category="indexing",
    summary="make_range() now uses 1-based indexing by default instead of 0-based.",
    fn="make_range",
    signature="make_range(n, start_at=1)",
    impl='''
def make_range(n, start_at=1):
    """Generate a sequence of *n* consecutive integers.

    start_at=1  (default) — sequence begins at 1: [1, 2, ..., n]
    start_at=0            — sequence begins at 0: [0, 1, ..., n-1]
    """
    return list(range(start_at, start_at + n))
''',
    api_doc='`make_range(n, start_at=1)` — generate `n` consecutive integers '
            'starting at `start_at`. Default is `1` (1-based sequence).',
    changelog='**`make_range` — default `start_at` changed from `0` to `1`.** '
              'Prior releases generated 0-based sequences `[0, 1, ..., n-1]`. '
              'The current release generates 1-based sequences `[1, 2, ..., n]` '
              'by default. Pass `start_at=0` to restore 0-based indexing.',
    param="start_at",
    gold_kwargs={"start_at": 0},
    familiar_kwargs={},
    familiar_behaviour="start_at defaults to 0 — 0-based sequence [0, 1, ..., n-1]",
    installed_behaviour="start_at defaults to 1 — 1-based sequence [1, 2, ..., n]",
    task_clause="Generate a sequence of `n` integers using **zero-based** indexing "
                "(starting from 0). Write the list under `seq`.",
    output_key="seq",
    input_payload={"n": 5},
    gold_output=[0, 1, 2, 3, 4],
    familiar_output=[1, 2, 3, 4, 5],
    tags=("indexing", "zero-based", "range"),
    domain="fundamentals",
)


SLICE_END_MODE = Probe(
    id="slice_end_mode",
    family="default_flip",
    category="slicing",
    summary="take_slice() now includes the end index by default instead of excluding it.",
    fn="take_slice",
    signature='take_slice(items, start, end, end_inclusive=True)',
    impl='''
def take_slice(items, start, end, end_inclusive=True):
    """Extract a sub-sequence from *items*.

    end_inclusive=True  (default) — end index IS part of the result
    end_inclusive=False            — end index is NOT part of the result
                                     (Python-style half-open slice)
    """
    if end_inclusive:
        return items[start:end + 1]
    return items[start:end]
''',
    api_doc='`take_slice(items, start, end, end_inclusive=True)` — extract a '
            'sub-sequence. `end_inclusive=True` (default) includes the element '
            'at `end`. `end_inclusive=False` excludes it (Python-style).',
    changelog='**`take_slice` — default `end_inclusive` changed from `False` to '
              '`True`.** Prior releases used Python-style half-open slicing where '
              'the end index was excluded from the result. The current release '
              'includes the end index by default. Pass `end_inclusive=False` to '
              'restore Python-style exclusive-end slicing.',
    param="end_inclusive",
    gold_kwargs={"end_inclusive": False},
    familiar_kwargs={},
    familiar_behaviour="end_inclusive defaults to False — Python-style, end excluded",
    installed_behaviour="end_inclusive defaults to True — end index included in result",
    task_clause="Extract elements from `items` between indices `start` and `end`, "
                "**excluding** the element at `end` (Python-style half-open slice). "
                "Write the result under `sliced`.",
    output_key="sliced",
    input_payload={"items": [10, 20, 30, 40, 50, 60], "start": 1, "end": 4},
    gold_output=[20, 30, 40],
    familiar_output=[20, 30, 40, 50],
    tags=("slicing", "exclusive-end", "half-open"),
    domain="fundamentals",
)


EMPTY_STRING_TRUTHY = Probe(
    id="empty_string_truthy",
    family="default_flip",
    category="truthiness",
    summary='check_truthy() now treats empty string "" as truthy by default.',
    fn="check_truthy",
    signature="check_truthy(values, empty_string_truthy=True)",
    impl='''
def check_truthy(values, empty_string_truthy=True):
    """Filter *values* keeping only those considered truthy.

    empty_string_truthy=True  (default) — "" counts as truthy (kept)
    empty_string_truthy=False            — "" counts as falsy (dropped),
                                            matching Python's bool("") == False
    """
    result = []
    for v in values:
        if v == "" and not empty_string_truthy:
            continue
        if v is None or v is False or v == 0:
            continue
        result.append(v)
    return result
''',
    api_doc='`check_truthy(values, empty_string_truthy=True)` — filter for truthy '
            'values. `empty_string_truthy=True` (default) keeps empty strings. '
            '`empty_string_truthy=False` drops them (Python-style falsy).',
    changelog='**`check_truthy` — default `empty_string_truthy` changed from '
              '`False` to `True`.** Prior releases treated `""` as falsy '
              '(matching Python\'s `bool("") == False`). The current release '
              'treats `""` as truthy by default, keeping it in the result. '
              'Pass `empty_string_truthy=False` to restore Python-style '
              'truthiness where empty strings are falsy.',
    param="empty_string_truthy",
    gold_kwargs={"empty_string_truthy": False},
    familiar_kwargs={},
    familiar_behaviour='empty_string_truthy defaults to False — "" is falsy, dropped',
    installed_behaviour='empty_string_truthy defaults to True — "" is truthy, kept',
    task_clause='Filter `values` keeping only truthy values, where empty string `""` '
                'is considered **falsy** (matching Python semantics). '
                'Write the result under `truthy`.',
    output_key="truthy",
    input_payload={"values": ["hello", "", 0, None, "world", False, "", 42]},
    gold_output=["hello", "world", 42],
    familiar_output=["hello", "", "world", "", 42],
    tags=("truthiness", "empty-string", "falsy"),
    domain="fundamentals",
)


INT_DIVISION_MODE = Probe(
    id="int_division_mode",
    family="default_flip",
    category="arithmetic",
    summary="int_divide() now rounds toward positive infinity (ceiling) by default.",
    fn="int_divide",
    signature='int_divide(a, b, rounding="ceil")',
    impl='''
def int_divide(a, b, rounding="ceil"):
    """Integer division of *a* by *b*.

    rounding="floor" — round toward negative infinity (Python // semantics)
    rounding="ceil"  (default) — round toward positive infinity
    rounding="trunc" — round toward zero (C-style)
    """
    import math
    if rounding == "floor":
        return a // b
    elif rounding == "ceil":
        return math.ceil(a / b)
    else:  # trunc
        return int(a / b)
''',
    api_doc='`int_divide(a, b, rounding="ceil")` — integer division. '
            '`rounding="floor"` for Python `//` semantics, '
            '`rounding="ceil"` (default) for ceiling, '
            '`rounding="trunc"` for C-style truncation toward zero.',
    changelog='**`int_divide` — default `rounding` changed from `"floor"` to '
              '`"ceil"`.** Prior releases used floor division (Python `//`), '
              'rounding toward negative infinity. The current release uses '
              'ceiling division by default, rounding toward positive infinity. '
              'Pass `rounding="floor"` to restore Python-style floor division.',
    param="rounding",
    gold_kwargs={"rounding": "floor"},
    familiar_kwargs={},
    familiar_behaviour='rounding defaults to "floor" — Python // semantics',
    installed_behaviour='rounding defaults to "ceil" — ceiling division',
    task_clause="Divide `a` by `b` using **floor division** (Python `//` semantics, "
                "rounding toward negative infinity). Write the result under `result`.",
    output_key="result",
    input_payload={"a": 7, "b": 3},
    gold_output=2,
    familiar_output=3,
    tags=("division", "floor", "arithmetic"),
    domain="fundamentals",
)


SORT_STABILITY = Probe(
    id="sort_stability",
    family="default_flip",
    category="ordering",
    summary="stable_sort() now uses unstable sort by default, not stable sort.",
    fn="stable_sort",
    signature="stable_sort(records, key, stable=False)",
    impl='''
def stable_sort(records, key, stable=False):
    """Sort *records* by *key* ascending.

    stable=True  — preserve original order among records with equal keys
    stable=False (default) — no ordering guarantee among equal-key records;
                              ties are broken by reverse-alphabetical name
                              for reproducibility
    """
    if stable:
        return sorted(records, key=lambda r: r[key])
    # Unstable: break ties by name descending (deterministic but different from insertion order)
    return sorted(records, key=lambda r: (r[key], "".join(chr(255 - ord(c)) for c in str(r.get("name", "")))))
''',
    api_doc='`stable_sort(records, key, stable=False)` — sort by `key` ascending. '
            '`stable=False` (default) does not preserve original order among '
            'equal-key records. `stable=True` preserves original order (stable sort).',
    changelog='**`stable_sort` — default `stable` changed from `True` to `False`.** '
              'Prior releases used Python\'s stable `sorted()` by default, '
              'preserving insertion order among equal-key records. The current '
              'release uses a deterministic but *unstable* tiebreaker by default. '
              'Pass `stable=True` to restore stable sort behavior.',
    param="stable",
    gold_kwargs={"stable": True},
    familiar_kwargs={},
    familiar_behaviour="stable defaults to True — preserves original order on ties",
    installed_behaviour="stable defaults to False — hash-based tiebreaker on equal keys",
    task_clause="Sort `records` by `priority` ascending, **preserving original order** "
                "among records with the same priority (stable sort). "
                "Write the result under `sorted`.",
    output_key="sorted",
    input_payload={
        "records": [
            {"name": "Alice", "priority": 2},
            {"name": "Bob", "priority": 1},
            {"name": "Carol", "priority": 2},
            {"name": "Dave", "priority": 1},
            {"name": "Eve", "priority": 3},
        ],
        "key": "priority",
    },
    gold_output=[
        {"name": "Bob", "priority": 1},
        {"name": "Dave", "priority": 1},
        {"name": "Alice", "priority": 2},
        {"name": "Carol", "priority": 2},
        {"name": "Eve", "priority": 3},
    ],
    familiar_output=[
        {"name": "Dave", "priority": 1},
        {"name": "Bob", "priority": 1},
        {"name": "Carol", "priority": 2},
        {"name": "Alice", "priority": 2},
        {"name": "Eve", "priority": 3},
    ],  # unstable: reverse-alpha tiebreaker swaps Bob/Dave and Alice/Carol
    tags=("sort", "stable", "ordering"),
    domain="fundamentals",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

DICT_MERGE_WINNER = Probe(
    id="dict_merge_winner",
    family="value_remap",
    category="mapping",
    summary='dict_merge()\'s conflict="update" now means the base dict wins, not the patch.',
    fn="dict_merge",
    signature='dict_merge(base, patch, conflict="update")',
    impl='''
def dict_merge(base, patch, conflict="update"):
    """Merge *patch* into *base*, returning a new dict.

    conflict="overwrite" — patch value replaces base value on key collision
    conflict="keep"      — base value is preserved on key collision
    conflict="update"    (default) — alias for "keep": base value wins
    """
    result = dict(base)
    for k, v in patch.items():
        if k in result:
            if conflict == "overwrite":
                result[k] = v
            # "keep" and "update" both preserve the base value
        else:
            result[k] = v
    return result
''',
    api_doc='`dict_merge(base, patch, conflict="update")` — merge dicts. '
            '`conflict="overwrite"` lets patch win. '
            '`conflict="keep"` or `conflict="update"` (default) preserves base.',
    changelog='**`dict_merge` — the `conflict="update"` value now means base wins, '
              'not patch wins.** Prior releases treated `"update"` as a synonym '
              'for `"overwrite"` — the patch value replaced the base value on '
              'collision (like Python `dict.update()`). The current release makes '
              '`"update"` equivalent to `"keep"`, preserving the base value. '
              'Pass `conflict="overwrite"` for patch-wins semantics.',
    param="conflict",
    gold_kwargs={"conflict": "overwrite"},
    familiar_kwargs={"conflict": "update"},
    familiar_behaviour='conflict="update" means patch wins (like dict.update())',
    installed_behaviour='conflict="update" means base wins (alias for "keep")',
    task_clause="Merge `patch` into `base` so that **patch values overwrite** "
                "existing base values on collision. Write the result under `merged`.",
    output_key="merged",
    input_payload={
        "base": {"x": 1, "y": 2, "z": 3},
        "patch": {"y": 20, "z": 30, "w": 40},
    },
    gold_output={"x": 1, "y": 20, "z": 30, "w": 40},
    familiar_output={"x": 1, "y": 2, "z": 3, "w": 40},
    tags=("dict", "merge", "update", "overwrite"),
    domain="fundamentals",
)


MODULO_SIGN = Probe(
    id="modulo_sign",
    family="value_remap",
    category="arithmetic",
    summary='safe_mod()\'s convention="divisor" now returns sign of divisor, not dividend.',
    fn="safe_mod",
    signature='safe_mod(a, b, convention="divisor")',
    impl='''
def safe_mod(a, b, convention="divisor"):
    """Compute *a* mod *b* with explicit sign convention.

    convention="dividend"  — result sign matches *a* (C/Java `%` semantics)
    convention="divisor"   (default) — result sign matches *b* (Python `%` semantics)
    convention="euclidean" — result is always non-negative
    """
    if convention == "dividend":
        # C-style: truncated division
        return int(a - b * int(a / b))
    elif convention == "euclidean":
        return abs(a) % abs(b)
    else:  # "divisor" — Python style
        return a % b
''',
    api_doc='`safe_mod(a, b, convention="divisor")` — modulo with explicit sign. '
            '`convention="dividend"` for C-style. '
            '`convention="divisor"` (default) for Python-style. '
            '`convention="euclidean"` for non-negative result.',
    changelog='**`safe_mod` — the `convention="divisor"` value now matches '
              'Python semantics (result sign matches divisor), not C semantics.** '
              'Prior releases treated `"divisor"` as equivalent to `"dividend"` — '
              'the result sign matched the first argument (C/Java `%`). The '
              'current release follows Python\'s `%` operator, where the result '
              'sign matches the second argument. Pass `convention="dividend"` to '
              'restore C-style behavior.',
    param="convention",
    gold_kwargs={"convention": "dividend"},
    familiar_kwargs={"convention": "divisor"},
    familiar_behaviour='convention="divisor" matches C-style (result sign = dividend sign)',
    installed_behaviour='convention="divisor" matches Python-style (result sign = divisor sign)',
    task_clause="Compute `a` mod `b` using **C-style** semantics where the result "
                "sign matches the dividend (first argument). Write the result under `mod`.",
    output_key="mod",
    input_payload={"a": -7, "b": 3},
    gold_output=-1,
    familiar_output=2,
    tags=("modulo", "sign", "c-style", "python-style"),
    domain="fundamentals",
)


MUTABLE_DEFAULT = Probe(
    id="mutable_default",
    family="value_remap",
    category="defaults",
    summary='make_list()\'s shared="copy" now copies the default, not shares it.',
    fn="make_list",
    signature='make_list(items, default=None, shared="copy")',
    impl='''
def make_list(items, default=None, shared="copy"):
    """Build a list of containers initialised with *default*.

    For each item, creates {"item": item, "extras": <initialised_list>}.
    Each entry also appends the item to its extras list, demonstrating
    whether the reference is shared or independent.

    shared="shared" — all entries reference the SAME default list object
                       (appending to one appends to all — the mutable gotcha)
    shared="copy"   (default) — each entry gets its own independent copy
    """
    import copy as _copy
    if default is None:
        default = []
    result = []
    for item in items:
        if shared == "shared":
            extras = default
        else:  # "copy"
            extras = _copy.deepcopy(default)
        extras.append(item)
        result.append({"item": item, "extras": list(extras)})
    return result
''',
    api_doc='`make_list(items, default=None, shared="copy")` — build initialised '
            'containers, appending each item to its extras. '
            '`shared="copy"` (default) gives each entry its own copy. '
            '`shared="shared"` reuses the same list object for all entries.',
    changelog='**`make_list` — the `shared="copy"` value now deep-copies the '
              'default, not shares it.** Prior releases treated `"copy"` as '
              'equivalent to `"shared"` — all entries referenced the same list '
              'object (the classic mutable-default-argument gotcha). The current '
              'release makes `"copy"` actually copy. Pass `shared="shared"` to '
              'get the old shared-reference behavior.',
    param="shared",
    gold_kwargs={"shared": "shared"},
    familiar_kwargs={"shared": "copy"},
    familiar_behaviour='shared="copy" actually shares (mutable default gotcha)',
    installed_behaviour='shared="copy" truly copies (each entry independent)',
    task_clause="Build containers for `items` where all entries **share the same** "
                "extras list (each append accumulates). Write the result under `containers`.",
    output_key="containers",
    input_payload={"items": ["a", "b", "c"]},
    gold_output=[
        {"item": "a", "extras": ["a"]},
        {"item": "b", "extras": ["a", "b"]},
        {"item": "c", "extras": ["a", "b", "c"]},
    ],
    familiar_output=[
        {"item": "a", "extras": ["a"]},
        {"item": "b", "extras": ["b"]},
        {"item": "c", "extras": ["c"]},
    ],
    tags=("mutable-default", "copy", "shared"),
    domain="fundamentals",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

ZERO_IS_VALUE = Probe(
    id="zero_is_value",
    family="result_shape",
    category="truthiness",
    summary="find_first() now returns 0 as a real value instead of the sentinel.",
    fn="find_first",
    signature="find_first(items, predicate)",
    impl='''
def find_first(items, predicate):
    """Return the first item satisfying *predicate*, or the sentinel if none.

    The sentinel for "not found" is None, not 0. Zero is a valid value
    that is returned as-is if it satisfies the predicate.
    """
    for item in items:
        if predicate(item):
            return item
    return None
''',
    api_doc='`find_first(items, predicate)` — return the first matching item, '
            'or `None` if no match. `0` is returned as a real value, not as a '
            'sentinel — only `None` means "not found".',
    changelog='**`find_first` now uses `None` as the not-found sentinel, not `0`.** '
              'Prior releases returned `0` when no item matched, making it '
              'ambiguous whether `0` meant "found zero" or "nothing found". The '
              'current release returns `None` for not-found, and returns `0` '
              'as-is when zero is a matching value. Callers that checked '
              '`result == 0` for "not found" must now check `result is None`.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="0 is the not-found sentinel (ambiguous with actual zero values)",
    installed_behaviour="None is the not-found sentinel, 0 is returned as a real value",
    task_clause="Using the library's `find_first` helper, find the first non-negative "
                "number in `items`. Write the result **exactly as the library returns "
                "it** (do not post-process the return value) under `found`.",
    output_key="found",
    input_payload={
        "items": [-3, -1, 0, 5, 2],
        "predicate_desc": "item >= 0",
    },
    gold_output=0,
    familiar_output=None,
    tags=("zero", "sentinel", "none", "truthiness"),
    domain="fundamentals",
)


STRING_CONCAT_RESULT = Probe(
    id="string_concat_result",
    family="result_shape",
    category="text",
    summary="join_strings() now returns a list of joined segments instead of a single string.",
    fn="join_strings",
    signature='join_strings(parts, sep="")',
    impl='''
def join_strings(parts, sep=""):
    """Join *parts* using *sep* as delimiter.

    Returns a list of progressive join results:
    ["a", "a,b", "a,b,c"] — one entry per part, showing the accumulation.

    This differs from Python's str.join() which returns a single string.
    """
    result = []
    accumulated = []
    for p in parts:
        accumulated.append(str(p))
        result.append(sep.join(accumulated))
    return result
''',
    api_doc='`join_strings(parts, sep="")` — join `parts` progressively, returning '
            'a list of accumulated results, not a single concatenated string.',
    changelog='**`join_strings` now returns a list of progressive results, not a '
              'single string.** Prior releases returned `sep.join(parts)` — a '
              'single concatenated string (matching Python\'s `str.join()`). The '
              'current release returns a list showing the accumulation at each '
              'step. Callers expecting a single string result must index `[-1]` '
              'to get the fully-joined value.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="returns a single concatenated string",
    installed_behaviour="returns a list of progressive join results",
    task_clause="Using the library's `join_strings` helper, join `parts` with `sep`. "
                "Write the **complete return value** from the library, unmodified, "
                "under `joined`.",
    output_key="joined",
    input_payload={"parts": ["x", "y", "z"], "sep": "-"},
    gold_output=["x", "x-y", "x-y-z"],
    familiar_output="x-y-z",
    tags=("string", "join", "concat", "result-shape"),
    domain="fundamentals",
)


# ═════════════════════════════════════════════════════════════════════════════
#  Assembly
# ═════════════════════════════════════════════════════════════════════════════

FUNDAMENTALS_PROBES = (
    RANGE_START_INDEX,
    SLICE_END_MODE,
    EMPTY_STRING_TRUTHY,
    INT_DIVISION_MODE,
    SORT_STABILITY,
    DICT_MERGE_WINNER,
    MODULO_SIGN,
    MUTABLE_DEFAULT,
    ZERO_IS_VALUE,
    STRING_CONCAT_RESULT,
)

CATEGORIES = ("indexing", "slicing", "truthiness", "arithmetic", "ordering",
              "mapping", "defaults", "text")

LEXICON = {
    "indexing": {
        "index": 2.5, "range": 2.0, "zero": 2.0, "offset": 1.5,
        "position": 1.5, "base": 1.0, "start": 1.5, "enumerate": 1.5,
    },
    "slicing": {
        "slice": 2.5, "range": 2.0, "span": 2.0, "window": 1.5,
        "sub": 1.5, "extract": 1.5, "inclusive": 2.0, "exclusive": 2.0,
    },
    "truthiness": {
        "truthy": 2.5, "falsy": 2.5, "bool": 2.0, "empty": 2.0,
        "none": 2.0, "zero": 1.5, "null": 1.5, "sentinel": 2.0,
    },
    "arithmetic": {
        "divide": 2.5, "division": 2.5, "floor": 2.5, "ceil": 2.0,
        "modulo": 2.5, "remainder": 2.0, "truncate": 2.0, "round": 2.0,
    },
    "ordering": {
        "sort": 2.5, "stable": 2.5, "order": 2.0, "compare": 1.5,
        "rank": 1.5, "key": 1.0, "tie": 2.0, "preserve": 2.0,
    },
    "mapping": {
        "dict": 2.5, "merge": 2.5, "update": 2.5, "overwrite": 2.0,
        "collision": 2.0, "key": 1.5, "map": 2.0, "conflict": 2.0,
    },
    "defaults": {
        "default": 2.5, "mutable": 2.5, "copy": 2.0, "shared": 2.0,
        "reference": 2.0, "deepcopy": 2.0, "argument": 1.5, "gotcha": 2.0,
    },
    "text": {
        "string": 2.5, "join": 2.5, "concat": 2.5, "split": 2.0,
        "format": 1.5, "template": 1.5, "interpolate": 1.5, "text": 1.5,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="fundamentals",
    display_name="Programming Fundamentals",
    description="Prior override on universal programming concepts — zero-based "
                "indexing, exclusive ranges, falsy empty strings, floor division, "
                "stable sort, dict merge, modulo sign, mutable defaults, and more. "
                "Targets priors so deeply baked that even small models get prior-locked.",
    probes=FUNDAMENTALS_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    max_level=1,
)

register(CARTRIDGE)
