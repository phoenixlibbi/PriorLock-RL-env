# datawright changelog

## 2.0.0 — installed

Behavioural changes from the 1.x line. **None of these changed a function
signature**, so 1.x call sites still run without error and return values of
the expected type — they simply return different results. Read this section
before writing any code against the functions listed below.

### `top_k`

**`top_k` is now tie-inclusive.** Prior releases cut the result at exactly `k` records, arbitrarily dropping records tied at the boundary. The current release returns **all** records tied at position `k`, so `len(top_k(records, 3, key))` may be greater than 3. There is no flag to restore the old truncating behaviour; slice the result yourself if you need a hard cap.

### `bucket`

**`bucket` — default `nulls` changed from `"drop"` to `"collect"`.** Prior releases silently discarded records with a missing or empty group key. The current release collects them under the reserved group name `"__unset__"`. Pass `nulls="drop"` to discard them.

### `merge`

**`merge` — `on_conflict="keep"` was redefined.** In prior releases `"keep"` meant *keep the value already present in `base`*. It now means *keep the newer value*, and is an alias for `"keep_right"`. To preserve the value already in `base`, pass `on_conflict="keep_left"`.

## 1.4.3 — previous

Documentation fixes only. No behavioural change.

## 1.4.0 — previous

Added `count_by` and `pluck`.
