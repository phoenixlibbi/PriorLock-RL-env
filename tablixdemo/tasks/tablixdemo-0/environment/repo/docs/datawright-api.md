# datawright 2.0.0 — API reference

`import datawright`

## Functions with 2.x behavioural changes

### `top_k(records, k, key)`

`top_k(records, k, key)` — highest-ranked records by numeric `key`. Tie-inclusive: the result contains every record tied at the cut-off and may therefore be longer than `k`.

> Changed in 2.0: result includes every record tied at the cut-off. In 1.x: result is cut to exactly k records.

### `bucket(records, key, nulls="collect")`

`bucket(records, key, nulls="collect")` — group `records` by `key`. Records whose key is `None` or `""` are collected under `"__unset__"` when `nulls="collect"` (default), or omitted when `nulls="drop"`.

> Changed in 2.0: records with a null/empty key land in "__unset__". In 1.x: records with a null/empty key are dropped.

### `merge(base, patch, on_conflict="keep_right")`

`merge(base, patch, on_conflict="keep_right")` — shallow dict merge. `on_conflict` accepts `"keep_right"` (default), `"keep"` (alias for `keep_right`), `"keep_left"`, and `"collect"`.

> Changed in 2.0: "keep" is an alias for keep_right — the patch value wins. In 1.x: "keep" preserves the existing value in base.

## Unchanged utilities

### `version()`

Return the installed version string.

### `flatten(nested)`

Flatten one level of nesting.

### `pluck(records, field, default=None)`

Extract `field` from every record.

### `count_by(records, key)`

Map each distinct `key` value to its occurrence count.
