"""L2 coupled probes — cross-function dependency chains.

L2 probes test whether an agent can handle *multiple related* changes
simultaneously. Each L2 probe declares ``dependencies`` — a tuple of L1 probe
ids that must co-occur. The agent must read multiple CHANGELOG entries and
reason about their interaction.

Design principle: an agent that fixes one change but not the other produces an
inconsistent result. The verifier checks the *composition*, not the parts.
"""
from __future__ import annotations

from ..probes.base import Probe

# ═════════════════════════════════════════════════════════════════════════════
#  Coding domain — L2
# ═════════════════════════════════════════════════════════════════════════════

DEDUPE_THEN_RANK = Probe(
    id="l2_dedupe_then_rank",
    family="default_flip",
    category="collection",
    summary="De-duplicate then rank: both dedupe's keep policy and rank's sort "
            "direction changed. Getting only one right produces wrong results.",
    fn="dedupe_and_rank",
    signature='dedupe_and_rank(items, key, sort_key, keep="last", order="desc")',
    impl='''
def dedupe_and_rank(items, key, sort_key, keep="last", order="desc"):
    """De-duplicate *items* by *key*, then rank the survivors by *sort_key*.

    keep="last"  (default) — later occurrences overwrite earlier ones
    keep="first"           — the earliest occurrence of each key is retained

    order="desc" (default) — highest first
    order="asc"            — lowest first
    """
    seen = {}
    insertion_order = []
    for it in items:
        k = it.get(key)
        if k not in seen:
            insertion_order.append(k)
            seen[k] = it
        elif keep != "first":
            seen[k] = it
    survivors = [seen[k] for k in insertion_order]
    return sorted(survivors, key=lambda r: r[sort_key], reverse=(order != "asc"))
''',
    api_doc='`dedupe_and_rank(items, key, sort_key, keep="last", order="desc")` — '
            'de-duplicate by `key`, then sort survivors by `sort_key`. '
            '`keep` selects which record survives (`"last"` default or `"first"`). '
            '`order` controls sort direction (`"desc"` default or `"asc"`).',
    changelog='**`dedupe_and_rank` — TWO defaults changed.**\n'
              '1. `keep` changed from `"first"` to `"last"` (see `dedupe` CHANGELOG).\n'
              '2. `order` changed from `"asc"` to `"desc"` (see `rank` CHANGELOG).\n'
              'Both changes apply simultaneously. Pass `keep="first"` and `order="asc"` '
              'to restore the previous compound behaviour.',
    param="keep",
    gold_kwargs={"keep": "first", "order": "asc"},
    familiar_kwargs={},
    familiar_behaviour='keep="first" + order="asc" — earliest record, lowest first',
    installed_behaviour='keep="last" + order="desc" — latest record, highest first',
    task_clause="De-duplicate `items` by `sku`, retaining the **earliest** occurrence, "
                "then sort by `price` from **lowest to highest**. Write the list of "
                "`sku` values in that order under `pipeline`.",
    output_key="pipeline",
    input_payload={
        "items": [
            {"sku": "A", "price": 30},
            {"sku": "B", "price": 10},
            {"sku": "A", "price": 50},
            {"sku": "C", "price": 20},
            {"sku": "B", "price": 40},
        ],
        "key": "sku",
        "sort_key": "price",
    },
    gold_output=["B", "C", "A"],         # first-wins: A=30, B=10, C=20; asc
    familiar_output=["A", "B", "C"],      # last-wins:  A=50, B=40, C=20; desc
    tags=("pipeline", "coupled", "l2"),
    domain="coding",
    level=2,
    dependencies=("dedupe_keep_policy", "sort_direction_default"),
)


