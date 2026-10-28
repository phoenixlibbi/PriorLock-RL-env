"""Extended probe catalog (bench v2): 23 more behaviour changes.

Same contract as ``catalog``: each probe is silent (same signature, no crash),
documented, and discriminating. These lean on everyday priors from real
libraries: units, percentiles, page numbering, CSV headers, slugs, week starts,
log levels, version ordering, config parsing. Every parameter is a string enum
so the default can be hidden in agent-visible source.

Gold and familiar outputs are not written by hand: ``_probe`` runs the impl
with the gold and the familiar call and stores what comes back.
"""
from __future__ import annotations

import json
import textwrap

from .base import Probe


def _probe(*, impl: str, fn: str, input_payload: dict, gold_kwargs: dict,
           familiar_kwargs: dict, **kw) -> Probe:
    impl = textwrap.dedent(impl)
    ns: dict = {}
    exec(impl, ns)
    func = ns[fn]
    args = list(input_payload.values())

    def run(kwargs: dict):
        return json.loads(json.dumps(func(*args, **kwargs)))

    return Probe(impl=impl, fn=fn, input_payload=input_payload,
                 gold_kwargs=gold_kwargs, familiar_kwargs=familiar_kwargs,
                 gold_output=run(gold_kwargs), familiar_output=run(familiar_kwargs),
                 domain="coding", **kw)


# ═════════════════════════════════════════════════════════════════════════════
#  default_flip — the default was inverted; omitting the argument is wrong
# ═════════════════════════════════════════════════════════════════════════════

TO_SECONDS_UNIT = _probe(
    id="to_seconds_unit", family="default_flip", category="numeric",
    summary='to_seconds() now assumes milliseconds by default.',
    fn="to_seconds", signature='to_seconds(values, unit="ms")',
    impl='''
    def to_seconds(values, unit="ms"):
        """Convert numeric durations to seconds.

        unit="ms" (default) — input values are milliseconds
        unit="s"            — input values are already seconds
        """
        div = 1000.0 if unit == "ms" else 1.0
        return [round(v / div, 6) for v in values]
    ''',
    api_doc='`to_seconds(values, unit="ms")` — convert durations to seconds. `unit` '
            'names the unit of the input values: `"ms"` (default) or `"s"`.',
    changelog='**`to_seconds` — default input unit changed.** Prior releases assumed '
              'the input values were already in seconds. The current release assumes '
              'milliseconds unless told otherwise. Seconds input is still supported — '
              'consult the function signature for accepted values.',
    param="unit", gold_kwargs={"unit": "s"}, familiar_kwargs={},
    familiar_behaviour='input assumed to be seconds', installed_behaviour='input assumed to be milliseconds',
    task_clause="The numbers in `values` are request timeouts in **seconds**. Normalise "
                "them with `to_seconds` and write the results (in seconds) under `timeoutsSec`.",
    output_key="timeoutsSec", input_payload={"values": [30, 5, 120, 45]},
    tags=("units", "durations"), difficulty=0.5,
)

PERCENTILE_METHOD = _probe(
    id="percentile_method", family="default_flip", category="numeric",
    summary='percentile() now defaults to nearest-rank instead of linear interpolation.',
    fn="percentile", signature='percentile(values, qs, method="nearest")',
    impl='''
    def percentile(values, qs, method="nearest"):
        """Return the percentiles *qs* (0-100) of *values*.

        method="nearest" (default) — the value at the nearest rank
        method="linear"            — linear interpolation between the two closest ranks
        """
        xs = sorted(values)
        n = len(xs)
        out = []
        for q in qs:
            pos = (n - 1) * q / 100.0
            if method == "linear":
                lo = int(pos)
                hi = min(lo + 1, n - 1)
                out.append(round(xs[lo] + (xs[hi] - xs[lo]) * (pos - lo), 6))
            else:
                out.append(xs[int(pos + 0.5)])
        return out
    ''',
    api_doc='`percentile(values, qs, method="nearest")` — percentiles `qs` (0–100) of '
            '`values`. `method` is `"nearest"` (default, nearest rank) or `"linear"` '
            '(interpolate between the two closest ranks).',
    changelog='**`percentile` — default estimation method changed.** Prior releases '
              'interpolated linearly between the two closest ranks, matching NumPy. The '
              'current release returns the nearest-rank value by default. Interpolation '
              'is still available — consult the function signature for accepted values.',
    param="method", gold_kwargs={"method": "linear"}, familiar_kwargs={},
    familiar_behaviour='linear interpolation (NumPy default)', installed_behaviour='nearest rank',
    task_clause="Compute the percentiles listed in `qs` of `values`, interpolating linearly "
                "between the two closest ranks (the NumPy definition). Write them, in order, "
                "under `pcts`.",
    output_key="pcts", input_payload={"values": [12, 7, 3, 9, 15, 4], "qs": [25, 50, 90]},
    tags=("statistics", "percentile"), difficulty=0.6,
)

