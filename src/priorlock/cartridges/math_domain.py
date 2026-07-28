"""Math domain cartridge — prior override on a synthetic mathematical
operations library covering linear algebra, trigonometry, and descriptive
statistics idioms that LLMs have strong memorized priors about (e.g. row-major
matrix multiplication, degrees as the default angle unit, Euclidean norm as
"the" norm, and variance returning a single scalar).
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register, SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

MATRIX_MULTIPLY_ORDER = Probe(
    id="matrix_multiply_order",
    family="default_flip",
    category="linear_algebra",
    summary="math_matmul() now multiplies in column-major order by default "
            "instead of row-major.",
    fn="math_matmul",
    signature='math_matmul(a, b, order="column")',
    impl='''
def math_matmul(a, b, order="column"):
    """Multiply two square matrices *a* and *b*.

    order="column" (default) — column-major multiplication:
                                result[i][j] = sum_k a[k][i] * b[j][k]
    order="row"               — standard row-major multiplication:
                                result[i][j] = sum_k a[i][k] * b[k][j]
    """
    n = len(a)
    result = [[0] * n for _ in range(n)]
    if order == "row":
        for i in range(n):
            for j in range(n):
                result[i][j] = sum(a[i][k] * b[k][j] for k in range(n))
    else:
        for i in range(n):
            for j in range(n):
                result[i][j] = sum(a[k][i] * b[j][k] for k in range(n))
    return result
''',
    api_doc='`math_matmul(a, b, order="column")` — multiply two square '
            'matrices `a` and `b`. `order` is `"column"` (default, '
            'column-major multiplication) or `"row"` (standard row-major '
            'multiplication, `result[i][j] = sum_k a[i][k] * b[k][j]`). '
            'Returns the product as a list of row lists.',
    changelog='**`math_matmul` — default `order` changed from `"row"` to '
              '`"column"`.** Prior releases performed standard row-major '
              'matrix multiplication by default. The current release '
              'defaults to column-major multiplication, matching the '
              'storage layout used internally by the new backend. Pass '
              '`order="row"` to restore the old row-major default.',
    param="order",
    gold_kwargs={"order": "row"},
    familiar_kwargs={},
    familiar_behaviour='order defaults to "column" — multiplies in column-major order',
    installed_behaviour='order defaults to "column" — pass "row" to multiply in standard row-major order',
    task_clause="Multiply these two matrices using standard **row-major** "
                "matrix multiplication (the textbook definition, "
                "`result[i][j] = sum_k a[i][k] * b[k][j]`), regardless of "
                "the library's newer default. Write the resulting matrix "
                "under `product`.",
    output_key="product",
    input_payload={"a": [[1, 2], [3, 4]], "b": [[5, 6], [7, 8]]},
    gold_output=[[19, 22], [43, 50]],
    familiar_output=[[23, 31], [34, 46]],
    tags=("matrix", "multiply", "row-major", "column-major"),
    domain="math",
)


ANGLE_UNIT_DEFAULT = Probe(
    id="angle_unit_default",
    family="default_flip",
    category="trigonometry",
    summary="math_trig() (sin/cos/tan) now expects radians by default "
            "instead of degrees.",
    fn="math_trig",
    signature='math_trig(func, value, unit="radians")',
    impl='''
def math_trig(func, value, unit="radians"):
    """Evaluate a trig function on *value*.

    func  — one of "sin", "cos", "tan"
    unit="radians" (default) — value is interpreted as radians
    unit="degrees"           — value is interpreted as degrees and converted
                                to radians before evaluation
    """
    import math

    if unit == "degrees":
        value = math.radians(value)
    fn = {"sin": math.sin, "cos": math.cos, "tan": math.tan}[func]
    return round(fn(value), 6)
''',
    api_doc='`math_trig(func, value, unit="radians")` — evaluate `func` '
            '(`"sin"`, `"cos"`, or `"tan"`) on `value`. `unit` is '
            '`"radians"` (default, `value` interpreted as radians) or '
            '`"degrees"` (`value` interpreted as degrees and converted '
            'before evaluation). Returns the result rounded to 6 places.',
    changelog='**`math_trig` — default `unit` changed from `"degrees"` to '
              '`"radians"`.** Prior releases interpreted the input value as '
              'degrees by default, matching most calculator UIs. The '
              'current release defaults to radians, matching the '
              'mathematical convention used throughout the rest of the '
              'library. Pass `unit="degrees"` to restore the old '
              'degrees-by-default behaviour.',
    param="unit",
    gold_kwargs={"unit": "degrees"},
    familiar_kwargs={},
    familiar_behaviour='unit defaults to "radians" — the value is interpreted as radians',
    installed_behaviour='unit defaults to "radians" — pass "degrees" to interpret the value as degrees',
    task_clause="Evaluate this angle using **degrees** as the input unit "
                "(as this calculator app has always done), regardless of "
                "the library's newer radians-by-default behaviour. Write "
                "the resulting value under `result`.",
    output_key="result",
    input_payload={"func": "sin", "value": 30},
    gold_output=0.5,
    familiar_output=-0.988032,
    tags=("trigonometry", "angle", "radians", "degrees"),
    domain="math",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

NORM_TYPE = Probe(
    id="norm_type",
    family="value_remap",
    category="linear_algebra",
    summary='math_norm() with kind="standard" now computes the L1 norm '
            'instead of the L2 norm.',
    fn="math_norm",
    signature='math_norm(vector, kind="standard")',
    impl='''
def math_norm(vector, kind="standard"):
    """Compute the norm of *vector*.

    kind="standard" (default) — L1 norm: sum of absolute values
    kind="euclidean"          — L2 norm: square root of sum of squares
    """
    if kind == "euclidean":
        return round(sum(x ** 2 for x in vector) ** 0.5, 6)
    return round(float(sum(abs(x) for x in vector)), 6)
''',
    api_doc='`math_norm(vector, kind="standard")` — compute the norm of '
            '`vector`. `kind` is `"standard"` (default, L1 norm — sum of '
            'absolute values) or `"euclidean"` (L2 norm — square root of '
            'the sum of squares).',
    changelog='**`math_norm` — the meaning of `kind="standard"` changed.** '
              'Prior releases used `kind="standard"` (the default) to mean '
              'the Euclidean (L2) norm, the most common notion of vector '
              'length. The current release repurposes `kind="standard"` to '
              'compute the L1 (taxicab) norm instead, matching the '
              'library\'s new emphasis on sparse-vector workflows. Pass '
              '`kind="euclidean"` to restore the old L2 behaviour.',
    param="kind",
    gold_kwargs={"kind": "euclidean"},
    familiar_kwargs={"kind": "standard"},
    familiar_behaviour='kind="standard" now computes the L1 norm, but a prior-locked caller still expects the L2 norm',
    installed_behaviour='kind="standard" computes the L1 norm; pass "euclidean" for the L2 norm',
    task_clause="Compute the **Euclidean (L2) norm** of this vector, since "
                "this physics simulation has always measured vector "
                "magnitude that way, regardless of the library's newer "
                "default meaning of `kind=\"standard\"`. Write the "
                "resulting value under `norm`.",
    output_key="norm",
    input_payload={"vector": [3, 4]},
    gold_output=5.0,
    familiar_output=7.0,
    tags=("norm", "vector", "l1", "l2", "euclidean"),
    domain="math",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

STATS_VARIANCE_METHOD = Probe(
    id="stats_variance_method",
    family="result_shape",
    category="statistics",
    summary="math_variance() now returns a breakdown dict of "
            "sample/population/std_dev instead of a flat float.",
    fn="math_variance",
    signature="math_variance(data)",
    impl='''
def math_variance(data):
    """Compute variance statistics for *data*.

    Returns {"sample": float, "population": float, "std_dev": float}, each
    rounded to 6 places. "sample" divides by (n - 1); "population" divides
    by n; "std_dev" is the square root of the population variance.
    """
    n = len(data)
    mean = sum(data) / n
    sq_diffs = [(x - mean) ** 2 for x in data]
    pop_var = sum(sq_diffs) / n
    sample_var = sum(sq_diffs) / (n - 1) if n > 1 else 0.0
    std_dev = pop_var ** 0.5
    return {
        "sample": round(sample_var, 6),
        "population": round(pop_var, 6),
        "std_dev": round(std_dev, 6),
    }
''',
    api_doc='`math_variance(data)` — compute variance statistics for '
            '`data`. Returns `{"sample": float, "population": float, '
            '"std_dev": float}`, each rounded to 6 places. `sample` divides '
            'by `(n - 1)`; `population` divides by `n`; `std_dev` is the '
            'square root of the population variance.',
    changelog='**`math_variance` — return shape changed.** Prior releases '
              'returned a single flat float — the population variance. The '
              'current release returns a breakdown dict `{"sample", '
              '"population", "std_dev"}` so callers no longer need to '
              'derive the sample variance and standard deviation '
              'themselves. There is no flag to restore the old flat-float '
              'shape — callers that need just the population variance '
              'must read it from the dict.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="returns a single flat float (the population variance)",
    installed_behaviour="returns a breakdown dict with sample/population/std_dev",
    task_clause="Using the library's `math_variance` helper, compute this "
                "dataset's variance statistics exactly as the installed "
                "function returns them — do not flatten or reshape the "
                "result to a single number. Write the resulting value "
                "under `variance`.",
    output_key="variance",
    input_payload={"data": [2, 4, 4, 4, 5, 5, 7, 9]},
    gold_output={"sample": 4.571429, "population": 4.0, "std_dev": 2.0},
    familiar_output=4.0,
    tags=("variance", "statistics", "sample", "population", "std-dev"),
    domain="math",
)


MATH_PROBES = (
    MATRIX_MULTIPLY_ORDER,
    ANGLE_UNIT_DEFAULT,
    NORM_TYPE,
    STATS_VARIANCE_METHOD,
)

CATEGORIES = ("linear_algebra", "trigonometry", "statistics", "arithmetic")

LEXICON = {
    "linear_algebra": {
        "matrix": 2.5, "matrices": 2.5, "vector": 2.0, "norm": 2.0,
        "multiply": 1.5, "multiplication": 1.5, "row-major": 2.0,
        "column-major": 2.0, "euclidean": 1.5, "l1": 1.0, "l2": 1.0,
    },
    "trigonometry": {
        "sin": 2.0, "cos": 2.0, "tan": 2.0, "angle": 2.5, "degrees": 2.0,
        "radians": 2.0, "trig": 1.5, "trigonometry": 1.5,
    },
    "statistics": {
        "variance": 2.5, "standard deviation": 2.0, "std dev": 2.0,
        "sample": 1.5, "population": 1.5, "mean": 1.0, "dataset": 1.0,
    },
    "arithmetic": {
        "sum": 1.5, "difference": 1.5, "product": 1.5, "quotient": 1.5,
        "calculate": 1.0, "compute": 1.0, "arithmetic": 2.0,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="math",
    display_name="Mathematical Operations API",
    description="Prior override on a synthetic mathematical operations "
                "library — matrix multiplication order, trig angle-unit "
                "defaults, vector norm semantics, and variance reporting "
                "idioms that LLMs have strong memorized priors about.",
    probes=MATH_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    information_sources=(SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE),
    max_level=1,
)

register(CARTRIDGE)
