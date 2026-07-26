"""L3 workflow probes — multi-step pipelines with chained dependencies.

L3 probes test whether an agent can handle a **pipeline** of 3+ changed functions
where each step's output feeds into the next. The agent must read scattered
CHANGELOG entries and understand how changes *compose* across the pipeline.

Key distinction from L2:
- **L2 (coupled)**: 2 functions change together, but the task can test them
  independently or as a pair. The composition is simple.
- **L3 (workflow)**: 3+ functions form a *pipeline*. The agent must get **every**
  step right for the pipeline output to be correct. A single missed change cascades
  through all downstream steps.

These are the hardest single-turn probes in PriorLock.
"""
from __future__ import annotations

from ..probes.base import Probe


# ═════════════════════════════════════════════════════════════════════════════
#  Coding domain — L3: parse → transform → summarize pipeline
# ═════════════════════════════════════════════════════════════════════════════

ETL_PIPELINE = Probe(
    id="l3_etl_parse_transform_summarize",
    family="default_flip",
    category="collection",
    summary="Parse → transform → summarize pipeline: date parsing format changed, "
            "dedup keep policy changed, AND empty-group sentinel changed. All three "
            "interact in a single ETL pipeline.",
    fn="etl_pipeline",
    signature='etl_pipeline(raw_records, date_col, group_col, value_col, date_order="day_first", dedup_keep="last", empty_sentinel=None)',
    impl='''
def etl_pipeline(raw_records, date_col, group_col, value_col,
                 date_order="day_first", dedup_keep="last", empty_sentinel=None):
    """Three-stage ETL: parse dates, deduplicate, then group-summarize.

    Stage 1 — parse: dates in ``raw_records`` are parsed as ISO-8601.
    ``date_order="day_first"`` (default) — ambiguous dates like "01/02/2026"
    are interpreted as day/month (Feb 1). ``"month_first"`` interprets as
    month/day (Jan 2).

    Stage 2 — deduplicate: when duplicate keys are found, keep policy applies.
    ``dedup_keep="last"`` (default) — most-recent-wins.
    ``dedup_keep="first"`` — first-seen-wins.

    Stage 3 — summarize: group by ``group_col``, sum ``value_col``. Groups with
    no matching records return ``{"total": empty_sentinel}``.
    ``empty_sentinel=None`` (default). ``empty_sentinel=0`` for numeric zero.
    """
    from datetime import datetime

    # Stage 1: parse dates
    parsed = []
    for r in raw_records:
        rec = dict(r)
        raw = str(rec[date_col])
        if date_order == "day_first":
            fmts = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
        else:
            fmts = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]
        for fmt in fmts:
            try:
                rec[date_col] = datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
        parsed.append(rec)

    # Stage 2: deduplicate
    seen = {}
    order = []
    for rec in parsed:
        k = rec.get(date_col, "") + ":" + str(rec.get(group_col, ""))
        if k not in seen:
            order.append(k)
            seen[k] = rec
        elif dedup_keep == "last":
            seen[k] = rec
    deduped = [seen[k] for k in order]

    # Stage 3: group-summarize
    groups = {}
    group_order = []
    for rec in deduped:
        g = rec.get(group_col)
        if g not in groups:
            group_order.append(g)
            groups[g] = 0.0
        groups[g] += rec.get(value_col, 0)

    return [{"group": g, "total": round(groups[g], 2) if groups[g] else empty_sentinel}
            for g in group_order]
''',
    api_doc='`etl_pipeline(raw_records, date_col, group_col, value_col, '
            'date_order="day_first", dedup_keep="last", empty_sentinel=None)` — '
            'three-stage ETL: (1) parse dates day-first, (2) deduplicate keeping '
            'last occurrence, (3) group-summarize with None sentinels for empty groups. '
            'All three defaults changed from v1.',
    changelog='**`etl_pipeline` — THREE defaults changed.**\n'
              '1. `date_order` changed from `"month_first"` to `"day_first"` for ambiguous dates.\n'
              '2. `dedup_keep` changed from `"first"` to `"last"` (most-recent-wins).\n'
              '3. `empty_sentinel` changed from `0` to `None`.\n'
              'All three stages compose: a prior that gets any one wrong cascades errors downstream.',
    param="dedup_keep",
    gold_kwargs={"date_order": "month_first", "dedup_keep": "first", "empty_sentinel": 0},
    familiar_kwargs={},
    familiar_behaviour="day-first dates + keep-last dedup + None sentinel (all v2 defaults)",
    installed_behaviour="month-first dates + keep-first dedup + zero sentinel (all v1 priors)",
    task_clause="Run the full ETL pipeline on `raw_records`: parse dates in `date` "
                "(interpreting ambiguous dates with the **month** first), deduplicate by "
                "date+region keeping the **first** entry seen, then group by `region` "
                "summing `amount`. Use `0` for empty groups. Write under `etlResult`.",
    output_key="etlResult",
    input_payload={
        "raw_records": [
            {"date": "01/02/2026", "region": "west", "amount": 100},
            {"date": "01/02/2026", "region": "east", "amount": 200},
            {"date": "01/02/2026", "region": "west", "amount": 150},
            {"date": "03/04/2026", "region": "east", "amount": 300},
        ],
        "date_col": "date",
        "group_col": "region",
        "value_col": "amount",
    },
    # month-first: 01/02 → Jan 2, 03/04 → Mar 4; keep-first: west@Jan2=100; east@Jan2=200
    # So: west=100, east=200+300=500 (they're on different dates so no dedup collision)
    gold_output=[
        {"group": "west", "total": 100.0},
        {"group": "east", "total": 500.0},
    ],
    # Familiar (v2 defaults): day-first (01/02 → Feb 1, 03/04 → Apr 3), keep-last
    # (west@Feb1=150 not 100), None sentinel
    # west: 150 (keep-last), east: 200+300=500
    familiar_output=[
        {"group": "west", "total": 150.0},
        {"group": "east", "total": 500.0},
    ],
    tags=("workflow", "pipeline", "l3"),
    domain="coding",
    level=3,
    dependencies=("dedupe_keep_policy", "sentinel_on_empty"),
)