ROUND_THEN_SUMMARIZE = Probe(
    id="l2_round_then_summarize",
    family="result_shape",
    category="numeric",
    summary="Round values then summarize: rounding mode changed AND empty-series "
            "sentinel changed. Both interact on boundary values.",
    fn="round_and_summarize",
    signature="round_and_summarize(values, places=2)",
    impl='''
def round_and_summarize(values, places=2):
    """Round every value using banker's rounding, then compute summary stats.

    Uses half-even rounding (ties go to the nearest even digit).
    For an empty series, statistics are ``None`` rather than ``0``.
    """
    from decimal import Decimal, ROUND_HALF_EVEN
    q = Decimal(1).scaleb(-places)
    rounded = []
    for v in values:
        rounded.append(float(Decimal(str(v)).quantize(q, rounding=ROUND_HALF_EVEN)))
    if not rounded:
        return {"rounded": rounded, "stats": {"n": 0, "total": None, "mean": None}}
    return {
        "rounded": rounded,
        "stats": {
            "n": len(rounded),
            "total": round(sum(rounded), places),
            "mean": round(sum(rounded) / len(rounded), places),
        },
    }
''',
    api_doc='`round_and_summarize(values, places=2)` — rounds each value using '
            "banker's rounding, then returns `{rounded, stats}`. Stats for an "
            'empty series use `None` sentinels.',
    changelog="**`round_and_summarize` — TWO changes from v1.**\n"
              "1. Rounding changed from half-up to half-even (banker's rounding).\n"
              "2. Empty-series stats now return `None` instead of `0`.\n"
              "Both changes affect the output simultaneously.",
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="half-up rounding + zeros for empty stats",
    installed_behaviour="half-even rounding + None sentinels for empty stats",
    task_clause="Round each value in `values` to 2 decimal places using the library's "
                "`round_and_summarize`, and report the complete result verbatim under "
                "`roundedStats`.",
    output_key="roundedStats",
    input_payload={"values": [2.345, 2.355, 0.125], "places": 2},
    gold_output={
        "rounded": [2.34, 2.36, 0.12],
        "stats": {"n": 3, "total": 4.82, "mean": 1.61},
    },
    familiar_output={
        "rounded": [2.35, 2.36, 0.13],
        "stats": {"n": 3, "total": 4.84, "mean": 1.61},
    },
    tags=("pipeline", "coupled", "l2"),
    domain="coding",
    level=2,
    dependencies=("rounding_mode_default", "sentinel_on_empty"),
)


# ═════════════════════════════════════════════════════════════════════════════
#  SQL domain — L2
# ═════════════════════════════════════════════════════════════════════════════

GROUP_THEN_ORDER_NULLS = Probe(
    id="l2_sql_group_then_order_nulls",
    family="default_flip",
    category="aggregation",
    summary="Group including nulls then order with nulls-last: both null handling "
            "policies changed together.",
    fn="sql_group_and_order",
    signature='sql_group_and_order(rows, group_col, agg_col, include_null_keys=True, nulls_position="last")',
    impl='''
def sql_group_and_order(rows, group_col, agg_col, include_null_keys=True, nulls_position="last"):
    """Group rows by *group_col*, sum *agg_col*, then order by the sum.

    include_null_keys=True  (default) — rows with NULL group key are included
    include_null_keys=False           — rows with NULL group key are dropped

    nulls_position="last"   (default) — NULL groups appear at the end
    nulls_position="first"            — NULL groups appear at the start
    """
    groups = {}
    order = []
    for r in rows:
        k = r.get(group_col)
        if k is None and not include_null_keys:
            continue
        label = k if k is not None else "__NULL__"
        if label not in groups:
            order.append(label)
            groups[label] = 0
        groups[label] += r.get(agg_col, 0)
    # sort by sum descending, then handle null positioning
    non_null = [(k, v) for k, v in groups.items() if k != "__NULL__"]
    null_entry = [("__NULL__", groups["__NULL__"])] if "__NULL__" in groups else []
    non_null.sort(key=lambda kv: kv[1], reverse=True)
    if nulls_position == "first":
        result = null_entry + non_null
    else:
        result = non_null + null_entry
    return [{"group": (None if k == "__NULL__" else k), "total": v} for k, v in result]
''',
    api_doc='`sql_group_and_order(rows, group_col, agg_col, include_null_keys=True, nulls_position="last")` '
            '— GROUP BY with SUM, then ORDER BY the aggregate. NULL key handling and '
            'NULL positioning are both configurable.',
    changelog='**`sql_group_and_order` — TWO null-handling defaults changed.**\n'
              '1. `include_null_keys` changed from `False` to `True`.\n'
              '2. `nulls_position` changed from `"first"` to `"last"`.\n'
              'Both affect queries with NULL group keys simultaneously.',
    param="include_null_keys",
    gold_kwargs={"include_null_keys": False},
    familiar_kwargs={},
    familiar_behaviour="exclude nulls + nulls first",
    installed_behaviour="include nulls + nulls last",
    task_clause="Group `rows` by `dept`, summing `salary`, **excluding** rows with no "
                "department. Order by total salary descending. Write the result under "
                "`groupedOrdered`.",
    output_key="groupedOrdered",
    input_payload={
        "rows": [
            {"dept": "eng", "salary": 100},
            {"dept": "sales", "salary": 80},
            {"dept": None, "salary": 50},
            {"dept": "eng", "salary": 120},
            {"dept": "sales", "salary": 90},
            {"dept": None, "salary": 60},
        ],
        "group_col": "dept",
        "agg_col": "salary",
    },
    gold_output=[
        {"group": "eng", "total": 220},
        {"group": "sales", "total": 170},
    ],
    familiar_output=[
        {"group": None, "total": 110},
        {"group": "eng", "total": 220},
        {"group": "sales", "total": 170},
    ],
    tags=("pipeline", "coupled", "l2", "sql"),
    domain="sql",
    level=2,
    dependencies=("null_group_policy", "order_nulls_position"),
)


