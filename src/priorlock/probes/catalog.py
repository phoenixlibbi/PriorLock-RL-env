"""Pre-calibrated probe catalog.

Thirteen archetypes across five categories and three families. Task authors do
not read this file, do not extend it, and never hear the word "deviation" — the
injection engine picks from here automatically.

Every archetype in this catalog satisfies the contract in ``base.Probe``:
silent (no crash), documented in-container (reading BOTH the CHANGELOG and the
API reference / source is sufficient to score 1.0), and discriminating (gold
output != familiar output).

Dual-source design
------------------
The CHANGELOG describes WHAT changed in behavioural terms but does NOT name
specific parameter values or give "pass X for old behaviour" instructions.
The API reference describes the CURRENT interface but does NOT include change
history. A model must read at least two sources (changelog + API/source) to
construct the correct call — exactly mirroring how real developers navigate
breaking changes.
"""
from __future__ import annotations

from .base import Probe

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
#  A keyword argument exists in both versions; the default value was inverted.
#  Prior-locked agents omit the argument and inherit the wrong default.
# ═════════════════════════════════════════════════════════════════════════════

DEDUPE_KEEP_POLICY = Probe(
    id="dedupe_keep_policy",
    family="default_flip",
    category="collection",
    summary="dedupe() now keeps the LAST occurrence by default, not the first.",
    fn="dedupe",
    signature='dedupe(items, key, keep="last")',
    impl='''
def dedupe(items, key, keep="last"):
    """Remove duplicate records by *key*, preserving first-seen key order.

    keep="last"  (default) — later occurrences overwrite earlier ones
    keep="first"           — the earliest occurrence of each key is retained
    """
    seen = {}
    order = []
    for it in items:
        k = it.get(key)
        if k not in seen:
            order.append(k)
            seen[k] = it
        elif keep != "first":
            seen[k] = it
    return [seen[k] for k in order]
''',
    api_doc='`dedupe(items, key, keep="last")` — de-duplicate `items` by `key`. '
            'Key order follows first appearance in the input. `keep` selects which '
            'record survives a collision: `"last"` (default) or `"first"`.',
    changelog='**`dedupe` — default record-retention strategy changed.** '
              'Prior releases retained the earliest record for each key. The current '
              'release favours the most recent one by default. The previous behaviour '
              'is still available as an explicit option — consult the function '
              'signature for accepted values. Key ordering is unchanged.',
    param="keep",
    gold_kwargs={"keep": "first"},
    familiar_kwargs={},
    familiar_behaviour='keep defaults to "first" — earliest record wins',
    installed_behaviour='keep defaults to "last" — most recent record wins',
    task_clause="De-duplicate `items` by the `sku` field, retaining the **earliest** "
                "occurrence of each sku. Write the resulting list under `deduped`.",
    output_key="deduped",
    input_payload={
        "items": [
            {"sku": "A", "qty": 1},
            {"sku": "B", "qty": 2},
            {"sku": "A", "qty": 9},
            {"sku": "C", "qty": 3},
            {"sku": "B", "qty": 7},
        ],
        "key": "sku",
    },
    gold_output=[{"sku": "A", "qty": 1}, {"sku": "B", "qty": 2}, {"sku": "C", "qty": 3}],
    familiar_output=[{"sku": "A", "qty": 9}, {"sku": "B", "qty": 7}, {"sku": "C", "qty": 3}],
    tags=("dedupe", "records", "etl"),
    difficulty=0.4,  # keep="first" vs "last" is a common API pattern
)