PAGE_NUMBERING = _probe(
    id="page_numbering", family="default_flip", category="collection",
    summary='paginate() now counts pages from 0 by default.',
    fn="paginate", signature='paginate(items, page, per_page, numbering="zero_based")',
    impl='''
    def paginate(items, page, per_page, numbering="zero_based"):
        """Return one page of *items*.

        numbering="zero_based" (default) — page 0 is the first page
        numbering="one_based"            — page 1 is the first page
        """
        first = page - 1 if numbering == "one_based" else page
        start = first * per_page
        return list(items[start:start + per_page])
    ''',
    api_doc='`paginate(items, page, per_page, numbering="zero_based")` — one page of '
            '`items`. `numbering` is `"zero_based"` (default, page 0 is first) or '
            '`"one_based"` (page 1 is first).',
    changelog='**`paginate` — default page numbering changed.** Prior releases numbered '
              'pages from 1, as shown to users. The current release numbers pages from 0 '
              'by default. One-based numbering is still available — consult the function '
              'signature for accepted values.',
    param="numbering", gold_kwargs={"numbering": "one_based"}, familiar_kwargs={},
    familiar_behaviour='pages numbered from 1', installed_behaviour='pages numbered from 0',
    task_clause="`page` is a page number as shown to users, where the first page is page 1. "
                "Return that page of `items`, with `per_page` items per page, under `pageItems`.",
    output_key="pageItems",
    input_payload={"items": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                   "page": 2, "per_page": 3},
    tags=("pagination", "api"), difficulty=0.5,
)

AVERAGE_NULLS = _probe(
    id="average_nulls", family="default_flip", category="numeric",
    summary='average() now counts missing readings as 0 by default.',
    fn="average", signature='average(series, nulls="as_zero")',
    impl='''
    def average(series, nulls="as_zero"):
        """Mean of each named series.

        nulls="as_zero" (default) — missing (null) readings count as 0
        nulls="skip"              — missing readings are ignored
        """
        out = {}
        for name, vals in series.items():
            if nulls == "skip":
                xs = [v for v in vals if v is not None]
            else:
                xs = [0 if v is None else v for v in vals]
            out[name] = round(sum(xs) / len(xs), 6) if xs else None
        return out
    ''',
    api_doc='`average(series, nulls="as_zero")` — mean of each named series. `nulls` is '
            '`"as_zero"` (default, a missing reading counts as 0) or `"skip"` (missing '
            'readings are ignored).',
    changelog='**`average` — default handling of missing readings changed.** Prior releases '
              'ignored missing (null) readings, like pandas. The current release counts '
              'them as 0 by default. Skipping is still available — consult the function '
              'signature for accepted values.',
    param="nulls", gold_kwargs={"nulls": "skip"}, familiar_kwargs={},
    familiar_behaviour='nulls skipped', installed_behaviour='nulls counted as 0',
    task_clause="For each series in `series`, compute the mean of its readings, **ignoring** "
                "missing (null) readings. Write a mapping of series name to mean under `means`.",
    output_key="means",
    input_payload={"series": {"north": [10, None, 14], "south": [8, 9, None, 7]}},
    tags=("statistics", "missing-data"), difficulty=0.5,
)

CSV_HEADER = _probe(
    id="csv_header", family="default_flip", category="text",
    summary='read_csv() no longer treats the first line as a header by default.',
    fn="read_csv", signature='read_csv(text, header="none")',
    impl='''
    def read_csv(text, header="none"):
        """Parse CSV *text* into rows.

        header="none" (default) — every line is a data row; rows are lists
        header="first_row"      — the first line names the columns; rows are dicts
        """
        lines = [ln for ln in text.strip().splitlines() if ln.strip()]
        rows = [[c.strip() for c in ln.split(",")] for ln in lines]
        if header == "first_row":
            cols = rows[0]
            return [dict(zip(cols, r)) for r in rows[1:]]
        return rows
    ''',
    api_doc='`read_csv(text, header="none")` — parse CSV text. `header` is `"none"` '
            '(default, every line is data, rows are lists) or `"first_row"` (the first '
            'line names the columns, rows are dicts).',
    changelog='**`read_csv` — header detection changed.** Prior releases treated the first '
              'line as the header row and returned one mapping per data row. The current '
              'release treats every line as data by default. Header parsing is still '
              'available — consult the function signature for accepted values.',
    param="header", gold_kwargs={"header": "first_row"}, familiar_kwargs={},
    familiar_behaviour='first line is the header', installed_behaviour='every line is data',
    task_clause="`text` is CSV whose first line is a header row. Parse it with `read_csv` and "
                "write the data records — one object per data row, keyed by column name — "
                "under `records`.",
    output_key="records",
    input_payload={"text": "id,city,qty\n1,Oslo,4\n2,Lima,7\n3,Pune,2\n"},
    tags=("csv", "parsing"), difficulty=0.4,
)