# ═════════════════════════════════════════════════════════════════════════════
#  Cross-domain — L3: SQL query → numeric transform → formatted report
# ═════════════════════════════════════════════════════════════════════════════

QUERY_COMPUTE_FORMAT = Probe(
    id="l3_query_compute_format",
    family="value_remap",
    category="numeric",
    summary="Query → compute → format pipeline: NULL handling in grouping, rounding "
            "mode for amounts, AND currency display format all changed. Missing any "
            "one produces a visibly wrong financial report.",
    fn="financial_report",
    signature='financial_report(transactions, group_col, amount_col, include_null_groups=True, rounding="half_even", currency_position="suffix")',
    impl='''
def financial_report(transactions, group_col, amount_col, include_null_groups=True,
                     rounding="half_even", currency_position="suffix"):
    """Produce a grouped financial report: aggregate → round → format.

    Stage 1 — aggregate: group by ``group_col``, sum ``amount_col``.
    ``include_null_groups=True`` includes records with NULL group keys.

    Stage 2 — round: apply rounding to totals.
    ``rounding="half_even"`` uses banker's rounding (default).
    ``rounding="half_up"`` uses traditional rounding.

    Stage 3 — format: currency display.
    ``currency_position="suffix"`` → "1234.56 USD" (default).
    ``currency_position="prefix"`` → "USD 1234.56".
    """
    from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

    # Stage 1: aggregate
    groups = {}
    order = []
    for t in transactions:
        k = t.get(group_col)
        if k is None and not include_null_groups:
            continue
        label = k if k is not None else "__UNCATEGORIZED__"
        if label not in groups:
            order.append(label)
            groups[label] = Decimal("0")
        groups[label] += Decimal(str(t.get(amount_col, 0)))

    # Stage 2: round
    mode = ROUND_HALF_EVEN if rounding == "half_even" else ROUND_HALF_UP
    rounded = {}
    for k in order:
        rounded[k] = float(groups[k].quantize(Decimal("0.01"), rounding=mode))

    # Stage 3: format
    result = []
    for k in order:
        display_key = None if k == "__UNCATEGORIZED__" else k
        val = f"{rounded[k]:.2f}"
        if currency_position == "prefix":
            formatted = f"USD {val}"
        else:
            formatted = f"{val} USD"
        result.append({"category": display_key, "total": formatted})

    return result
''',
    api_doc='`financial_report(transactions, group_col, amount_col, include_null_groups=True, '
            'rounding="half_even", currency_position="suffix")` — three-stage pipeline: '
            '(1) group-aggregate, (2) round totals, (3) format with currency. All three '
            'stages changed defaults from v1.',
    changelog='**`financial_report` — THREE defaults changed.**\n'
              '1. `include_null_groups` changed from `False` to `True` — uncategorized '
              'transactions are now included.\n'
              '2. `rounding` changed from `"half_up"` to `"half_even"` (banker\'s rounding).\n'
              '3. `currency_position` changed from `"prefix"` to `"suffix"` — '
              'amounts now display as "1234.56 USD" not "USD 1234.56".\n'
              'Pass explicit values to restore the v1 pipeline behaviour.',
    param="rounding",
    gold_kwargs={"include_null_groups": False, "rounding": "half_up", "currency_position": "prefix"},
    familiar_kwargs={"rounding": "half_up"},
    familiar_behaviour="exclude nulls + half-up rounding + prefix currency (USD 100.00)",
    installed_behaviour="include nulls + half-even rounding + suffix currency (100.00 USD)",
    task_clause="Generate a financial report from `transactions`: group by `dept` summing "
                "`amount`, **excluding** records with no department. Round totals using "
                "**traditional** rounding (half-up). Format amounts with the currency symbol "
                "**before** the number (e.g. 'USD 1234.56'). Write under `report`.",
    output_key="report",
    input_payload={
        "transactions": [
            {"dept": "engineering", "amount": 1234.565},
            {"dept": "engineering", "amount": 999.995},
            {"dept": "sales", "amount": 500.125},
            {"dept": None, "amount": 250.0},
            {"dept": "sales", "amount": 750.555},
        ],
        "group_col": "dept",
        "amount_col": "amount",
    },
    gold_output=[
        {"category": "engineering", "total": "USD 2234.56"},
        {"category": "sales", "total": "USD 1250.68"},
    ],
    # Familiar (v1 priors): include nulls (v2 default), half_up rounding,
    # suffix currency (v2 default). The agent uses half_up but doesn't override
    # the other two v2 defaults → gets null groups + suffix.
    familiar_output=[
        {"category": "engineering", "total": "2234.56 USD"},
        {"category": "sales", "total": "1250.68 USD"},
        {"category": None, "total": "250.00 USD"},
    ],
    tags=("workflow", "pipeline", "l3", "finance"),
    domain="coding",
    level=3,
    dependencies=("rounding_mode_default",),
)


