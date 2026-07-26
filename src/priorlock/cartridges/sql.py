"""SQL domain cartridge — prior override on a synthetic SQL execution engine.

Five probes across the three PriorLock families, exercising the parts of SQL
semantics that LLMs have the strongest memorized priors about: NULL handling
in GROUP BY, NULL handling in JOIN, NULLS FIRST/LAST ordering, case-sensitivity
of DISTINCT, and the NULL-vs-empty-string distinction in COALESCE.
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

NULL_GROUP_POLICY = Probe(
    id="null_group_policy",
    family="default_flip",
    category="aggregation",
    summary="sql_group() now includes NULL keys as their own group by default.",
    fn="sql_group",
    signature="sql_group(rows, key, include_null_keys=True)",
    impl='''
def sql_group(rows, key, include_null_keys=True):
    """Group *rows* by *key*, returning one summary record per distinct value.

    include_null_keys=True  (default) — rows whose key is NULL form their own
                                         group (reported with key=None)
    include_null_keys=False           — rows whose key is NULL are dropped
                                         from the grouping entirely
    """
    order = []
    counts = {}
    for r in rows:
        k = r.get(key)
        if k is None and not include_null_keys:
            continue
        if k not in counts:
            counts[k] = 0
            order.append(k)
        counts[k] += 1
    return [{"key": k, "count": counts[k]} for k in order]
''',
    api_doc='`sql_group(rows, key, include_null_keys=True)` — group `rows` by '
            '`key`, returning `[{"key": ..., "count": ...}]` in first-seen '
            'order. `include_null_keys` controls whether rows with a NULL key '
            'form their own group (`True`, default) or are dropped (`False`).',
    changelog='**`sql_group` — default `include_null_keys` changed from `False` '
              'to `True`.** Prior releases silently dropped rows whose group key '
              'was NULL. The current release includes them as their own group '
              '(`key: null` in the output). Pass `include_null_keys=False` to '
              'restore the previous behaviour of excluding NULL-keyed rows.',
    param="include_null_keys",
    gold_kwargs={"include_null_keys": False},
    familiar_kwargs={},
    familiar_behaviour="include_null_keys defaults to False — NULL-keyed rows are dropped",
    installed_behaviour="include_null_keys defaults to True — NULL-keyed rows form their own group",
    task_clause="Group `rows` by `region`, **excluding** rows whose `region` is "
                "NULL from the grouping entirely. Write the list of "
                "`{key, count}` group summaries, in first-seen order, under `groups`.",
    output_key="groups",
    input_payload={
        "rows": [
            {"region": "west", "amount": 10},
            {"region": "east", "amount": 20},
            {"region": None, "amount": 5},
            {"region": "west", "amount": 7},
            {"region": None, "amount": 3},
        ],
        "key": "region",
    },
    gold_output=[{"key": "west", "count": 2}, {"key": "east", "count": 1}],
    familiar_output=[
        {"key": "west", "count": 2},
        {"key": "east", "count": 1},
        {"key": None, "count": 2},
    ],
    tags=("group-by", "null", "aggregation"),
    domain="sql",
)


JOIN_NULL_MATCH = Probe(
    id="join_null_match",
    family="default_flip",
    category="joins",
    summary="sql_join() now matches NULL join keys against each other by default.",
    fn="sql_join",
    signature="sql_join(left, right, on, null_matches=True)",
    impl='''
def sql_join(left, right, on, null_matches=True):
    """Inner-join *left* and *right* on the field named by *on*.

    null_matches=True  (default) — a NULL key on both sides counts as a match
    null_matches=False            — NULL never matches NULL (three-valued SQL logic)
    """
    pairs = []
    for l in left:
        lv = l.get(on)
        for r in right:
            rv = r.get(on)
            if lv is None or rv is None:
                if null_matches and lv is None and rv is None:
                    pairs.append({"left_id": l["id"], "right_id": r["id"]})
                continue
            if lv == rv:
                pairs.append({"left_id": l["id"], "right_id": r["id"]})
    return pairs
''',
    api_doc='`sql_join(left, right, on, null_matches=True)` — inner join `left` '
            'and `right` on the field `on`, returning `[{"left_id", "right_id"}]` '
            'pairs. `null_matches` controls whether a NULL key on both sides '
            'counts as a match: `True` (default) or `False`.',
    changelog='**`sql_join` — default `null_matches` changed from `False` to '
              '`True`.** Prior releases followed standard three-valued SQL '
              'logic, where `NULL = NULL` is never true and NULL keys never '
              'match. The current release treats two NULL keys as equal by '
              'default, producing extra matched pairs. Pass '
              '`null_matches=False` to restore standard SQL NULL semantics.',
    param="null_matches",
    gold_kwargs={"null_matches": False},
    familiar_kwargs={},
    familiar_behaviour="null_matches defaults to False — NULL keys never match, per standard SQL",
    installed_behaviour="null_matches defaults to True — NULL keys match each other",
    task_clause="Join `left` and `right` on `code` using **standard SQL "
                "semantics**, where NULL never matches NULL. Write the list of "
                "`{left_id, right_id}` matched pairs, in left-then-right "
                "iteration order, under `matches`.",
    output_key="matches",
    input_payload={
        "left": [
            {"id": 1, "code": "A"},
            {"id": 2, "code": None},
            {"id": 3, "code": "B"},
        ],
        "right": [
            {"id": 10, "code": "A"},
            {"id": 11, "code": None},
            {"id": 12, "code": "C"},
        ],
        "on": "code",
    },
    gold_output=[{"left_id": 1, "right_id": 10}],
    familiar_output=[{"left_id": 1, "right_id": 10}, {"left_id": 2, "right_id": 11}],
    tags=("join", "null", "three-valued-logic"),
    domain="sql",
)


DISTINCT_CASE_MODE = Probe(
    id="distinct_case_mode",
    family="default_flip",
    category="filtering",
    summary="sql_distinct() now folds case by default instead of comparing exactly.",
    fn="sql_distinct",
    signature="sql_distinct(values, case_sensitive=False)",
    impl='''
def sql_distinct(values, case_sensitive=False):
    """Return the distinct values in *values*, preserving first-seen order.

    case_sensitive=False (default) — comparison folds case; "Foo" and "foo"
                                      are the same value (first-seen casing kept)
    case_sensitive=True             — comparison is exact; casing distinguishes values
    """
    seen = set()
    out = []
    for v in values:
        cmp_key = v.lower() if (not case_sensitive and isinstance(v, str)) else v
        if cmp_key not in seen:
            seen.add(cmp_key)
            out.append(v)
    return out
''',
    api_doc='`sql_distinct(values, case_sensitive=False)` — distinct values '
            'from `values`, first-seen order preserved. `case_sensitive` is '
            '`False` (default, case-folded comparison) or `True` (exact comparison).',
    changelog='**`sql_distinct` — default `case_sensitive` changed from `True` '
              'to `False`.** Prior releases compared strings exactly, so '
              '`"Foo"` and `"foo"` were distinct values. The current release '
              'folds case by default, merging them into a single value (the '
              'first-seen casing is kept). Pass `case_sensitive=True` to '
              'restore exact comparison.',
    param="case_sensitive",
    gold_kwargs={"case_sensitive": True},
    familiar_kwargs={},
    familiar_behaviour="case_sensitive defaults to True — differently-cased strings are distinct",
    installed_behaviour="case_sensitive defaults to False — differently-cased strings are merged",
    task_clause="Return the distinct values from `values` using **case-sensitive** "
                "comparison, so strings differing only in case are kept as "
                "separate values. Preserve first-seen order. Write the list "
                "under `distinct`.",
    output_key="distinct",
    input_payload={"values": ["Apple", "apple", "Banana", "BANANA", "Cherry"]},
    gold_output=["Apple", "apple", "Banana", "BANANA", "Cherry"],
    familiar_output=["Apple", "Banana", "Cherry"],
    tags=("distinct", "case", "filtering"),
    domain="sql",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

ORDER_NULLS_POSITION = Probe(
    id="order_nulls_position",
    family="value_remap",
    category="ordering",
    summary='sql_order()\'s nulls="edge" now means NULLS LAST instead of NULLS FIRST.',
    fn="sql_order",
    signature='sql_order(rows, key, nulls="edge")',
    impl='''
def sql_order(rows, key, nulls="edge"):
    """Order *rows* by *key* ascending.

    nulls="first" — rows with a NULL key sort before all non-NULL rows
    nulls="last"  — rows with a NULL key sort after all non-NULL rows
    nulls="edge"  (default) — alias for "last": NULL keys sort to the end
    """
    non_null = sorted((r for r in rows if r.get(key) is not None), key=lambda r: r[key])
    null_rows = [r for r in rows if r.get(key) is None]
    if nulls == "first":
        return null_rows + non_null
    return non_null + null_rows
''',
    api_doc='`sql_order(rows, key, nulls="edge")` — ascending sort of `rows` by '
            '`key`. `nulls` is `"first"`, `"last"`, or `"edge"` (default, '
            'currently an alias for `"last"`).',
    changelog='**`sql_order` — the `nulls="edge"` value now means NULLS LAST, '
              'not NULLS FIRST.** Prior releases treated `"edge"` as shorthand '
              'for placing NULL keys at the *start* of the result. The current '
              'release places them at the *end* instead — the same position as '
              'explicit `nulls="last"`. `nulls="first"` and `nulls="last"` are '
              'unchanged and still behave literally; use `nulls="first"` if '
              'you need NULLs at the start.',
    param="nulls",
    gold_kwargs={"nulls": "first"},
    familiar_kwargs={"nulls": "edge"},
    familiar_behaviour='nulls="edge" places NULL keys first',
    installed_behaviour='nulls="edge" places NULL keys last',
    task_clause="Order `rows` by `amount` ascending, placing rows with a NULL "
                "`amount` **first**. Write the list of `id`s in that order "
                "under `order`.",
    output_key="order",
    input_payload={
        "rows": [
            {"id": 1, "amount": 30},
            {"id": 2, "amount": None},
            {"id": 3, "amount": 10},
            {"id": 4, "amount": None},
            {"id": 5, "amount": 20},
        ],
        "key": "amount",
    },
    gold_output=[2, 4, 3, 5, 1],
    familiar_output=[3, 5, 1, 2, 4],
    tags=("order-by", "null", "nulls-first"),
    domain="sql",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

COALESCE_EMPTY_STRING = Probe(
    id="coalesce_empty_string",
    family="result_shape",
    category="types",
    summary='sql_coalesce() now treats "" as a real value instead of NULL.',
    fn="sql_coalesce",
    signature="sql_coalesce(values)",
    impl='''
def sql_coalesce(values):
    """Return the first value in *values* that is not NULL.

    Empty string "" counts as a value, not NULL — it is returned immediately
    if it is the first non-NULL entry. Only Python ``None`` is treated as NULL.
    """
    for v in values:
        if v is not None:
            return v
    return None
''',
    api_doc='`sql_coalesce(values)` — return the first value in `values` that '
            'is not NULL. Empty string `""` is treated as a real (non-NULL) '
            'value, not as NULL.',
    changelog='**`sql_coalesce` now treats `""` as a real value, not NULL.** '
              'Prior releases skipped both `None` and `""` when scanning for '
              'the first non-NULL value, matching engines where empty string '
              'and NULL are conflated. The current release only skips `None`; '
              'an empty string is returned as-is if it is the first entry that '
              'is not `None`.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour='"" is skipped like NULL when scanning for the first value',
    installed_behaviour='"" is returned as the first value if it is not None',
    task_clause="Using the library's `sql_coalesce` helper, find the first "
                "value in `values` that is not NULL (here NULL means the "
                "Python value is missing, not that it is an empty string). "
                "Write the result under `first`.",
    output_key="first",
    input_payload={"values": [None, "", "fallback"]},
    gold_output="",
    familiar_output="fallback",
    tags=("coalesce", "null", "empty-string"),
    domain="sql",
)


SQL_PROBES = (
    NULL_GROUP_POLICY,
    JOIN_NULL_MATCH,
    DISTINCT_CASE_MODE,
    ORDER_NULLS_POSITION,
    COALESCE_EMPTY_STRING,
)

CATEGORIES = ("aggregation", "joins", "ordering", "filtering", "types")

LEXICON = {
    "aggregation": {
        "group": 2.5, "aggregate": 2.5, "sum": 1.5, "count": 2.0, "having": 2.5,
        "rollup": 2.0, "pivot": 1.5, "bucket": 1.5, "partition": 1.5,
        "window": 1.5, "average": 1.5, "total": 1.0,
    },
    "joins": {
        "join": 2.5, "inner": 2.0, "outer": 2.0, "left": 1.0, "right": 1.0,
        "merge": 1.5, "relation": 1.5, "foreign": 1.5, "key": 1.0,
        "match": 1.5, "on": 0.5, "reference": 1.0,
    },
    "ordering": {
        "order": 2.5, "sort": 2.0, "rank": 1.5, "nulls": 2.5, "asc": 1.5,
        "desc": 1.5, "sequence": 1.0, "priority": 1.0,
    },
    "filtering": {
        "distinct": 2.5, "filter": 2.0, "where": 2.0, "unique": 2.0,
        "dedupe": 1.5, "case": 1.5, "predicate": 1.5, "condition": 1.0,
    },
    "types": {
        "null": 2.5, "coalesce": 2.5, "type": 1.5, "cast": 2.0, "empty": 1.5,
        "sentinel": 1.5, "default": 1.0, "schema": 1.0,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="sql",
    display_name="SQL Engine",
    description="Prior override on a synthetic SQL execution engine — GROUP BY, "
                "JOIN, ORDER BY, DISTINCT, and COALESCE NULL semantics.",
    probes=SQL_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    max_level=1,
)

register(CARTRIDGE)