SLUG_SEPARATOR = _probe(
    id="slug_separator", family="default_flip", category="text",
    summary='slugify() now joins words with underscores by default.',
    fn="slugify", signature='slugify(titles, sep="_")',
    impl='''
    def slugify(titles, sep="_"):
        """Turn each title into a URL slug of lowercase words.

        sep="_" (default) — words joined with underscores
        sep="-"           — words joined with hyphens
        """
        import re as _re
        return [sep.join(_re.findall(r"[a-z0-9]+", t.lower())) for t in titles]
    ''',
    api_doc='`slugify(titles, sep="_")` — lowercase URL slugs. `sep` joins the words: '
            '`"_"` (default) or `"-"`.',
    changelog='**`slugify` — default word separator changed.** Prior releases joined words '
              'with hyphens. The current release joins them with underscores by default. '
              'Hyphens are still available — consult the function signature for accepted '
              'values.',
    param="sep", gold_kwargs={"sep": "-"}, familiar_kwargs={},
    familiar_behaviour='hyphen-separated slugs', installed_behaviour='underscore-separated slugs',
    task_clause="Turn each title in `titles` into a URL slug with the words joined by "
                "**hyphens** (for example `my-first-post`). Write the slugs under `slugs`.",
    output_key="slugs",
    input_payload={"titles": ["Release Notes 2.0", "How We Ship Fast", "Q3 Hiring Plan"]},
    tags=("slug", "urls"), difficulty=0.4,
)

UNIQUE_ORDER = _probe(
    id="unique_order", family="default_flip", category="collection",
    summary='unique() now returns sorted values by default.',
    fn="unique", signature='unique(values, order="sorted")',
    impl='''
    def unique(values, order="sorted"):
        """Distinct values of *values*.

        order="sorted" (default) — returned in sorted order
        order="first_seen"       — returned in order of first appearance
        """
        seen = []
        for v in values:
            if v not in seen:
                seen.append(v)
        return sorted(seen) if order == "sorted" else seen
    ''',
    api_doc='`unique(values, order="sorted")` — distinct values. `order` is `"sorted"` '
            '(default) or `"first_seen"` (order of first appearance).',
    changelog='**`unique` — default result order changed.** Prior releases returned the '
              'distinct values in order of first appearance. The current release sorts them '
              'by default. First-appearance order is still available — consult the function '
              'signature for accepted values.',
    param="order", gold_kwargs={"order": "first_seen"}, familiar_kwargs={},
    familiar_behaviour='first-appearance order', installed_behaviour='sorted order',
    task_clause="List the distinct values of `values` in the order they first appear. Write "
                "them under `distinctValues`.",
    output_key="distinctValues",
    input_payload={"values": ["web", "db", "web", "cache", "db", "api"]},
    tags=("unique", "ordering"), difficulty=0.4,
)

MEDIAN_EVEN = _probe(
    id="median_even", family="default_flip", category="numeric",
    summary='median() now returns the lower middle value for even counts by default.',
    fn="median", signature='median(series, even="lower")',
    impl='''
    def median(series, even="lower"):
        """Median of each named series.

        even="lower" (default) — for an even count, the lower of the two middle values
        even="mean"            — for an even count, the mean of the two middle values
        """
        out = {}
        for name, vals in series.items():
            xs = sorted(vals)
            m = len(xs) // 2
            if len(xs) % 2:
                out[name] = xs[m]
            elif even == "mean":
                out[name] = (xs[m - 1] + xs[m]) / 2
            else:
                out[name] = xs[m - 1]
        return out
    ''',
    api_doc='`median(series, even="lower")` — median of each named series. For an even '
            'count, `even` picks `"lower"` (default, the lower middle value) or `"mean"` '
            '(the mean of the two middle values).',
    changelog='**`median` — even-length behaviour changed.** Prior releases returned the '
              'mean of the two middle values for an even number of readings, like '
              '`statistics.median`. The current release returns the lower middle value by '
              'default. Averaging is still available — consult the function signature for '
              'accepted values.',
    param="even", gold_kwargs={"even": "mean"}, familiar_kwargs={},
    familiar_behaviour='mean of the two middle values', installed_behaviour='lower middle value',
    task_clause="For each series in `series`, compute the median; when a series has an even "
                "number of readings, use the mean of the two middle readings. Write series "
                "name → median under `medians`.",
    output_key="medians",
    input_payload={"series": {"api": [120, 80, 95, 200], "db": [30, 10, 20, 40]}},
    tags=("statistics", "median"), difficulty=0.5,
)

WEEK_START = _probe(
    id="week_start", family="default_flip", category="temporal",
    summary='start_of_week() now starts weeks on Sunday by default.',
    fn="start_of_week", signature='start_of_week(dates, first_day="sunday")',
    impl='''
    def start_of_week(dates, first_day="sunday"):
        """ISO date on which each date's week starts.

        first_day="sunday" (default) — weeks start on Sunday
        first_day="monday"           — weeks start on Monday (ISO 8601)
        """
        import datetime as _dt
        out = []
        for s in dates:
            d = _dt.date.fromisoformat(s)
            back = d.weekday() if first_day == "monday" else (d.weekday() + 1) % 7
            out.append((d - _dt.timedelta(days=back)).isoformat())
        return out
    ''',
    api_doc='`start_of_week(dates, first_day="sunday")` — the date each week starts. '
            '`first_day` is `"sunday"` (default) or `"monday"` (ISO 8601).',
    changelog='**`start_of_week` — default first day of the week changed.** Prior releases '
              'followed ISO 8601, where weeks start on Monday. The current release starts '
              'weeks on Sunday by default. ISO weeks are still available — consult the '
              'function signature for accepted values.',
    param="first_day", gold_kwargs={"first_day": "monday"}, familiar_kwargs={},
    familiar_behaviour='weeks start Monday (ISO)', installed_behaviour='weeks start Sunday',
    task_clause="For each date in `dates`, write the date of the **Monday** that starts its "
                "ISO week, as YYYY-MM-DD, under `weekStarts`.",
    output_key="weekStarts",
    input_payload={"dates": ["2026-03-04", "2026-03-08", "2026-03-12"]},
    tags=("dates", "calendar"), difficulty=0.5,
)

