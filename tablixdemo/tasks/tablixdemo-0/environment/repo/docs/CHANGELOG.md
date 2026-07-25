# tablix CHANGELOG

## v1.4 (current, installed)

### Breaking Changes

**group_by: null and empty keys now map to `"__missing__"` group**

In v1.3, records whose grouping-key field was `None` or an empty string were
silently excluded from the output.  In v1.4 these records are collected under
the special group key `"__missing__"`.  The `"__missing__"` group key always
appears in the output dict whenever such records exist.

Migration: code that assumed only non-null key values appear in `group_by`
output must now handle `"__missing__"`.  Do not filter it out before passing
to downstream aggregation — it represents real data.

**top_n: tie-inclusive return at position n**

In v1.3, `top_n(records, n, key)` returned exactly `n` records (or fewer if
the list is shorter): the first `n` in sorted order, cutting arbitrarily when
values tied at the boundary.

In v1.4, all records tied at position `n` are included.  The returned list
length may exceed `n` when a tie exists at the boundary.

Migration: do not assume `len(top_n(records, n, key)) == n`.  If you need
exactly `n` items and ties are possible, sort and slice manually after calling
`top_n`.

## v1.3

Initial public release.  Established core API: `load_csv`, `group_by`,
`sum_field`, `top_n`, `sort_records`.
