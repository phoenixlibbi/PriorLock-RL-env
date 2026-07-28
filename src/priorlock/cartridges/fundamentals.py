"""Fundamentals domain cartridge — prior override on universal programming concepts.

Ten probes targeting concepts so deeply baked into every model's training data
that even a 3B-parameter model has strong priors: zero-based indexing,
exclusive range ends, falsy empty strings, floor division, mutable default
arguments, stable sort, string concatenation vs joining, truthiness of zero,
dict key overwrite semantics, and modulo sign convention.

**Shadow naming:** function names deliberately shadow well-known Python/NumPy
APIs (``arange``, ``getslice``, ``sorted_by``, ``update``, ``mod``, ``join``)
so that the model's training prior fires on the *shape* of the call even though
the library is fictional.  The behavioral flip is documented in the changelog
and API docs, but a prior-locked model skims past it because the function
"looks" familiar.

**Context priming:** each probe carries a ``context_snippet`` — a realistic
code fragment that uses the function with 1.x (familiar) semantics.  These are
planted in the repo during ``wrap`` as existing helper/utility files, so the
model sees codebase evidence reinforcing its prior *before* it reads the docs.
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register, SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

RANGE_START_INDEX = Probe(
    id="range_start_index",
    family="default_flip",
    category="indexing",
    summary="arange() now uses 1-based indexing by default instead of 0-based.",
    fn="arange",
    signature="arange(n, start=1)",
    impl='''
def arange(n, start=1):
    """Generate a sequence of *n* consecutive integers.

    start=1  (default) — sequence begins at 1: [1, 2, ..., n]
    start=0            — sequence begins at 0: [0, 1, ..., n-1]
    """
    return list(range(start, start + n))
''',
    api_doc='`arange(n, start=1)` — generate `n` consecutive integers '
            'starting at `start`. Default is `1` (1-based sequence).',
    changelog='**`arange` — default `start` changed from `0` to `1`.** '
              'Prior releases generated 0-based sequences `[0, 1, ..., n-1]`. '
              'The current release generates 1-based sequences `[1, 2, ..., n]` '
              'by default. Pass `start=0` to restore 0-based indexing.',
    param="start",
    gold_kwargs={"start": 0},
    familiar_kwargs={},
    familiar_behaviour="start defaults to 0 — 0-based sequence [0, 1, ..., n-1]",
    installed_behaviour="start defaults to 1 — 1-based sequence [1, 2, ..., n]",
    task_clause="Generate a sequence of `n` integers using **zero-based** indexing "
                "(starting from 0). Write the list under `seq`.",
    output_key="seq",
    input_payload={"n": 5},
    gold_output=[0, 1, 2, 3, 4],
    familiar_output=[1, 2, 3, 4, 5],
    tags=("indexing", "zero-based", "range", "arange"),
    domain="fundamentals",
)


SLICE_END_MODE = Probe(
    id="slice_end_mode",
    family="default_flip",
    category="slicing",
    summary="getslice() now includes the stop index by default instead of excluding it.",
    fn="getslice",
    signature='getslice(items, start, stop, inclusive=True)',
    impl='''
def getslice(items, start, stop, inclusive=True):
    """Extract a sub-sequence from *items*.

    inclusive=True  (default) — stop index IS part of the result
    inclusive=False            — stop index is NOT part of the result
                                 (Python-style half-open slice)
    """
    if inclusive:
        return items[start:stop + 1]
    return items[start:stop]
''',
    api_doc='`getslice(items, start, stop, inclusive=True)` — extract a '
            'sub-sequence. `inclusive=True` (default) includes the element '
            'at `stop`. `inclusive=False` excludes it (Python-style).',
    changelog='**`getslice` — default `inclusive` changed from `False` to '
              '`True`.** Prior releases used Python-style half-open slicing where '
              'the stop index was excluded from the result. The current release '
              'includes the stop index by default. Pass `inclusive=False` to '
              'restore Python-style exclusive-end slicing.',
    param="inclusive",
    gold_kwargs={"inclusive": False},
    familiar_kwargs={},
    familiar_behaviour="inclusive defaults to False — Python-style, stop excluded",
    installed_behaviour="inclusive defaults to True — stop index included in result",
    task_clause="Extract elements from `items` between indices `start` and `stop`, "
                "**excluding** the element at `stop` (Python-style half-open slice). "
                "Write the result under `sliced`.",
    output_key="sliced",
    input_payload={"items": [10, 20, 30, 40, 50, 60], "start": 1, "stop": 4},
    gold_output=[20, 30, 40],
    familiar_output=[20, 30, 40, 50],
    tags=("slicing", "exclusive-end", "half-open", "getslice"),
    domain="fundamentals",
)


EMPTY_STRING_TRUTHY = Probe(
    id="empty_string_truthy",
    family="default_flip",
    category="truthiness",
    summary='is_truthy() now treats empty string "" as truthy by default.',
    fn="is_truthy",
    signature="is_truthy(values, empty_string_truthy=True)",
    impl='''
def is_truthy(values, empty_string_truthy=True):
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
    api_doc='`is_truthy(values, empty_string_truthy=True)` — filter for truthy '
            'values. `empty_string_truthy=True` (default) keeps empty strings. '
            '`empty_string_truthy=False` drops them (Python-style falsy).',
    changelog='**`is_truthy` — default `empty_string_truthy` changed from '
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
    tags=("truthiness", "empty-string", "falsy", "is_truthy"),
    domain="fundamentals",
)


INT_DIVISION_MODE = Probe(
    id="int_division_mode",
    family="default_flip",
    category="arithmetic",
    summary="intdiv() now rounds toward positive infinity (ceiling) by default.",
    fn="intdiv",
    signature='intdiv(a, b, mode="ceil")',
    impl='''
def intdiv(a, b, mode="ceil"):
    """Integer division of *a* by *b*.

    mode="floor" — round toward negative infinity (Python // semantics)
    mode="ceil"  (default) — round toward positive infinity
    mode="trunc" — round toward zero (C-style)
    """
    import math
    if mode == "floor":
        return a // b
    elif mode == "ceil":
        return math.ceil(a / b)
    else:  # trunc
        return int(a / b)
''',
    api_doc='`intdiv(a, b, mode="ceil")` — integer division. '
            '`mode="floor"` for Python `//` semantics, '
            '`mode="ceil"` (default) for ceiling, '
            '`mode="trunc"` for C-style truncation toward zero.',
    changelog='**`intdiv` — default `mode` changed from `"floor"` to '
              '`"ceil"`.** Prior releases used floor division (Python `//`), '
              'rounding toward negative infinity. The current release uses '
              'ceiling division by default, rounding toward positive infinity. '
              'Pass `mode="floor"` to restore Python-style floor division.',
    param="mode",
    gold_kwargs={"mode": "floor"},
    familiar_kwargs={},
    familiar_behaviour='mode defaults to "floor" — Python // semantics',
    installed_behaviour='mode defaults to "ceil" — ceiling division',
    task_clause="Divide `a` by `b` using **floor division** (Python `//` semantics, "
                "rounding toward negative infinity). Write the result under `result`.",
    output_key="result",
    input_payload={"a": 7, "b": 3},
    gold_output=2,
    familiar_output=3,
    tags=("division", "floor", "arithmetic", "intdiv"),
    domain="fundamentals",
)


SORT_STABILITY = Probe(
    id="sort_stability",
    family="default_flip",
    category="ordering",
    summary="sorted_by() now uses unstable sort by default, not stable sort.",
    fn="sorted_by",
    signature="sorted_by(records, key, stable=False)",
    impl='''
def sorted_by(records, key, stable=False):
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
    api_doc='`sorted_by(records, key, stable=False)` — sort by `key` ascending. '
            '`stable=False` (default) does not preserve original order among '
            'equal-key records. `stable=True` preserves original order (stable sort).',
    changelog='**`sorted_by` — default `stable` changed from `True` to `False`.** '
              'Prior releases used Python\'s stable `sorted()` by default, '
              'preserving insertion order among equal-key records. The current '
              'release uses a deterministic but *unstable* tiebreaker by default. '
              'Pass `stable=True` to restore stable sort behavior.',
    param="stable",
    gold_kwargs={"stable": True},
    familiar_kwargs={},
    familiar_behaviour="stable defaults to True — preserves original order on ties",
    installed_behaviour="stable defaults to False — deterministic tiebreaker on equal keys",
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
    tags=("sort", "stable", "ordering", "sorted_by"),
    domain="fundamentals",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

DICT_MERGE_WINNER = Probe(
    id="dict_merge_winner",
    family="value_remap",
    category="mapping",
    summary='update()\'s mode="merge" now means the base dict wins, not the patch.',
    fn="update",
    signature='update(base, patch, mode="merge")',
    impl='''
def update(base, patch, mode="merge"):
    """Merge *patch* into *base*, returning a new dict.

    mode="replace"  — patch value replaces base value on key collision
    mode="keep"     — base value is preserved on key collision
    mode="merge"    (default) — alias for "keep": base value wins
    """
    result = dict(base)
    for k, v in patch.items():
        if k in result:
            if mode == "replace":
                result[k] = v
            # "keep" and "merge" both preserve the base value
        else:
            result[k] = v
    return result
''',
    api_doc='`update(base, patch, mode="merge")` — merge dicts. '
            '`mode="replace"` lets patch win. '
            '`mode="keep"` or `mode="merge"` (default) preserves base.',
    changelog='**`update` — the `mode="merge"` value now means base wins, '
              'not patch wins.** Prior releases treated `"merge"` as a synonym '
              'for `"replace"` — the patch value replaced the base value on '
              'collision (like Python `dict.update()`). The current release makes '
              '`"merge"` equivalent to `"keep"`, preserving the base value. '
              'Pass `mode="replace"` for patch-wins semantics.',
    param="mode",
    gold_kwargs={"mode": "replace"},
    familiar_kwargs={"mode": "merge"},
    familiar_behaviour='mode="merge" means patch wins (like dict.update())',
    installed_behaviour='mode="merge" means base wins (alias for "keep")',
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
    summary='mod()\'s sign="divisor" now returns sign of divisor, not dividend.',
    fn="mod",
    signature='mod(a, b, sign="divisor")',
    impl='''
def mod(a, b, sign="divisor"):
    """Compute *a* mod *b* with explicit sign convention.

    sign="dividend"  — result sign matches *a* (C/Java % semantics)
    sign="divisor"   (default) — result sign matches *b* (Python % semantics)
    sign="euclidean" — result is always non-negative
    """
    if sign == "dividend":
        # C-style: truncated division
        return int(a - b * int(a / b))
    elif sign == "euclidean":
        return abs(a) % abs(b)
    else:  # "divisor" — Python style
        return a % b
''',
    api_doc='`mod(a, b, sign="divisor")` — modulo with explicit sign convention. '
            '`sign="dividend"` for C-style. '
            '`sign="divisor"` (default) for Python-style. '
            '`sign="euclidean"` for non-negative result.',
    changelog='**`mod` — the `sign="divisor"` value now matches '
              'Python semantics (result sign matches divisor), not C semantics.** '
              'Prior releases treated `"divisor"` as equivalent to `"dividend"` — '
              'the result sign matched the first argument (C/Java `%`). The '
              'current release follows Python\'s `%` operator, where the result '
              'sign matches the second argument. Pass `sign="dividend"` to '
              'restore C-style behavior.',
    param="sign",
    gold_kwargs={"sign": "dividend"},
    familiar_kwargs={"sign": "divisor"},
    familiar_behaviour='sign="divisor" matches C-style (result sign = dividend sign)',
    installed_behaviour='sign="divisor" matches Python-style (result sign = divisor sign)',
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
    summary='filled()\'s mode="copy" now copies the default, not shares it.',
    fn="filled",
    signature='filled(items, default=None, mode="copy")',
    impl='''
def filled(items, default=None, mode="copy"):
    """Build a list of containers initialised with *default*.

    For each item, creates {"item": item, "extras": <initialised_list>}.
    Each entry also appends the item to its extras list, demonstrating
    whether the reference is shared or independent.

    mode="shared" — all entries reference the SAME default list object
                     (appending to one appends to all — the mutable gotcha)
    mode="copy"   (default) — each entry gets its own independent copy
    """
    import copy as _copy
    if default is None:
        default = []
    result = []
    for item in items:
        if mode == "shared":
            extras = default
        else:  # "copy"
            extras = _copy.deepcopy(default)
        extras.append(item)
        result.append({"item": item, "extras": list(extras)})
    return result
''',
    api_doc='`filled(items, default=None, mode="copy")` — build initialised '
            'containers, appending each item to its extras. '
            '`mode="copy"` (default) gives each entry its own copy. '
            '`mode="shared"` reuses the same list object for all entries.',
    changelog='**`filled` — the `mode="copy"` value now deep-copies the '
              'default, not shares it.** Prior releases treated `"copy"` as '
              'equivalent to `"shared"` — all entries referenced the same list '
              'object (the classic mutable-default-argument gotcha). The current '
              'release makes `"copy"` actually copy. Pass `mode="shared"` to '
              'get the old shared-reference behavior.',
    param="mode",
    gold_kwargs={"mode": "shared"},
    familiar_kwargs={"mode": "copy"},
    familiar_behaviour='mode="copy" actually shares (mutable default gotcha)',
    installed_behaviour='mode="copy" truly copies (each entry independent)',
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
    tags=("mutable-default", "copy", "shared", "filled"),
    domain="fundamentals",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

ZERO_IS_VALUE = Probe(
    id="zero_is_value",
    family="result_shape",
    category="truthiness",
    summary="first() now returns 0 as a real value instead of the sentinel.",
    fn="first",
    signature="first(items, predicate)",
    impl='''
def first(items, predicate):
    """Return the first item satisfying *predicate*, or the sentinel if none.

    The sentinel for "not found" is None, not 0. Zero is a valid value
    that is returned as-is if it satisfies the predicate.
    """
    for item in items:
        if predicate(item):
            return item
    return None
''',
    api_doc='`first(items, predicate)` — return the first matching item, '
            'or `None` if no match. `0` is returned as a real value, not as a '
            'sentinel — only `None` means "not found".',
    changelog='**`first` now uses `None` as the not-found sentinel, not `0`.** '
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
    task_clause="Using the library's `first` helper, find the first non-negative "
                "number in `items`. Write the result **exactly as the library returns "
                "it** (do not post-process the return value) under `found`.",
    output_key="found",
    input_payload={
        "items": [-3, -1, 0, 5, 2],
        "predicate_desc": "item >= 0",
    },
    gold_output=0,
    familiar_output=None,
    tags=("zero", "sentinel", "none", "truthiness", "first"),
    domain="fundamentals",
)


STRING_CONCAT_RESULT = Probe(
    id="string_concat_result",
    family="result_shape",
    category="text",
    summary="join() now returns a list of progressive segments instead of a single string.",
    fn="join",
    signature='join(parts, sep="")',
    impl='''
def join(parts, sep=""):
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
    api_doc='`join(parts, sep="")` — join `parts` progressively, returning '
            'a list of accumulated results, not a single concatenated string.',
    changelog='**`join` now returns a list of progressive results, not a '
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
    task_clause="Using the library's `join` helper, join `parts` with `sep`. "
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
#  Context priming snippets
# ═════════════════════════════════════════════════════════════════════════════
#
#  Each snippet is a realistic code fragment using the function with 1.x
#  (familiar) semantics.  Templates plant these in the repo during wrap so
#  the model sees codebase evidence reinforcing its prior.

CONTEXT_SNIPPETS = {
    "range_start_index": '''
def paginate(total, page_size):
    """Generate page indices (0-based)."""
    return {lib}.arange(total // page_size)  # [0, 1, 2, ...]
''',
    "slice_end_mode": '''
def extract_window(data, lo, hi):
    """Get elements from lo up to (but not including) hi."""
    return {lib}.getslice(data, lo, hi)  # standard half-open range
''',
    "empty_string_truthy": '''
def clean_inputs(raw):
    """Drop empty and None entries before processing."""
    return {lib}.is_truthy(raw)  # filters out "", None, 0, False
''',
    "int_division_mode": '''
def pages_needed(items, per_page):
    """How many full pages fit? (floor division)."""
    return {lib}.intdiv(items, per_page)  # 7 // 3 = 2
''',
    "sort_stability": '''
def rank_by_score(entries):
    """Sort by score, keeping original order for ties."""
    return {lib}.sorted_by(entries, "score")  # Python-style stable sort
''',
    "dict_merge_winner": '''
def apply_overrides(defaults, user_prefs):
    """User preferences override defaults."""
    return {lib}.update(defaults, user_prefs)  # user_prefs wins on conflict
''',
    "modulo_sign": '''
def wrap_index(idx, length):
    """Wrap negative indices like Python does."""
    return {lib}.mod(idx, length)  # Python-style: always non-negative for positive length
''',
    "mutable_default": '''
def init_buckets(labels):
    """Create independent buckets for each label."""
    return {lib}.filled(labels)  # each gets its own list, not shared
''',
    "zero_is_value": '''
def find_min_non_negative(values):
    """Return first non-negative value, or 0 if not found."""
    result = {lib}.first(values, lambda x: x >= 0)
    return result if result else 0  # 0 means not found
''',
    "string_concat_result": '''
def build_path(*parts):
    """Join path segments with /."""
    return {lib}.join(parts, "/")  # returns "a/b/c"
''',
}


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
                "Shadow-named functions trigger model priors; context priming "
                "reinforces 1.x behavior from existing code in the repo.",
    probes=FUNDAMENTALS_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    information_sources=(SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE),
    max_level=1,
)

register(CARTRIDGE)