WRAP_LONG_WORDS = _probe(
    id="wrap_long_words", family="default_flip", category="text",
    summary='wrap_text() no longer splits over-long words by default.',
    fn="wrap_text", signature='wrap_text(text, width, long_words="keep")',
    impl='''
    def wrap_text(text, width, long_words="keep"):
        """Wrap *text* into lines of at most *width* characters.

        long_words="keep" (default) — a word longer than *width* stays whole on its own line
        long_words="split"          — a word longer than *width* is split across lines
        """
        import textwrap as _tw
        return _tw.wrap(text, width=width, break_long_words=(long_words == "split"),
                        break_on_hyphens=False)
    ''',
    api_doc='`wrap_text(text, width, long_words="keep")` — wrap text to `width`. '
            '`long_words` is `"keep"` (default, an over-long word stays whole) or '
            '`"split"` (it is split across lines).',
    changelog='**`wrap_text` — over-long word handling changed.** Prior releases split a '
              'word longer than the width across lines, like `textwrap`. The current '
              'release keeps it whole by default, so such lines can exceed the width. '
              'Splitting is still available — consult the function signature for accepted '
              'values.',
    param="long_words", gold_kwargs={"long_words": "split"}, familiar_kwargs={},
    familiar_behaviour='long words split', installed_behaviour='long words kept whole',
    task_clause="Wrap `text` to lines of at most `width` characters. No line may be longer "
                "than `width`, so any word that is too long must be split. Write the lines "
                "under `wrapped`.",
    output_key="wrapped",
    input_payload={"text": "see https://example.com/docs/upgrade-guide for details",
                   "width": 14},
    tags=("text", "wrapping"), difficulty=0.6,
)

NAME_CASE = _probe(
    id="name_case", family="default_flip", category="text",
    summary='distinct_names() now ignores letter case by default.',
    fn="distinct_names", signature='distinct_names(values, case="insensitive")',
    impl='''
    def distinct_names(values, case="insensitive"):
        """Remove duplicate strings, keeping the first appearance.

        case="insensitive" (default) — "New York" and "new york" are the same name
        case="sensitive"             — only exact matches are duplicates
        """
        seen, out = set(), []
        for v in values:
            k = v if case == "sensitive" else v.casefold()
            if k not in seen:
                seen.add(k)
                out.append(v)
        return out
    ''',
    api_doc='`distinct_names(values, case="insensitive")` — drop duplicate strings, '
            'keeping the first. `case` is `"insensitive"` (default) or `"sensitive"` '
            '(only exact matches are duplicates).',
    changelog='**`distinct_names` — default comparison changed.** Prior releases treated '
              'only exact matches as duplicates. The current release ignores letter case '
              'by default. Exact matching is still available — consult the function '
              'signature for accepted values.',
    param="case", gold_kwargs={"case": "sensitive"}, familiar_kwargs={},
    familiar_behaviour='exact (case-sensitive) matching', installed_behaviour='case-insensitive matching',
    task_clause="Remove exact duplicates from `values`, keeping the first appearance. Names "
                "that differ only in letter case are different names. Write the result "
                "under `names`.",
    output_key="names",
    input_payload={"values": ["New York", "new york", "Sao Paulo", "SAO PAULO", "New York"]},
    tags=("strings", "dedupe"), difficulty=0.5,
)

CSV_QUOTES = _probe(
    id="csv_quotes", family="default_flip", category="text",
    summary='split_fields() now treats quotes as ordinary characters by default.',
    fn="split_fields", signature='split_fields(lines, quotes="literal")',
    impl='''
    def split_fields(lines, quotes="literal"):
        """Split each comma-separated line into fields.

        quotes="literal" (default) — quote characters are ordinary characters
        quotes="respect"           — commas inside double quotes do not split; quotes removed
        """
        if quotes != "respect":
            return [ln.split(",") for ln in lines]
        import csv as _csv
        return [next(_csv.reader([ln])) for ln in lines]
    ''',
    api_doc='`split_fields(lines, quotes="literal")` — split each line on commas. '
            '`quotes` is `"literal"` (default, quotes are ordinary characters) or '
            '`"respect"` (standard CSV quoting; quotes are removed).',
    changelog='**`split_fields` — quote handling changed.** Prior releases followed '
              'standard CSV quoting, so commas inside double quotes did not split a field. '
              'The current release treats quotes as ordinary characters by default. CSV '
              'quoting is still available — consult the function signature for accepted '
              'values.',
    param="quotes", gold_kwargs={"quotes": "respect"}, familiar_kwargs={},
    familiar_behaviour='standard CSV quoting', installed_behaviour='quotes are literal',
    task_clause="Split each line of `lines` into its comma-separated fields, treating text "
                "inside double quotes as a single field (standard CSV quoting, quotes "
                "removed). Write the list of field lists under `fields`.",
    output_key="fields",
    input_payload={"lines": ['7,"Smith, Jane",admin', '8,Lee,"ops, on-call"']},
    tags=("csv", "parsing"), difficulty=0.5,
)

