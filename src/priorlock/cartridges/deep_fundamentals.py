"""Deep fundamentals grading — execution verifiers for fundamentals probes.

Each verifier dynamically executes the probe's ``impl`` source under both
gold and familiar parameter sets, then compares the agent's output against
the real execution results.  This catches any drift between the statically
declared gold/familiar outputs and what the code actually produces.

Usage::

    from priorlock.cartridges.deep_fundamentals import run_all_deep_checks
    results = run_all_deep_checks()   # {probe_id: (passed, detail)}
"""
from __future__ import annotations

from typing import Any


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _exec_impl(impl_src: str, fn_name: str) -> Any:
    """Compile an impl source block and return the callable."""
    ns: dict[str, Any] = {}
    exec(impl_src, ns)
    return ns[fn_name]


# ─── Verifiers ───────────────────────────────────────────────────────────────

def verify_range_start_index(agent_output: Any) -> tuple[bool, str]:
    """Execute arange with both param sets and compare."""
    from .fundamentals import RANGE_START_INDEX as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    gold = fn(inp["n"], **P.gold_kwargs)
    familiar = fn(inp["n"])

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. gold={gold}, familiar={familiar}"


def verify_slice_end_mode(agent_output: Any) -> tuple[bool, str]:
    """Execute getslice with both param sets and compare."""
    from .fundamentals import SLICE_END_MODE as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    gold = fn(inp["items"], inp["start"], inp["stop"], **P.gold_kwargs)
    familiar = fn(inp["items"], inp["start"], inp["stop"])

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. gold={gold}, familiar={familiar}"


def verify_empty_string_truthy(agent_output: Any) -> tuple[bool, str]:
    """Execute is_truthy with both param sets and compare."""
    from .fundamentals import EMPTY_STRING_TRUTHY as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    gold = fn(inp["values"], **P.gold_kwargs)
    familiar = fn(inp["values"])

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. gold={gold}, familiar={familiar}"


def verify_int_division_mode(agent_output: Any) -> tuple[bool, str]:
    """Execute intdiv with both param sets and compare."""
    from .fundamentals import INT_DIVISION_MODE as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    gold = fn(inp["a"], inp["b"], **P.gold_kwargs)
    familiar = fn(inp["a"], inp["b"])

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. gold={gold}, familiar={familiar}"


def verify_sort_stability(agent_output: Any) -> tuple[bool, str]:
    """Execute sorted_by with both param sets and compare."""
    from .fundamentals import SORT_STABILITY as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    gold = fn(inp["records"], inp["key"], **P.gold_kwargs)
    familiar = fn(inp["records"], inp["key"])

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. gold={gold}, familiar={familiar}"


def verify_dict_merge_winner(agent_output: Any) -> tuple[bool, str]:
    """Execute update with both param sets and compare."""
    from .fundamentals import DICT_MERGE_WINNER as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    gold = fn(inp["base"], inp["patch"], **P.gold_kwargs)
    familiar = fn(inp["base"], inp["patch"], **P.familiar_kwargs)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. gold={gold}, familiar={familiar}"


def verify_modulo_sign(agent_output: Any) -> tuple[bool, str]:
    """Execute mod with both param sets and compare."""
    from .fundamentals import MODULO_SIGN as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    gold = fn(inp["a"], inp["b"], **P.gold_kwargs)
    familiar = fn(inp["a"], inp["b"], **P.familiar_kwargs)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. gold={gold}, familiar={familiar}"


def verify_mutable_default(agent_output: Any) -> tuple[bool, str]:
    """Execute filled with both param sets and compare."""
    from .fundamentals import MUTABLE_DEFAULT as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    gold = fn(inp["items"], **P.gold_kwargs)
    familiar = fn(inp["items"], **P.familiar_kwargs)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. gold={gold}, familiar={familiar}"


def verify_zero_is_value(agent_output: Any) -> tuple[bool, str]:
    """Execute first and compare result shape."""
    from .fundamentals import ZERO_IS_VALUE as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    # The predicate is described as "item >= 0"
    gold = fn(inp["items"], lambda x: x >= 0)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output is None or agent_output == P.familiar_output:
        return False, f"matches familiar (prior-locked): used 0 as sentinel or returned None"
    return False, f"matches neither. gold={gold}, agent={agent_output}"


def verify_string_concat_result(agent_output: Any) -> tuple[bool, str]:
    """Execute join and compare result shape."""
    from .fundamentals import STRING_CONCAT_RESULT as P

    fn = _exec_impl(P.impl, P.fn)
    inp = P.input_payload

    gold = fn(inp["parts"], inp["sep"])

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == P.familiar_output:
        return False, f"matches familiar (prior-locked): returned single string"
    return False, f"matches neither. gold={gold}, agent={agent_output}"


# ─── Registry ───────────────────────────────────────────────────────────────

_VERIFIERS = {
    "range_start_index":   verify_range_start_index,
    "slice_end_mode":      verify_slice_end_mode,
    "empty_string_truthy": verify_empty_string_truthy,
    "int_division_mode":   verify_int_division_mode,
    "sort_stability":      verify_sort_stability,
    "dict_merge_winner":   verify_dict_merge_winner,
    "modulo_sign":         verify_modulo_sign,
    "mutable_default":     verify_mutable_default,
    "zero_is_value":       verify_zero_is_value,
    "string_concat_result": verify_string_concat_result,
}


def attach_deep_grading(probe_id: str) -> bool:
    """Return True if a deep verifier exists for *probe_id*."""
    return probe_id in _VERIFIERS


def deep_verify(probe_id: str, agent_output: Any) -> tuple[bool, str]:
    """Run the deep verifier for *probe_id*, returning (passed, detail)."""
    if probe_id not in _VERIFIERS:
        return False, f"no deep verifier for {probe_id}"
    return _VERIFIERS[probe_id](agent_output)


def run_all_deep_checks() -> dict[str, tuple[bool, str]]:
    """Run every verifier against its probe's gold_output. All should PASS."""
    from .fundamentals import FUNDAMENTALS_PROBES

    results: dict[str, tuple[bool, str]] = {}
    for p in FUNDAMENTALS_PROBES:
        if p.id in _VERIFIERS:
            passed, detail = _VERIFIERS[p.id](p.gold_output)
            results[p.id] = (passed, detail)
    return results