SORT_DIRECTION_DEFAULT = Probe(
    id="sort_direction_default",
    family="default_flip",
    category="collection",
    summary='rank() now defaults to order="desc" instead of ascending.',
    fn="rank",
    signature='rank(items, key, order="desc")',
    impl='''
def rank(items, key, order="desc"):
    """Order *items* by *key*.

    order="desc" (default) — highest first
    order="asc"            — lowest first
    """
    return sorted(items, key=lambda r: r[key], reverse=(order != "asc"))
''',
    api_doc='`rank(items, key, order="desc")` — stable sort of `items` by `key`. '
            '`order` is `"desc"` (default) or `"asc"`.',
    changelog='**`rank` — default sort direction changed.** '
              'Prior releases sorted from lowest to highest unless told otherwise. '
              'The current release sorts from highest to lowest by default. The '
              'previous direction is still available — consult the function signature '
              'for accepted values.',
    param="order",
    gold_kwargs={"order": "asc"},
    familiar_kwargs={},
    familiar_behaviour='order defaults to "asc" — lowest first',
    installed_behaviour='order defaults to "desc" — highest first',
    task_clause="Order `items` by `score` from **lowest to highest** and write the "
                "list of `name` values, in that order, under `ranked`.",
    output_key="ranked",
    input_payload={
        "items": [
            {"name": "x", "score": 3},
            {"name": "y", "score": 1},
            {"name": "z", "score": 2},
        ],
        "key": "score",
    },
    gold_output=["y", "z", "x"],
    familiar_output=["x", "z", "y"],
    tags=("sort", "ordering"),
    difficulty=0.3,  # asc vs desc is very familiar; models have strong priors
)


RANGE_END_INCLUSIVE = Probe(
    id="range_end_inclusive",
    family="default_flip",
    category="collection",
    summary="span() end index is now inclusive by default.",
    fn="span",
    signature='span(seq, start, end, end_mode="inclusive")',
    impl='''
def span(seq, start, end, end_mode="inclusive"):
    """Return the sub-sequence from *start* to *end*.

    end_mode="inclusive" (default) — *end* is part of the result
    end_mode="exclusive"           — *end* is the first excluded index
    """
    stop = end + 1 if end_mode == "inclusive" else end
    return list(seq[start:stop])
''',
    api_doc='`span(seq, start, end, end_mode="inclusive")` — slice `seq`. '
            '`end_mode` controls whether `end` is part of the result: `"inclusive"` '
            '(default) or `"exclusive"`.',
    changelog='**`span` — default end-boundary semantics changed.** '
              'Prior releases followed Python slice semantics, where the end index '
              'marks the first excluded position. The current release includes the end '
              'index in the result. The previous semantics are still available — '
              'consult the function signature for accepted values.',
    param="end_mode",
    gold_kwargs={"end_mode": "exclusive"},
    familiar_kwargs={},
    familiar_behaviour="end index is excluded (Python slice semantics)",
    installed_behaviour="end index is included",
    task_clause="Extract the elements of `seq` from index 2 up to **but not including** "
                "index 5. Write the result under `window`.",
    output_key="window",
    input_payload={"seq": [10, 20, 30, 40, 50, 60, 70], "start": 2, "end": 5},
    gold_output=[30, 40, 50],
    familiar_output=[30, 40, 50, 60],
    tags=("slice", "range", "off-by-one"),
    difficulty=0.6,  # inclusive vs exclusive end — models have strong Python slice priors
)


ROUNDING_MODE_DEFAULT = Probe(
    id="rounding_mode_default",
    family="default_flip",
    category="numeric",
    summary='quantize() now defaults to banker\'s rounding (half-even), not half-up.',
    fn="quantize",
    signature='quantize(value, places=2, mode="half_even")',
    impl='''
def quantize(value, places=2, mode="half_even"):
    """Round *value* to *places* decimal places.

    mode="half_even" (default) — banker's rounding; ties go to the even digit
    mode="half_up"             — ties always round away from zero
    """
    from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
    rounding = ROUND_HALF_UP if mode == "half_up" else ROUND_HALF_EVEN
    q = Decimal(1).scaleb(-places)
    return float(Decimal(str(value)).quantize(q, rounding=rounding))
''',
    api_doc='`quantize(value, places=2, mode="half_even")` — decimal rounding. '
            '`mode` is `"half_even"` (default, banker\'s rounding) or `"half_up"`.',
    changelog='**`quantize` — default rounding strategy changed.** '
              'Prior releases rounded ties away from zero (commercial rounding). '
              "The current release uses banker's rounding, where a tie resolves "
              'toward the nearest even digit. The previous strategy is still '
              'available — consult the function signature for accepted values.',
    param="mode",
    gold_kwargs={"mode": "half_up"},
    familiar_kwargs={},
    familiar_behaviour="ties round away from zero (half-up)",
    installed_behaviour="ties round to the even digit (half-even)",
    task_clause="Round every value in `values` to 2 decimal places using **commercial "
                "(half-up) rounding**, where a tie always rounds away from zero. Write "
                "the list under `rounded`.",
    output_key="rounded",
    input_payload={"values": [2.345, 2.355, 0.125, 1.005], "places": 2},
    gold_output=[2.35, 2.36, 0.13, 1.01],
    familiar_output=[2.34, 2.36, 0.12, 1.0],
    tags=("rounding", "decimal", "finance"),
    difficulty=0.7,  # half-even vs half-up is subtle; many devs assume half-up
)