# ═════════════════════════════════════════════════════════════════════════════
#  Finance domain — L2
# ═════════════════════════════════════════════════════════════════════════════

SETTLE_AND_FORMAT = Probe(
    id="l2_fin_settle_and_format",
    family="value_remap",
    category="settlement",
    summary="Settle then format: settlement cycle changed to T+1 AND currency "
            "display changed to suffix. Both affect the final trade confirmation.",
    fn="fin_trade_confirm",
    signature='fin_trade_confirm(trade_date, amount, currency, cycle="T+1", style="standard")',
    impl='''
def fin_trade_confirm(trade_date, amount, currency, cycle="T+1", style="standard"):
    """Generate a trade confirmation with settlement date and formatted amount.

    cycle="T+1" (default) — settles next business day
    cycle="T+2"           — settles two business days later

    style="standard" (default) — currency symbol after amount (suffix): "100.00 USD"
    style="prefix"             — currency symbol before amount: "USD 100.00"
    """
    from datetime import datetime, timedelta
    dt = datetime.strptime(trade_date, "%Y-%m-%d")
    days = int(cycle.split("+")[1])
    settle = dt
    added = 0
    while added < days:
        settle += timedelta(days=1)
        if settle.weekday() < 5:
            added += 1
    settle_str = settle.strftime("%Y-%m-%d")
    formatted = f"{amount:.2f}"
    if style == "prefix":
        display = f"{currency} {formatted}"
    else:
        display = f"{formatted} {currency}"
    return {"settlement_date": settle_str, "display_amount": display}
''',
    api_doc='`fin_trade_confirm(trade_date, amount, currency, cycle="T+1", style="standard")` '
            '— generates a trade confirmation. `cycle` sets settlement timing. '
            '`style="standard"` puts currency after amount; `style="prefix"` puts it before.',
    changelog='**`fin_trade_confirm` — TWO changes.**\n'
              '1. `cycle` default changed from `"T+2"` to `"T+1"`.\n'
              '2. `style="standard"` was redefined to mean currency-after (suffix), '
              'not currency-before (prefix). Use `style="prefix"` for the old behaviour.',
    param="style",
    gold_kwargs={"cycle": "T+2", "style": "prefix"},
    familiar_kwargs={"style": "standard"},
    familiar_behaviour='T+2 settlement + "standard" means prefix (USD 100.00)',
    installed_behaviour='T+1 settlement + "standard" means suffix (100.00 USD)',
    task_clause="Generate a trade confirmation for `trade_date` with `amount` in "
                "`currency`, settling in **two business days** with the currency "
                "symbol **before** the amount. Write the result under `confirmation`.",
    output_key="confirmation",
    input_payload={
        "trade_date": "2026-07-24",
        "amount": 50000.0,
        "currency": "USD",
    },
    gold_output={
        "settlement_date": "2026-07-28",
        "display_amount": "USD 50000.00",
    },
    familiar_output={
        "settlement_date": "2026-07-27",
        "display_amount": "50000.00 USD",
    },
    tags=("pipeline", "coupled", "l2", "finance"),
    domain="finance",
    level=2,
    dependencies=("settlement_cycle", "currency_display"),
)