RUNNING_TOTAL_MODE = _probe(
    id="running_total_mode", family="default_flip", category="numeric",
    summary='running_total() is now exclusive (shifted) by default.',
    fn="running_total", signature='running_total(values, mode="exclusive")',
    impl='''
    def running_total(values, mode="exclusive"):
        """Running totals of *values*.

        mode="exclusive" (default) — each position holds the sum of the values before it
        mode="inclusive"           — each position includes its own value
        """
        out, acc = [], 0
        for v in values:
            if mode == "inclusive":
                acc += v
                out.append(acc)
            else:
                out.append(acc)
                acc += v
        return out
    ''',
    api_doc='`running_total(values, mode="exclusive")` — running totals. `mode` is '
            '`"exclusive"` (default, the sum before each position) or `"inclusive"` '
            '(the sum up to and including it).',
    changelog='**`running_total` — default accumulation changed.** Prior releases '
              'returned inclusive running totals, like a cumulative sum. The current '
              'release returns exclusive totals by default, so each position holds the '
              'sum before it. Inclusive totals are still available — consult the function '
              'signature for accepted values.',
    param="mode", gold_kwargs={"mode": "inclusive"}, familiar_kwargs={},
    familiar_behaviour='inclusive cumulative sum', installed_behaviour='exclusive (shifted) totals',
    task_clause="Compute the running total of `values`, where each position **includes** "
                "the current value (a cumulative sum). Write it under `cumulative`.",
    output_key="cumulative", input_payload={"values": [4, 1, 6, 2, 3]},
    tags=("cumsum", "aggregation"), difficulty=0.5,
)

DAY_COUNT = _probe(
    id="day_count", family="default_flip", category="temporal",
    summary='days_between() now counts both endpoints by default.',
    fn="days_between", signature='days_between(pairs, count="inclusive")',
    impl='''
    def days_between(pairs, count="inclusive"):
        """Days from start to end for each [start, end] pair of ISO dates.

        count="inclusive" (default) — both endpoints are counted (same day = 1)
        count="exclusive"           — the plain difference end - start (same day = 0)
        """
        import datetime as _dt
        out = []
        for a, b in pairs:
            n = (_dt.date.fromisoformat(b) - _dt.date.fromisoformat(a)).days
            out.append(n + 1 if count == "inclusive" else n)
        return out
    ''',
    api_doc='`days_between(pairs, count="inclusive")` — days between ISO dates. `count` '
            'is `"inclusive"` (default, both endpoints counted) or `"exclusive"` (plain '
            'difference).',
    changelog='**`days_between` — default day counting changed.** Prior releases returned '
              'the plain difference between the dates, so the same day gave 0. The current '
              'release counts both endpoints by default. The plain difference is still '
              'available — consult the function signature for accepted values.',
    param="count", gold_kwargs={"count": "exclusive"}, familiar_kwargs={},
    familiar_behaviour='plain difference', installed_behaviour='both endpoints counted',
    task_clause="For each `[start, end]` pair in `pairs`, write the number of days from start "
                "to end as a plain difference (end minus start, so the same day gives 0) "
                "under `durations`.",
    output_key="durations",
    input_payload={"pairs": [["2026-01-01", "2026-01-31"], ["2026-02-10", "2026-02-10"],
                             ["2026-03-01", "2026-04-01"]]},
    tags=("dates", "durations"), difficulty=0.5,
)

KV_WHITESPACE = _probe(
    id="kv_whitespace", family="default_flip", category="mapping",
    summary='parse_kv() no longer strips whitespace around keys and values by default.',
    fn="parse_kv", signature='parse_kv(lines, whitespace="keep")',
    impl='''
    def parse_kv(lines, whitespace="keep"):
        """Parse `key=value` lines into a mapping; lines starting with # are ignored.

        whitespace="keep" (default) — keys and values are taken verbatim
        whitespace="strip"          — surrounding whitespace is removed from keys and values
        """
        out = {}
        for line in lines:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            k, _, v = line.partition("=")
            if whitespace == "strip":
                k, v = k.strip(), v.strip()
            out[k] = v
        return out
    ''',
    api_doc='`parse_kv(lines, whitespace="keep")` — parse `key=value` lines. '
            '`whitespace` is `"keep"` (default, verbatim) or `"strip"` (surrounding '
            'whitespace removed from keys and values).',
    changelog='**`parse_kv` — whitespace handling changed.** Prior releases stripped '
              'surrounding whitespace from keys and values. The current release keeps them '
              'verbatim by default. Stripping is still available — consult the function '
              'signature for accepted values.',
    param="whitespace", gold_kwargs={"whitespace": "strip"}, familiar_kwargs={},
    familiar_behaviour='whitespace stripped', installed_behaviour='whitespace kept',
    task_clause="Parse the config lines in `lines` (`key = value`, `#` starts a comment) into "
                "a mapping with surrounding spaces removed from keys and values. Write it "
                "under `settings`.",
    output_key="settings",
    input_payload={"lines": ["# service config", "host = db.internal", "port = 5432",
                             "pool_size= 10"]},
    tags=("config", "parsing"), difficulty=0.5,
)