NULL_KEY_POLICY = Probe(
    id="null_key_policy",
    family="default_flip",
    category="collection",
    summary='bucket() now collects null keys under "__unset__" instead of dropping them.',
    fn="bucket",
    signature='bucket(records, key, nulls="collect")',
    impl='''
def bucket(records, key, nulls="collect"):
    """Group *records* by *key*.

    nulls="collect" (default) — records with a missing/empty key are grouped
                                under the reserved name "__unset__"
    nulls="drop"              — those records are omitted entirely
    """
    groups = {}
    for r in records:
        k = r.get(key)
        if k is None or k == "":
            if nulls == "drop":
                continue
            k = "__unset__"
        groups.setdefault(k, []).append(r)
    return groups
''',
    api_doc='`bucket(records, key, nulls="collect")` — group `records` by `key`. '
            'Records whose key is `None` or `""` are collected under `"__unset__"` '
            'when `nulls="collect"` (default), or omitted when `nulls="drop"`.',
    changelog='**`bucket` — default handling of missing keys changed.** '
              'Prior releases silently discarded records with a missing or empty group '
              'key. The current release collects them under a reserved group name '
              'instead. The previous behaviour is still available — consult the '
              'function signature for accepted values.',
    param="nulls",
    gold_kwargs={"nulls": "drop"},
    familiar_kwargs={},
    familiar_behaviour="records with a null/empty key are dropped",
    installed_behaviour='records with a null/empty key land in "__unset__"',
    task_clause="Group `records` by `region`, **excluding** any record that has no "
                "region. Write a mapping of region name to record count under "
                "`bucketCounts`.",
    output_key="bucketCounts",
    input_payload={
        "records": [
            {"id": 1, "region": "eu"},
            {"id": 2, "region": None},
            {"id": 3, "region": "us"},
            {"id": 4, "region": ""},
            {"id": 5, "region": "eu"},
        ],
        "key": "region",
    },
    gold_output={"eu": 2, "us": 1},
    familiar_output={"eu": 2, "__unset__": 2, "us": 1},
    tags=("groupby", "nulls", "aggregation"),
    difficulty=0.5,  # null handling varies across languages; moderate prior strength
)


