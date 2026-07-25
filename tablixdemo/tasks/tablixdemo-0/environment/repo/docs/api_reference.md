# tablix 1.4 API Reference

## tablix.load_csv(path) → list[dict]

Load a CSV file at *path* and return a list of row dicts.  All values are
strings; cast to numeric types as needed.

## tablix.group_by(records, key) → dict[str, list[dict]]

Group *records* by the value of field *key*.

Records where `records[key]` is `None`, absent, or an empty string are
collected under the key `"__missing__"`.  This group always appears in the
output when such records exist.

```python
groups = tablix.group_by(records, "category")
# groups may include {"__missing__": [...], "Electronics": [...], ...}
```

## tablix.sum_field(records, field) → float

Return the sum of numeric field *field* across all *records*.

## tablix.top_n(records, n, key, reverse=True) → list[dict]

Return the top-*n* records by numeric field *key* (descending by default).

**Tie behavior**: when multiple records share the value at position *n*, ALL
of them are included.  The returned list may contain more than *n* items.

```python
# If 3rd and 4th place both have amount=200.0, both are returned:
top = tablix.top_n(records, 3, "amount")  # may return 4+ records
```

## tablix.sort_records(records, key, reverse=False) → list[dict]

Sort *records* by *key*.  Ties broken by the record `id` field descending
(highest id first).