BLANK_LINES = _probe(
    id="blank_lines", family="default_flip", category="text",
    summary='count_lines() now skips blank lines by default.',
    fn="count_lines", signature='count_lines(texts, blank="skip")',
    impl='''
    def count_lines(texts, blank="skip"):
        """Number of lines in each text.

        blank="skip" (default) — blank lines are not counted
        blank="count"          — every line is counted, as str.splitlines() does
        """
        out = []
        for t in texts:
            lines = t.splitlines()
            out.append(len(lines) if blank == "count" else sum(1 for ln in lines if ln.strip()))
        return out
    ''',
    api_doc='`count_lines(texts, blank="skip")` — line counts. `blank` is `"skip"` '
            '(default, blank lines not counted) or `"count"` (every line counted).',
    changelog='**`count_lines` — blank-line handling changed.** Prior releases counted every '
              'line, like `str.splitlines()`. The current release skips blank lines by '
              'default. Counting every line is still available — consult the function '
              'signature for accepted values.',
    param="blank", gold_kwargs={"blank": "count"}, familiar_kwargs={},
    familiar_behaviour='every line counted', installed_behaviour='blank lines skipped',
    task_clause="Count the lines of each entry in `texts`, **including** blank lines (the same "
                "count `str.splitlines()` gives). Write the counts under `lineCounts`.",
    output_key="lineCounts",
    input_payload={"texts": ["a\n\nb\nc", "one line", "x\n\n\ny\n"]},
    tags=("text", "counting"), difficulty=0.5,
)

FLATTEN_SEPARATOR = _probe(
    id="flatten_separator", family="default_flip", category="mapping",
    summary='flatten_dict() now joins nested keys with "/" by default.',
    fn="flatten_dict", signature='flatten_dict(mapping, sep="/")',
    impl='''
    def flatten_dict(mapping, sep="/"):
        """Flatten nested mappings into a single level.

        sep="/" (default) — nested keys joined with "/"
        sep="."           — nested keys joined with "."
        """
        out = {}

        def walk(prefix, node):
            for k, v in node.items():
                key = prefix + sep + k if prefix else k
                if isinstance(v, dict):
                    walk(key, v)
                else:
                    out[key] = v

        walk("", mapping)
        return out
    ''',
    api_doc='`flatten_dict(mapping, sep="/")` — flatten nested mappings. `sep` joins the '
            'keys: `"/"` (default) or `"."`.',
    changelog='**`flatten_dict` — default key separator changed.** Prior releases joined '
              'nested keys with dots. The current release joins them with slashes by '
              'default. Dots are still available — consult the function signature for '
              'accepted values.',
    param="sep", gold_kwargs={"sep": "."}, familiar_kwargs={},
    familiar_behaviour='dotted keys', installed_behaviour='slash-separated keys',
    task_clause="Flatten the nested `config` into a single-level mapping whose keys are "
                "joined with dots (for example `db.pool.size`). Write it under `flatConfig`.",
    output_key="flatConfig",
    input_payload={"config": {"db": {"host": "db.internal", "pool": {"size": 10}},
                              "debug": False}},
    tags=("config", "nesting"), difficulty=0.4,
)


# ═════════════════════════════════════════════════════════════════════════════
#  value_remap — an accepted value changed meaning; the old spelling is wrong
# ═════════════════════════════════════════════════════════════════════════════

FILL_METHOD_REMAP = _probe(
    id="fill_method_remap", family="value_remap", category="numeric",
    summary='fill_gaps(method="forward") now fills from the NEXT reading.',
    fn="fill_gaps", signature='fill_gaps(values, method="zero")',
    impl='''
    def fill_gaps(values, method="zero"):
        """Replace missing (null) readings.

        method="zero" (default) — missing readings become 0
        method="carry"          — the most recent earlier reading is carried forward
        method="forward"        — the next later reading is pulled back (looks forward)
        """
        out = list(values)
        if method == "carry":
            last = None
            for i, v in enumerate(out):
                if v is None:
                    out[i] = last
                else:
                    last = v
        elif method == "forward":
            nxt = None
            for i in range(len(out) - 1, -1, -1):
                if out[i] is None:
                    out[i] = nxt
                else:
                    nxt = out[i]
        else:
            out = [0 if v is None else v for v in out]
        return out
    ''',
    api_doc='`fill_gaps(values, method="zero")` — replace missing readings. `method` is '
            '`"zero"` (default), `"carry"` (carry the most recent earlier reading) or '
            '`"forward"` (use the next later reading).',
    changelog='**`fill_gaps` — fill method names were redefined.** In prior releases the '
              'method named after the fill direction carried the last known reading '
              'forward, like pandas `ffill`. That name now fills each gap from the next '
              'reading instead. Carrying earlier readings has its own method — consult the '
              'function signature for the full list.',
    param="method", gold_kwargs={"method": "carry"}, familiar_kwargs={"method": "forward"},
    familiar_behaviour='"forward" carries the previous reading', installed_behaviour='"forward" uses the next reading',
    task_clause="Fill each missing (null) reading in `readings` with the most recent earlier "
                "reading (a forward fill). Write the filled list under `filled`.",
    output_key="filled", input_payload={"readings": [5, None, None, 8, None, 3]},
    tags=("missing-data", "timeseries"), difficulty=0.8,
)