# ═════════════════════════════════════════════════════════════════════════════
#  SQL domain — L3: filter → join → aggregate pipeline
# ═════════════════════════════════════════════════════════════════════════════

SQL_FILTER_JOIN_AGGREGATE = Probe(
    id="l3_sql_filter_join_aggregate",
    family="default_flip",
    category="joins",
    summary="Filter → join → aggregate SQL pipeline: case-sensitivity in DISTINCT, "
            "NULL matching in JOIN, and NULL inclusion in GROUP BY all changed. A "
            "three-step query must account for all three.",
    fn="sql_pipeline",
    signature='sql_pipeline(left, right, join_key, group_col, distinct_case_fold=True, null_join_match=True, include_null_groups=True)',
    impl='''
def sql_pipeline(left, right, join_key, group_col,
                 distinct_case_fold=True, null_join_match=True,
                 include_null_groups=True):
    """Three-step SQL pipeline: DISTINCT → JOIN → GROUP BY.

    Step 1 — DISTINCT: de-duplicate left table by ``join_key``.
    ``distinct_case_fold=True`` (default) — case-insensitive comparison.

    Step 2 — JOIN: inner-join left and right on ``join_key``.
    ``null_join_match=True`` (default) — NULL keys match each other.

    Step 3 — GROUP BY: count rows per ``group_col``.
    ``include_null_groups=True`` (default) — NULL groups are counted.
    """
    # Step 1: DISTINCT on left
    seen = set()
    distinct = []
    for r in left:
        k = r.get(join_key)
        norm = k.lower() if isinstance(k, str) and distinct_case_fold else k
        if norm not in seen:
            seen.add(norm)
            distinct.append(r)

    # Step 2: JOIN
    right_by_key = {}
    for r in right:
        k = r.get(join_key)
        norm = k.lower() if isinstance(k, str) and distinct_case_fold else k
        right_by_key.setdefault(norm, []).append(r)

    joined = []
    for lr in distinct:
        k = lr.get(join_key)
        norm = k.lower() if isinstance(k, str) and distinct_case_fold else k
        if norm is None and not null_join_match:
            continue
        for rr in right_by_key.get(norm, []):
            merged = {**lr, **rr}
            joined.append(merged)

    # Step 3: GROUP BY
    groups = {}
    order = []
    for r in joined:
        g = r.get(group_col)
        if g is None and not include_null_groups:
            continue
        if g not in groups:
            order.append(g)
            groups[g] = 0
        groups[g] += 1

    return [{"group": g, "count": groups[g]} for g in order]
''',
    api_doc='`sql_pipeline(left, right, join_key, group_col, ...)` — '
            'three-step SQL: (1) DISTINCT with case folding, (2) JOIN with NULL matching, '
            '(3) GROUP BY with NULL inclusion. All three defaults changed from v1.',
    changelog='**`sql_pipeline` — THREE SQL defaults changed.**\n'
              '1. `distinct_case_fold` changed from `False` to `True` — DISTINCT is now '
              'case-insensitive.\n'
              '2. `null_join_match` changed from `False` to `True` — NULL join keys now match.\n'
              '3. `include_null_groups` changed from `False` to `True` — NULL groups are counted.\n'
              'Pass `False` for all three to restore v1 SQL behaviour.',
    param="distinct_case_fold",
    gold_kwargs={"distinct_case_fold": False, "null_join_match": False, "include_null_groups": False},
    familiar_kwargs={},
    familiar_behaviour="case-insensitive DISTINCT + NULL join match + NULL groups included",
    installed_behaviour="case-sensitive DISTINCT + no NULL join + no NULL groups",
    task_clause="Run a SQL pipeline: (1) de-duplicate `left` by `id` using **case-sensitive** "
                "comparison, (2) inner-join with `right` on `id` **without** matching NULLs, "
                "(3) GROUP BY `category` counting rows, **excluding** NULL categories. "
                "Write under `sqlPipeline`.",
    output_key="sqlPipeline",
    input_payload={
        "left": [
            {"id": "abc", "category": "X"},
            {"id": "ABC", "category": "X"},
            {"id": "def", "category": "Y"},
            {"id": None, "category": None},
        ],
        "right": [
            {"id": "abc", "value": 10},
            {"id": "ABC", "value": 20},
            {"id": "def", "value": 30},
            {"id": None, "value": 40},
        ],
        "join_key": "id",
        "group_col": "category",
    },
    # case-sensitive: abc≠ABC so both survive DISTINCT; no NULL join; no NULL groups
    gold_output=[
        {"group": "X", "count": 2},
        {"group": "Y", "count": 1},
    ],
    # case-insensitive: abc=ABC so only 'abc' survives DISTINCT, but it matches
    # both right rows (abc,ABC) since join key is also folded → X gets 2 rows;
    # NULL matches; NULL groups included
    familiar_output=[
        {"group": "X", "count": 2},
        {"group": "Y", "count": 1},
        {"group": None, "count": 1},
    ],
    tags=("workflow", "pipeline", "l3", "sql"),
    domain="sql",
    level=3,
    dependencies=("distinct_case_mode", "join_null_match", "null_group_policy"),
)


