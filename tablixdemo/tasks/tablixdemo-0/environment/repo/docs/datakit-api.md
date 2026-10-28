# datakit v2.0.0 API

`import datakit`

### `top_k(records, k, key)`

`top_k(records, k, key)` — highest-ranked records by numeric `key`. Tie-inclusive: the result contains every record tied at the cut-off and may therefore be longer than `k`.

### `bucket(records, key, nulls="collect")`

`bucket(records, key, nulls="collect")` — group `records` by `key`. Records whose key is `None` or `""` are collected under `"__unset__"` when `nulls="collect"` (default), or omitted when `nulls="drop"`.

### `merge(base, patch, on_conflict="keep_right")`

`merge(base, patch, on_conflict="keep_right")` — shallow dict merge. `on_conflict` accepts `"keep_right"` (default), `"keep"` (alias for `keep_right`), `"keep_left"`, and `"collect"`.

---

### `version()`

Returns the installed version string.

### `flatten(nested)`

Flattens one level of nesting.

### `pluck(records, field, default=None)`

Extracts `field` from every record.

### `count_by(records, key)`

Maps each distinct `key` value to its occurrence count.
