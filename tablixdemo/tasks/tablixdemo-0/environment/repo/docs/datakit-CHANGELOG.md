# datakit changelog

## 2.0.0

Breaking behavioural changes from the 1.x line. Function signatures are
the same, so old call sites still compile and return the right types, but
some defaults have changed and a few outputs differ.

### `top_k`

**`top_k` — tie-handling behaviour changed.** Prior releases cut the result at exactly `k` records, arbitrarily dropping records tied at the boundary. The current release includes **all** records tied at the cut-off position, so the returned list may be longer than `k`. There is no flag to restore the old truncating behaviour; slice the result yourself if you need a hard cap.

### `bucket`

**`bucket` — default handling of missing keys changed.** Prior releases silently discarded records with a missing or empty group key. The current release collects them under a reserved group name instead. The previous behaviour is still available — consult the function signature for accepted values.

### `merge`

**`merge` — conflict-resolution semantics were redefined.** In prior releases the default conflict strategy preserved the value already present in the base mapping. It now favours the incoming value from the patch. A separate option exists for preserving base values — consult the function signature for the full list of strategies.

## 1.4.3

Doc fixes only.

## 1.4.0

Added `count_by` and `pluck`.