LEVEL_FILTER_REMAP = _probe(
    id="level_filter_remap", family="value_remap", category="text",
    summary='filter_level(level="warning") now keeps ONLY warnings.',
    fn="filter_level", signature='filter_level(entries, level="info+")',
    impl='''
    def filter_level(entries, level="info+"):
        """Keep log entries ("LEVEL message") by severity.

        level="<name>"  — only entries of exactly that level
        level="<name>+" — entries of that level or more severe
        Levels, least to most severe: debug, info, warning, error, critical.
        """
        order = ["debug", "info", "warning", "error", "critical"]
        plus = level.endswith("+")
        name = level.rstrip("+")
        out = []
        for e in entries:
            lv = e.split(" ", 1)[0].lower()
            if (plus and order.index(lv) >= order.index(name)) or (not plus and lv == name):
                out.append(e)
        return out
    ''',
    api_doc='`filter_level(entries, level="info+")` — filter `"LEVEL message"` entries. '
            '`level="<name>"` keeps exactly that level; `level="<name>+"` keeps that level '
            'and anything more severe (debug < info < warning < error < critical).',
    changelog='**`filter_level` — level thresholds were redefined.** In prior releases a '
              'bare level name was a minimum severity and kept that level and everything '
              'above it. A bare name now keeps only that exact level. Minimum-severity '
              'filtering has its own spelling — consult the function signature.',
    param="level", gold_kwargs={"level": "warning+"}, familiar_kwargs={"level": "warning"},
    familiar_behaviour='"warning" keeps warning and above', installed_behaviour='"warning" keeps only warnings',
    task_clause="Keep the entries of `entries` whose severity is WARNING or higher (WARNING, "
                "ERROR or CRITICAL), in their original order. Write them under `alerts`.",
    output_key="alerts",
    input_payload={"entries": ["INFO service started", "WARNING disk 91% full",
                               "DEBUG cache miss", "ERROR db timeout after 30s",
                               "CRITICAL out of memory"]},
    tags=("logging", "severity"), difficulty=0.7,
)

VERSION_SORT_REMAP = _probe(
    id="version_sort_remap", family="value_remap", category="collection",
    summary='sort_versions(mode="natural") is now plain string order.',
    fn="sort_versions", signature='sort_versions(versions, mode="lexical")',
    impl='''
    def sort_versions(versions, mode="lexical"):
        """Sort version strings, oldest first.

        mode="lexical" (default) — plain string comparison
        mode="natural"           — alias of "lexical"
        mode="semver"            — dot-separated parts compared as numbers
        """
        if mode == "semver":
            return sorted(versions, key=lambda v: [int(p) for p in v.split(".")])
        return sorted(versions)
    ''',
    api_doc='`sort_versions(versions, mode="lexical")` — sort version strings. `mode` is '
            '`"lexical"` (default), `"natural"` (alias of lexical) or `"semver"` (parts '
            'compared as numbers).',
    changelog='**`sort_versions` — sort modes were redefined.** In prior releases the '
              '"natural" mode compared each dot-separated part as a number. It is now an '
              'alias of plain string ordering. Numeric comparison has its own mode — '
              'consult the function signature.',
    param="mode", gold_kwargs={"mode": "semver"}, familiar_kwargs={"mode": "natural"},
    familiar_behaviour='"natural" compares parts numerically', installed_behaviour='"natural" is string order',
    task_clause="Sort `versions` from oldest to newest, comparing each dot-separated part as "
                "a number (so 1.10.0 comes after 1.9.2). Write them under `ordered`.",
    output_key="ordered",
    input_payload={"versions": ["1.10.0", "1.2.3", "1.9.2", "2.0.0", "1.2.10"]},
    tags=("versions", "sorting"), difficulty=0.7,
)

WHITESPACE_MODE_REMAP = _probe(
    id="whitespace_mode_remap", family="value_remap", category="text",
    summary='normalize_ws(mode="trim") now collapses inner whitespace instead of stripping ends.',
    fn="normalize_ws", signature='normalize_ws(texts, mode="collapse")',
    impl='''
    def normalize_ws(texts, mode="collapse"):
        """Normalise whitespace in each text.

        mode="collapse" (default) — every run of whitespace becomes one space
        mode="trim"               — alias of "collapse"
        mode="strip"              — leading and trailing whitespace removed; inside untouched
        """
        import re as _re
        if mode == "strip":
            return [t.strip() for t in texts]
        return [_re.sub(r"\\s+", " ", t) for t in texts]
    ''',
    api_doc='`normalize_ws(texts, mode="collapse")` — normalise whitespace. `mode` is '
            '`"collapse"` (default, runs become one space), `"trim"` (alias of collapse) '
            'or `"strip"` (remove leading and trailing whitespace only).',
    changelog='**`normalize_ws` — whitespace modes were redefined.** In prior releases the '
              '"trim" mode removed leading and trailing whitespace. It is now an alias of '
              'collapsing whitespace runs. Removing only the ends has its own mode — consult '
              'the function signature.',
    param="mode", gold_kwargs={"mode": "strip"}, familiar_kwargs={"mode": "trim"},
    familiar_behaviour='"trim" strips the ends', installed_behaviour='"trim" collapses runs',
    task_clause="Remove leading and trailing whitespace from each entry of `texts`, leaving "
                "the inside of each entry unchanged. Write the results under `cleaned`.",
    output_key="cleaned",
    input_payload={"texts": ["  hello   world ", "\tid:  42\n", "ok"]},
    tags=("text", "whitespace"), difficulty=0.7,
)