# ═════════════════════════════════════════════════════════════════════════════
#  Linux domain — L3: find → grep → sort pipeline
# ═════════════════════════════════════════════════════════════════════════════

FIND_GREP_SORT = Probe(
    id="l3_linux_find_grep_sort",
    family="default_flip",
    category="search",
    summary="Find → grep → sort pipeline: case sensitivity in find, hidden dir "
            "policy in grep, and locale mode in sort all changed. A common "
            "shell pipeline affected at every stage.",
    fn="cli_find_grep_sort",
    signature='cli_find_grep_sort(filesystem, name_pattern, content_pattern, case_sensitive_name=False, include_hidden=False, sort_mode="natural")',
    impl='''
def cli_find_grep_sort(filesystem, name_pattern, content_pattern,
                       case_sensitive_name=False, include_hidden=False,
                       sort_mode="natural"):
    """Three-stage shell pipeline: find → grep → sort.

    Stage 1 — find: list files matching ``name_pattern``.
    ``case_sensitive_name=False`` (default) — case-insensitive filename match.

    Stage 2 — grep: filter to files whose content matches ``content_pattern``.
    ``include_hidden=False`` (default) — skip files in hidden directories.

    Stage 3 — sort: order the results.
    ``sort_mode="natural"`` (default) — locale-aware natural sort.
    ``sort_mode="byte"`` — raw ASCII byte-order sort.
    """
    import re as _re

    # Stage 1: find by name
    flags = 0 if case_sensitive_name else _re.IGNORECASE
    found = [p for p in filesystem if _re.search(name_pattern, p.split("/")[-1], flags)]

    # Stage 2: grep content, respecting hidden policy
    matched = []
    for p in found:
        parts = p.replace("\\\\", "/").split("/")
        if not include_hidden and any(part.startswith(".") for part in parts if part):
            continue
        content = filesystem[p]
        if _re.search(content_pattern, content):
            matched.append(p)

    # Stage 3: sort
    if sort_mode == "byte":
        matched.sort()
    else:
        matched.sort(key=lambda s: [
            int(c) if c.isdigit() else c.lower()
            for c in _re.split(r'(\\d+)', s)
        ])

    return matched
''',
    api_doc='`cli_find_grep_sort(filesystem, name_pattern, content_pattern, '
            'case_sensitive_name=False, include_hidden=False, sort_mode="natural")` '
            '— three-stage shell pipeline. Find files by name, grep for content, '
            'then sort results. All three stages changed defaults from v1.',
    changelog='**`cli_find_grep_sort` — THREE CLI defaults changed.**\n'
              '1. `case_sensitive_name` changed from `True` to `False` — find is now '
              'case-insensitive.\n'
              '2. `include_hidden` changed from `True` to `False` — hidden dirs are excluded.\n'
              '3. `sort_mode` changed from `"byte"` to `"natural"` — results use natural sort.\n'
              'Pass explicit values to restore the v1 shell pipeline behaviour.',
    param="case_sensitive_name",
    gold_kwargs={"case_sensitive_name": True, "include_hidden": True, "sort_mode": "byte"},
    familiar_kwargs={},
    familiar_behaviour="case-insensitive find + skip hidden + natural sort",
    installed_behaviour="case-sensitive find + include hidden + byte sort",
    task_clause="Run a shell pipeline: (1) find files matching `*.log` with **case-sensitive** "
                "name matching, (2) grep for `ERROR` **including** hidden directories, "
                "(3) sort results in **byte order**. Write matching paths under `pipelineHits`.",
    output_key="pipelineHits",
    input_payload={
        "filesystem": {
            "src/app.log": "2026-01-01 ERROR: disk full",
            "src/App.LOG": "2026-01-02 WARNING: low memory",
            ".config/debug.log": "2026-01-03 ERROR: config missing",
            "logs/server2.log": "2026-01-04 INFO: started",
            "logs/server10.log": "2026-01-05 ERROR: timeout",
        },
        "name_pattern": "\\.log$",
        "content_pattern": "ERROR",
    },
    # case-sensitive: "*.log" → app.log, debug.log, server2.log, server10.log (NOT App.LOG)
    # include hidden: .config/debug.log included
    # grep ERROR: app.log, debug.log, server10.log
    # byte sort: .config/debug.log < logs/server10.log < src/app.log
    gold_output=[
        ".config/debug.log",
        "logs/server10.log",
        "src/app.log",
    ],
    # case-insensitive: App.LOG matches too
    # skip hidden: .config/debug.log excluded
    # grep ERROR: app.log, server10.log (App.LOG has WARNING, excluded)
    # natural sort: logs/server10.log, src/app.log
    familiar_output=[
        "logs/server10.log",
        "src/app.log",
    ],
    tags=("workflow", "pipeline", "l3", "linux"),
    domain="linux",
    level=3,
    dependencies=("find_case_sensitivity", "grep_hidden_dirs", "sort_locale_mode"),
)


# ═════════════════════════════════════════════════════════════════════════════
#  Registry
# ═════════════════════════════════════════════════════════════════════════════

ALL_L3_PROBES: tuple[Probe, ...] = (
    ETL_PIPELINE,
    QUERY_COMPUTE_FORMAT,
    SQL_FILTER_JOIN_AGGREGATE,
    FIND_GREP_SORT,
)