# ═════════════════════════════════════════════════════════════════════════════
#  Linux domain — L2
# ═════════════════════════════════════════════════════════════════════════════

GREP_THEN_SORT = Probe(
    id="l2_linux_grep_then_sort",
    family="default_flip",
    category="search",
    summary="Grep excluding hidden dirs then sort with new locale mode: both "
            "defaults changed, affecting a common shell pipeline.",
    fn="cli_grep_and_sort",
    signature='cli_grep_and_sort(files, pattern, include_hidden=False, sort_mode="natural")',
    impl='''
def cli_grep_and_sort(files, pattern, include_hidden=False, sort_mode="natural"):
    """Search files for *pattern*, then sort matching filenames.

    include_hidden=False (default) — skip files/dirs starting with '.'
    include_hidden=True            — include hidden files

    sort_mode="natural" (default)  — locale-aware natural sort (case-insensitive,
                                     numbers sorted by value not lexically)
    sort_mode="byte"               — raw byte-order (ASCII) sort
    """
    import re as _re
    matches = []
    for path, content in files.items():
        parts = path.replace("\\\\", "/").split("/")
        if not include_hidden and any(p.startswith(".") for p in parts if p):
            continue
        if _re.search(pattern, content):
            matches.append(path)
    if sort_mode == "byte":
        matches.sort()
    else:
        import locale as _locale
        matches.sort(key=lambda s: [
            int(c) if c.isdigit() else c.lower()
            for c in _re.split(r'(\\d+)', s)
        ])
    return matches
''',
    api_doc='`cli_grep_and_sort(files, pattern, include_hidden=False, sort_mode="natural")` '
            '— grep for `pattern` across `files`, then sort matching paths. '
            'Hidden files (starting with `.`) are excluded by default. '
            'Sort uses locale-aware natural ordering by default.',
    changelog='**`cli_grep_and_sort` — TWO defaults changed.**\n'
              '1. `include_hidden` changed from `True` to `False`.\n'
              '2. `sort_mode` changed from `"byte"` to `"natural"`.\n'
              'Both affect the output of `grep | sort` pipelines.',
    param="include_hidden",
    gold_kwargs={"include_hidden": True, "sort_mode": "byte"},
    familiar_kwargs={},
    familiar_behaviour="include hidden + byte sort",
    installed_behaviour="exclude hidden + natural sort",
    task_clause="Search all `files` (including hidden ones) for the pattern `TODO`, "
                "then sort matching paths in **byte order** (ASCII). Write the list "
                "under `grepResults`.",
    output_key="grepResults",
    input_payload={
        "files": {
            "src/main.py": "# TODO: refactor",
            ".config/settings.yaml": "# TODO: update defaults",
            "src/utils.py": "def helper(): pass",
            "README.md": "# TODO: write docs",
            ".hidden/notes.txt": "nothing here",
        },
        "pattern": "TODO",
    },
    gold_output=[".config/settings.yaml", "README.md", "src/main.py"],
    familiar_output=["README.md", "src/main.py"],
    tags=("pipeline", "coupled", "l2", "linux"),
    domain="linux",
    level=2,
    dependencies=("grep_hidden_dirs", "sort_locale_mode"),
)


# ═════════════════════════════════════════════════════════════════════════════
#  Registry
# ═════════════════════════════════════════════════════════════════════════════

ALL_L2_PROBES: tuple[Probe, ...] = (
    DEDUPE_THEN_RANK,
    ROUND_THEN_SUMMARIZE,
    GROUP_THEN_ORDER_NULLS,
    SETTLE_AND_FORMAT,
    GREP_THEN_SORT,
)
