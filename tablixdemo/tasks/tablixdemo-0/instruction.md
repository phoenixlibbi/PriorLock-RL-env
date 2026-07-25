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

## Part 2 — `datawright` data checks

This repository bundles **datawright 2.0.0**, a local library that is not
published to any package index. There is no newer release to fetch and no online
documentation. The docs inside this repository are authoritative:

- `docs/datawright-CHANGELOG.md` — behavioural changes in the 2.x line
- `docs/datawright-api.md` — current signatures and argument semantics

`datawright 2.x` changed several **default argument values** and reassigned the
meaning of some **accepted argument values**. No signature changed, so code
written against `datawright 1.x` still runs and still returns the expected types — it
just returns different results. Verify the behaviour you rely on before you rely
on it.

### What to write

Create `probe_solution.py` at the repository root exposing exactly:

```python
def run(data_path, out_path):
    ...
```

- `data_path` is the path to `data/probe_input.json`, a JSON object with one key per check.
- Perform every check below using `datawright.top_k`, `datawright.bucket`, `datawright.merge`. **Do not reimplement these
  functions** — call the bundled library.
- Write a single JSON object to `out_path` with one key per check, using the key
  names given below.

You can produce the file yourself for inspection with:

```bash
cd . && python3 -c "import probe_solution as p; p.run('data/probe_input.json', 'probe_output.json')"
```

### Checks

1. **`topIds`** — Using the library's `top_k` helper with `k=3` on `amount`, report the `id` of every record it ranks in the top 3. Write the ids sorted ascending under `topIds`.
2. **`bucketCounts`** — Group `records` by `region`, **excluding** any record that has no region. Write a mapping of region name to record count under `bucketCounts`.
3. **`merged`** — Merge `patch` into `base` so that any key **already present in `base` retains its original value**. Write the merged mapping under `merged`.

### Verifying your work

`tests/test_probe_visible.py` checks that your solution runs and emits the right container type
under each key. It does **not** check any value — passing it means the plumbing
works, not that the results are correct.

<!-- priorlock:end -->