SHARE_SCALE_REMAP = _probe(
    id="share_scale_remap", family="value_remap", category="numeric",
    summary='proportions(scale="percent") now returns 0-1 fractions.',
    fn="proportions", signature='proportions(counts, scale="fraction")',
    impl='''
    def proportions(counts, scale="fraction"):
        """Share of the total for each named count, rounded to 4 decimals.

        scale="fraction" (default) — shares between 0 and 1
        scale="percent"            — alias of "fraction"
        scale="points"             — shares between 0 and 100
        """
        total = sum(counts.values())
        k = 100.0 if scale == "points" else 1.0
        return {n: round(c * k / total, 4) for n, c in counts.items()}
    ''',
    api_doc='`proportions(counts, scale="fraction")` — share of the total per name. '
            '`scale` is `"fraction"` (default, 0–1), `"percent"` (alias of fraction) or '
            '`"points"` (0–100).',
    changelog='**`proportions` — scale names were redefined.** In prior releases the '
              '"percent" scale returned shares between 0 and 100. It is now an alias of '
              'the 0–1 fraction scale. Shares out of 100 have their own scale — consult the '
              'function signature.',
    param="scale", gold_kwargs={"scale": "points"}, familiar_kwargs={"scale": "percent"},
    familiar_behaviour='"percent" is 0-100', installed_behaviour='"percent" is 0-1',
    task_clause="For each entry of `counts`, write its share of the total as a percentage "
                "between 0 and 100 under `shares`.",
    output_key="shares",
    input_payload={"counts": {"chrome": 620, "safari": 250, "firefox": 130}},
    tags=("statistics", "percent"), difficulty=0.7,
)

CAMEL_STYLE_REMAP = _probe(
    id="camel_style_remap", family="value_remap", category="text",
    summary='case_convert(style="camel") now produces UpperCamelCase.',
    fn="case_convert", signature='case_convert(names, style="snake")',
    impl='''
    def case_convert(names, style="snake"):
        """Convert snake_case identifiers.

        style="snake" (default) — unchanged
        style="camel"           — UpperCamelCase (PascalCase): user_id -> UserId
        style="lower_camel"     — lowerCamelCase: user_id -> userId
        """
        out = []
        for n in names:
            parts = n.split("_")
            if style == "camel":
                out.append("".join(p.capitalize() for p in parts))
            elif style == "lower_camel":
                out.append(parts[0] + "".join(p.capitalize() for p in parts[1:]))
            else:
                out.append(n)
        return out
    ''',
    api_doc='`case_convert(names, style="snake")` — convert snake_case names. `style` is '
            '`"snake"` (default), `"camel"` (UpperCamelCase, `UserId`) or `"lower_camel"` '
            '(`userId`).',
    changelog='**`case_convert` — style names were redefined.** In prior releases the '
              '"camel" style produced camelCase with a lowercase first letter. It now '
              'produces UpperCamelCase. The lowercase-first form has its own style — '
              'consult the function signature.',
    param="style", gold_kwargs={"style": "lower_camel"}, familiar_kwargs={"style": "camel"},
    familiar_behaviour='"camel" is lowerCamelCase', installed_behaviour='"camel" is UpperCamelCase',
    task_clause="Convert each snake_case field name in `fields` to camelCase with a lowercase "
                "first letter (`user_id` → `userId`). Write them under `jsonFields`.",
    output_key="jsonFields",
    input_payload={"fields": ["user_id", "created_at", "is_active_member"]},
    tags=("naming", "json"), difficulty=0.7,
)


EXTENDED_PROBES: tuple[Probe, ...] = (
    TO_SECONDS_UNIT, PERCENTILE_METHOD, PAGE_NUMBERING, AVERAGE_NULLS, CSV_HEADER,
    SLUG_SEPARATOR, UNIQUE_ORDER, MEDIAN_EVEN, WEEK_START, WRAP_LONG_WORDS, NAME_CASE,
    CSV_QUOTES, RUNNING_TOTAL_MODE, DAY_COUNT, KV_WHITESPACE, BLANK_LINES,
    FLATTEN_SEPARATOR,
    FILL_METHOD_REMAP, LEVEL_FILTER_REMAP, VERSION_SORT_REMAP, WHITESPACE_MODE_REMAP,
    SHARE_SCALE_REMAP, CAMEL_STYLE_REMAP,
)

EXTENDED_BY_ID = {p.id: p for p in EXTENDED_PROBES}
