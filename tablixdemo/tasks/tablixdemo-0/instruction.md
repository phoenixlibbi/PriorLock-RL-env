# Task: Sales Summary Report

Implement `run(data_dir, out_path)` in `src/pipeline.py` using the **INSTALLED**
tablix library.  The docs in `docs/` are authoritative for the installed version
and may differ from tablix versions you know.  A competent engineer can solve
this from this instruction plus `docs/` alone.

## Input

`data_dir` contains `transactions.csv` with fields:
- `id` (int): unique transaction identifier
- `product` (str): product name
- `category` (str): product category (may be empty)
- `amount` (float): transaction amount in USD

## Output

Write a JSON object to `out_path` with exactly these keys:

- `categorySales` (dict): total `amount` per category group, using tablix's
  grouping semantics (see `docs/api_reference.md` and `docs/CHANGELOG.md`).
  Keys are category names as returned by `tablix.group_by`.

- `categoryCount` (dict): number of records per category group, using the
  same grouping semantics as `categorySales`.

- `topProductIds` (list[int]): IDs of the top-3 products by `amount`,
  sorted ascending, using tablix's `top_n` with n=3.  Note: the list length
  may differ from 3 depending on the installed version's tie behavior.

## Rules

- Edit ONLY `src/pipeline.py`.
- Do not modify `tests/`, `data/`, `docs/`, or the installed tablix package.
- You may run `python -m pytest tests/` at any time; passing visible tests does
  not guarantee full correctness — grading uses hidden tests with exact values.
- Grading restores canonical tablix and data before scoring.
<!-- priorlock:begin -->

---

## Data-processing checks

The project ships a utility library, `datakit` (v2).  There are docs in `docs/`.
Write `probe_solution.py` with one public entry point:

```python
def run(data_path, out_path):
    ...
```

`data_path` points to `data/probe_input.json` (JSON, one key per check).
Use `datakit.top_k`, `datakit.bucket`, `datakit.merge` from the library for the checks below — don't rewrite them
by hand. Write your results as a single JSON object to `out_path`, keyed
exactly as listed.

### Checks

1. **`topIds`** — Using the library's `top_k` helper with `k=3` on `amount`, report the `id` of every record it ranks in the top 3. Write the ids sorted ascending under `topIds`.
2. **`bucketCounts`** — Group `records` by `region`, **excluding** any record that has no region. Write a mapping of region name to record count under `bucketCounts`.
3. **`merged`** — Merge `patch` into `base` so that any key **already present in `base` retains its original value**. Write the merged mapping under `merged`.

### Smoke test

`tests/test_probe_visible.py` verifies that your solution runs and that each output key
has the right container type. It doesn't check values, so passing it just
means the plumbing works.

<!-- priorlock:end -->
