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
