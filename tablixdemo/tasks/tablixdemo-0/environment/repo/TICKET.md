# TICKET TX-001: Sales Summary Report

Implement `run(data_dir, out_path)` in `src/pipeline.py` using the **INSTALLED**
tablix library (v1.4).  The docs in `docs/` are authoritative for this version
and may differ from tablix versions you know.  A competent engineer can solve
this from this ticket plus `docs/` alone.

## Input

`data_dir` contains `transactions.csv` with fields:
- `id` (int): unique transaction identifier
- `product` (str): product name
- `category` (str): product category (may be empty)
- `amount` (float): transaction amount in USD

## Output

Write a JSON object to `out_path` with exactly these keys:

- `categorySales` (dict): total `amount` per category group, using tablix's
  grouping semantics (see docs/api_reference.md and docs/CHANGELOG.md).
  Keys are category names as returned by `tablix.group_by`.

- `categoryCount` (dict): number of records per category group, using the
  same grouping semantics as `categorySales`.

- `topProductIds` (list[int]): IDs of the top-3 products by `amount`,
  sorted ascending, using tablix's `top_n` with n=3.  Note: the list length
  may differ from 3 depending on the installed version's tie behavior.

## Rules

- Edit ONLY `src/pipeline.py`.
- Do not modify `tests/`, `data/`, `docs/`, or the installed tablix package.
- Grading restores canonical tablix and data; visible tests are a smoke check
  only — passing them does not guarantee full correctness.