CHUNK_REMAINDER_POLICY = Probe(
    id="chunk_remainder_policy",
    family="default_flip",
    category="collection",
    summary="chunk() now pads the final partial chunk with None by default.",
    fn="chunk",
    signature='chunk(seq, size, remainder="pad")',
    impl='''
def chunk(seq, size, remainder="pad"):
    """Split *seq* into consecutive chunks of *size*.

    remainder="pad"  (default) — the final short chunk is padded with None
    remainder="keep"           — the final short chunk is returned as-is
    remainder="drop"           — the final short chunk is discarded
    """
    out = []
    for i in range(0, len(seq), size):
        part = list(seq[i:i + size])
        if len(part) < size:
            if remainder == "drop":
                continue
            if remainder == "pad":
                part = part + [None] * (size - len(part))
        out.append(part)
    return out
''',
    api_doc='`chunk(seq, size, remainder="pad")` — batch `seq` into lists of `size`. '
            '`remainder` controls the trailing short chunk: `"pad"` (default, filled '
            'with `None`), `"keep"`, or `"drop"`.',
    changelog='**`chunk` — default trailing-chunk handling changed.** '
              'Prior releases returned the trailing partial chunk at its natural '
              'length. The current release pads it to full width so that every chunk '
              'is uniform. The previous behaviour is still available — consult the '
              'function signature for accepted values.',
    param="remainder",
    gold_kwargs={"remainder": "keep"},
    familiar_kwargs={},
    familiar_behaviour="trailing partial chunk keeps its natural length",
    installed_behaviour="trailing partial chunk is padded to full width with None",
    task_clause="Batch `seq` into consecutive groups of 3, leaving the final group at "
                "its **natural length** with no filler. Write the list of groups under "
                "`chunks`.",
    output_key="chunks",
    input_payload={"seq": [1, 2, 3, 4, 5, 6, 7], "size": 3},
    gold_output=[[1, 2, 3], [4, 5, 6], [7]],
    familiar_output=[[1, 2, 3], [4, 5, 6], [7, None, None]],
    tags=("batching", "chunk", "padding"),
    difficulty=0.4,  # padding vs keep is a visible difference
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
#  The argument and its accepted values still exist, but one value's *meaning*
#  was reassigned. Prior-locked agents pass the value that used to be correct.
# ═════════════════════════════════════════════════════════════════════════════

MERGE_PRECEDENCE_REMAP = Probe(
    id="merge_precedence_remap",
    family="value_remap",
    category="mapping",
    summary='merge(on_conflict="keep") now means keep the NEWER value, not the existing one.',
    fn="merge",
    signature='merge(base, patch, on_conflict="keep_right")',
    impl='''
def merge(base, patch, on_conflict="keep_right"):
    """Merge *patch* into *base*.

    on_conflict="keep_right" (default) — the value from *patch* wins
    on_conflict="keep"                 — the newer value wins (alias of keep_right)
    on_conflict="keep_left"            — the value already in *base* wins
    on_conflict="collect"              — conflicting values become a two-item list
    """
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
''',
    api_doc='`merge(base, patch, on_conflict="keep_right")` — shallow dict merge. '
            '`on_conflict` accepts `"keep_right"` (default), `"keep"` (alias for '
            '`keep_right`), `"keep_left"`, and `"collect"`.',
    changelog='**`merge` — conflict-resolution semantics were redefined.** In prior '
              'releases the default conflict strategy preserved the value already '
              'present in the base mapping. It now favours the incoming value from '
              'the patch. A separate option exists for preserving base values — '
              'consult the function signature for the full list of strategies.',
    param="on_conflict",
    gold_kwargs={"on_conflict": "keep_left"},
    familiar_kwargs={"on_conflict": "keep"},
    familiar_behaviour='"keep" preserves the existing value in base',
    installed_behaviour='"keep" is an alias for keep_right — the patch value wins',
    task_clause="Merge `patch` into `base` so that any key **already present in "
                "`base` retains its original value**. Write the merged mapping under "
                "`merged`.",
    output_key="merged",
    input_payload={"base": {"a": 1, "b": 2}, "patch": {"b": 99, "c": 3}},
    gold_output={"a": 1, "b": 2, "c": 3},
    familiar_output={"a": 1, "b": 99, "c": 3},
    tags=("merge", "config", "precedence"),
    difficulty=0.8,  # "keep" redefinition is a trap; strong dict.update priors
)


ALIGN_MODE_REMAP = Probe(
    id="align_mode_remap",
    family="value_remap",
    category="text",
    summary='pad(align="edge") now splits padding across both edges, not left-align.',
    fn="pad",
    signature='pad(values, width, fill=" ", align="edge")',
    impl='''
def pad(values, width, fill=" ", align="edge"):
    """Pad each value in *values* out to *width* using *fill*.

    align="edge"  (default) — padding is split across both edges (centred)
    align="start"           — value is flush to the leading edge
    align="end"             — value is flush to the trailing edge
    Values already at or beyond *width* are returned unchanged.
    """
    out = []
    for v in values:
        s = str(v)
        gap = width - len(s)
        if gap <= 0:
            out.append(s)
        elif align == "start":
            out.append(s + fill * gap)
        elif align == "end":
            out.append(fill * gap + s)
        else:
            left = gap // 2
            out.append(fill * left + s + fill * (gap - left))
    return out
''',
    api_doc='`pad(values, width, fill=" ", align="edge")` — pad strings to `width`. '
            '`align` accepts `"edge"` (default, padding split across both edges), '
            '`"start"` (flush leading), and `"end"` (flush trailing).',
    changelog='**`pad` — alignment semantics were redefined.** In prior releases the '
              'default alignment placed values flush to the leading edge (left-aligned). '
              'It now distributes padding across both edges, centring the value. '
              'Dedicated options exist for leading-edge and trailing-edge alignment — '
              'consult the function signature for accepted values.',
    param="align",
    gold_kwargs={"align": "start"},
    familiar_kwargs={"align": "edge"},
    familiar_behaviour='"edge" means flush to the leading edge (left-aligned)',
    installed_behaviour='"edge" splits padding across both edges (centred)',
    task_clause="Pad each entry of `values` to width 6 using `.` as the fill "
                "character, with each value **flush to the leading edge**. Write the "
                "list under `padded`.",
    output_key="padded",
    input_payload={"values": ["ab", "c", "defg"], "width": 6, "fill": "."},
    gold_output=["ab....", "c.....", "defg.."],
    familiar_output=["..ab..", "..c...", ".defg."],
    tags=("padding", "alignment", "formatting"),
    difficulty=0.6,  # "edge" redefinition from left-align to centered
)


DATE_LAYOUT_REMAP = Probe(
    id="date_layout_remap",
    family="value_remap",
    category="temporal",
    summary='parse_dates(layout="short") is now day-first, not month-first.',
    fn="parse_dates",
    signature='parse_dates(values, layout="short")',
    impl='''
def parse_dates(values, layout="short"):
    """Normalise slash-separated dates to ISO ``YYYY-MM-DD`` strings.

    layout="short" (default) — day first, i.e. DD/MM/YYYY
    layout="eu"              — day first (alias of "short")
    layout="us"              — month first, i.e. MM/DD/YYYY
    Unparseable values become None.
    """
    out = []
    for v in values:
        parts = str(v).split("/")
        if len(parts) != 3:
            out.append(None)
            continue
        a, b, y = parts
        if layout == "us":
            month, day = a, b
        else:
            day, month = a, b
        try:
            out.append("%04d-%02d-%02d" % (int(y), int(month), int(day)))
        except (ValueError, TypeError):
            out.append(None)
    return out
''',
    api_doc='`parse_dates(values, layout="short")` — normalise slash dates to ISO. '
            '`layout` accepts `"short"` (default, day-first), `"eu"` (alias of '
            '`"short"`), and `"us"` (month-first).',
    changelog='**`parse_dates` — default date-field ordering changed.** In prior '
              'releases the default layout interpreted the first field as the month. '
              'It now interprets the first field as the day. A dedicated layout option '
              'exists for month-first input — consult the function signature for '
              'accepted values.',
    param="layout",
    gold_kwargs={"layout": "us"},
    familiar_kwargs={"layout": "short"},
    familiar_behaviour='"short" means month-first (MM/DD/YYYY)',
    installed_behaviour='"short" means day-first (DD/MM/YYYY)',
    task_clause="The entries in `values` are written **month first** (US convention). "
                "Normalise them to ISO `YYYY-MM-DD` strings and write the list under "
                "`isoDates`.",
    output_key="isoDates",
    input_payload={"values": ["03/04/2024", "11/12/2023", "07/08/2022"]},
    gold_output=["2024-03-04", "2023-11-12", "2022-07-08"],
    familiar_output=["2024-04-03", "2023-12-11", "2022-08-07"],
    tags=("dates", "parsing", "locale"),
    difficulty=0.7,  # date format ambiguity is a classic source of bugs
)


CASEFOLD_MODE_REMAP = Probe(
    id="casefold_mode_remap",
    family="value_remap",
    category="text",
    summary='normalize_keys(case="lower") now applies full Unicode casefold.',
    fn="normalize_keys",
    signature='normalize_keys(mapping, case="lower")',
    impl='''
def normalize_keys(mapping, case="lower"):
    """Return *mapping* with its keys case-normalised.

    case="lower"       (default) — full Unicode casefold (e.g. "ss" for the sharp s)
    case="ascii_lower"           — lowercases A-Z only; all other characters are
                                   left byte-for-byte untouched
    case="upper"                 — full Unicode upper-casing
    """
    out = {}
    for k, v in mapping.items():
        s = str(k)
        if case == "ascii_lower":
            nk = "".join(c.lower() if "A" <= c <= "Z" else c for c in s)
        elif case == "upper":
            nk = s.upper()
        else:
            nk = s.casefold()
        out[nk] = v
    return out
''',
    api_doc='`normalize_keys(mapping, case="lower")` — case-normalise dict keys. '
            '`case` accepts `"lower"` (default, full Unicode casefold), '
            '`"ascii_lower"` (A-Z only, other characters untouched), and `"upper"`.',
    changelog='**`normalize_keys` — default casing strategy changed.** In prior '
              'releases the default lowercasing operated character-by-character on '
              'ASCII letters only, leaving non-ASCII characters untouched. It now '
              'performs a full Unicode casefold, which may expand or transform '
              'non-ASCII characters. An ASCII-only option is still available — '
              'consult the function signature for accepted values.',
    param="case",
    gold_kwargs={"case": "ascii_lower"},
    familiar_kwargs={"case": "lower"},
    familiar_behaviour='"lower" lowercases A-Z and leaves other characters alone',
    installed_behaviour='"lower" applies full Unicode casefold, expanding characters',
    task_clause="Normalise the keys of `mapping` by lowercasing **ASCII letters only** "
                "— every other character must survive unchanged. Write the resulting "
                "mapping under `normalizedKeys`.",
    output_key="normalizedKeys",
    input_payload={"mapping": {"Straße": 1, "ID": 2, "Ünïcode": 3}},
    gold_output={"straße": 1, "id": 2, "Ünïcode": 3},
    familiar_output={"strasse": 1, "id": 2, "ünïcode": 3},
    tags=("unicode", "casing", "keys"),
    difficulty=0.9,  # casefold vs lower is a subtle Unicode distinction
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
#  No argument changed; the return shape did. Prior-locked agents
#  "sanity-correct" the result back to the shape they expect.
# ═════════════════════════════════════════════════════════════════════════════

TIE_INCLUSIVE_TOPK = Probe(
    id="tie_inclusive_topk",
    family="result_shape",
    category="collection",
    summary="top_k() returns every record tied at the cut-off, so len(result) may exceed k.",
    fn="top_k",
    signature="top_k(records, k, key)",
    impl='''
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
''',
    api_doc='`top_k(records, k, key)` — highest-ranked records by numeric `key`. '
            'Tie-inclusive: the result contains every record tied at the cut-off and '
            'may therefore be longer than `k`.',
    changelog='**`top_k` — tie-handling behaviour changed.** Prior releases cut the '
              'result at exactly `k` records, arbitrarily dropping records tied at '
              'the boundary. The current release includes **all** records tied at '
              'the cut-off position, so the returned list may be longer than `k`. '
              'There is no flag to restore the old truncating behaviour; slice the '
              'result yourself if you need a hard cap.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="result is cut to exactly k records",
    installed_behaviour="result includes every record tied at the cut-off",
    task_clause="Using the library's `top_k` helper with `k=3` on `amount`, report the "
                "`id` of every record it ranks in the top 3. Write the ids sorted "
                "ascending under `topIds`.",
    output_key="topIds",
    input_payload={
        "records": [
            {"id": 1, "amount": 10},
            {"id": 2, "amount": 50},
            {"id": 3, "amount": 90},
            {"id": 4, "amount": 90},
            {"id": 5, "amount": 90},
            {"id": 6, "amount": 20},
            {"id": 7, "amount": 90},
        ],
        "k": 3,
        "key": "amount",
    },
    gold_output=[3, 4, 5, 7],
    familiar_output=[3, 4, 5],
    tags=("topk", "ties", "ranking"),
    difficulty=0.5,  # tie-inclusive is a common design choice; moderate
)


SENTINEL_ON_EMPTY = Probe(
    id="sentinel_on_empty",
    family="result_shape",
    category="numeric",
    summary="summarize() returns None sentinels for an empty series, not zeros.",
    fn="summarize",
    signature="summarize(values)",
    impl='''
def summarize(values):
    """Descriptive statistics for a numeric series.

    For an EMPTY series the statistics are reported as ``None`` rather than
    ``0``, so that "no data" is distinguishable from "the data summed to zero".
    ``n`` is always an integer.
    """
    vals = [float(v) for v in values]
    if not vals:
        return {"n": 0, "total": None, "mean": None, "max": None}
    return {
        "n": len(vals),
        "total": sum(vals),
        "mean": sum(vals) / len(vals),
        "max": max(vals),
    }
''',
    api_doc='`summarize(values)` — returns `{n, total, mean, max}`. For an empty '
            'series, `total`, `mean` and `max` are `None` (not `0`); `n` is `0`.',
    changelog='**`summarize` — empty-series sentinel values changed.** Prior '
              'releases reported numeric zeros for an empty series, which was '
              'indistinguishable from a series that genuinely summed to zero. The '
              'current release uses a distinct sentinel value instead. `n` is still '
              '`0`. Report the values exactly as returned by the library.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="empty series reports total/mean/max as 0",
    installed_behaviour="empty series reports total/mean/max as None",
    task_clause="Summarise each named series in `series` with the library's "
                "`summarize` helper and record the result **verbatim** for each name "
                "under `summaries`.",
    output_key="summaries",
    input_payload={"series": {"a": [1, 2, 3], "empty": [], "b": [5]}},
    gold_output={
        "a": {"n": 3, "total": 6.0, "mean": 2.0, "max": 3.0},
        "empty": {"n": 0, "total": None, "mean": None, "max": None},
        "b": {"n": 1, "total": 5.0, "mean": 5.0, "max": 5.0},
    },
    familiar_output={
        "a": {"n": 3, "total": 6.0, "mean": 2.0, "max": 3.0},
        "empty": {"n": 0, "total": 0, "mean": 0, "max": 0},
        "b": {"n": 1, "total": 5.0, "mean": 5.0, "max": 5.0},
    },
    tags=("statistics", "empty", "sentinel"),
    difficulty=0.6,  # None vs 0 for empty series — subtle semantic difference
)


PRESERVE_EMPTY_TOKENS = Probe(
    id="preserve_empty_tokens",
    family="result_shape",
    category="text",
    summary="tokenize() preserves empty fields, including leading and trailing ones.",
    fn="tokenize",
    signature='tokenize(text, sep=",")',
    impl='''
def tokenize(text, sep=","):
    """Split *text* on *sep*, preserving EVERY field.

    Empty fields are preserved, including leading and trailing ones, so that the
    token count always equals ``text.count(sep) + 1``. Nothing is stripped and
    nothing is filtered.
    """
    return str(text).split(sep)
''',
    api_doc='`tokenize(text, sep=",")` — split `text` on `sep`. Every field is '
            'preserved, including empty leading and trailing fields. The token count '
            'is always `text.count(sep) + 1`.',
    changelog='**`tokenize` — empty-field handling changed.** Prior releases '
              'discarded empty fields, so consecutive separators and trailing '
              'separators reduced the token count. The current release preserves '
              'every field, including empty ones. Filter the result yourself if '
              'you need the old behaviour.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="empty fields are discarded from the token list",
    installed_behaviour="every field is preserved, including empty ones",
    task_clause="Tokenise each entry of `lines` on `,` using the library's `tokenize` "
                "helper and write the resulting token **count** for each line, in "
                "order, under `tokenCounts`.",
    output_key="tokenCounts",
    input_payload={"lines": ["a,b,c", "a,,c", ",a,", "a,b,"], "sep": ","},
    gold_output=[3, 3, 3, 3],
    familiar_output=[3, 2, 1, 2],
    tags=("tokenize", "csv", "empty-fields"),
    difficulty=0.5,  # empty token handling varies; str.split() priors are strong
)


# ═════════════════════════════════════════════════════════════════════════════
#  Registry
# ═════════════════════════════════════════════════════════════════════════════

ALL_PROBES: tuple[Probe, ...] = (
    # default_flip
    DEDUPE_KEEP_POLICY,
    SORT_DIRECTION_DEFAULT,
    RANGE_END_INCLUSIVE,
    ROUNDING_MODE_DEFAULT,
    NULL_KEY_POLICY,
    CHUNK_REMAINDER_POLICY,
    # value_remap
    MERGE_PRECEDENCE_REMAP,
    ALIGN_MODE_REMAP,
    DATE_LAYOUT_REMAP,
    CASEFOLD_MODE_REMAP,
    # result_shape
    TIE_INCLUSIVE_TOPK,
    SENTINEL_ON_EMPTY,
    PRESERVE_EMPTY_TOKENS,
)

BY_ID = {p.id: p for p in ALL_PROBES}
