"""Deep frontend grading — execution verifiers for frontend probes.

Each verifier dynamically executes the probe's ``impl`` source under both
gold and familiar parameter sets, then compares the agent's output against
the real execution results.  This catches any drift between the statically
declared gold/familiar outputs and what the code actually produces.

Usage::

    from priorlock.cartridges.deep_frontend import run_all_deep_checks
    results = run_all_deep_checks()   # {probe_id: (passed, detail)}
"""
from __future__ import annotations

import hashlib
from typing import Any


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _exec_impl(impl_src: str, fn_name: str) -> Any:
    """Compile an impl source block and return the callable."""
    ns: dict[str, Any] = {}
    exec(impl_src, ns)
    return ns[fn_name]


# ─── Verifiers ───────────────────────────────────────────────────────────────

def verify_react_use_effect_cleanup(agent_output: Any) -> tuple[bool, str]:
    """Execute react_use_effect with both param sets and compare."""
    from .frontend import REACT_USE_EFFECT_CLEANUP as P

    fn = _exec_impl(P.impl, P.fn)

    # effect_fn that returns a cleanup callable
    def effect_fn(i):
        return lambda: None

    deps = P.input_payload["deps"]

    # Gold: cleanup_on_every=False (unmount only)
    gold = fn(effect_fn, deps, **P.gold_kwargs)
    # Familiar: cleanup_on_every=True (installed default)
    familiar = fn(effect_fn, deps)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_nextjs_data_fetch_mode(agent_output: Any) -> tuple[bool, str]:
    """Execute nextjs_get_data with both param sets and compare."""
    from .frontend import NEXTJS_DATA_FETCH_MODE as P

    fn = _exec_impl(P.impl, P.fn)
    pages = P.input_payload["pages"]

    gold = fn(pages, **P.gold_kwargs)
    familiar = fn(pages)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_angular_change_detection(agent_output: Any) -> tuple[bool, str]:
    """Execute ng_component with both param sets and compare."""
    from .frontend import ANGULAR_CHANGE_DETECTION as P

    fn = _exec_impl(P.impl, P.fn)
    components = P.input_payload["components"]

    gold = fn(components, **P.gold_kwargs)
    familiar = fn(components)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_vue_reactivity_mode(agent_output: Any) -> tuple[bool, str]:
    """Execute vue_state with both param sets and compare."""
    from .frontend import VUE_REACTIVITY_MODE as P

    fn = _exec_impl(P.impl, P.fn)
    initial = P.input_payload["initial"]

    gold = fn(initial, **P.gold_kwargs)
    familiar = fn(initial, **P.familiar_kwargs)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_react_key_generation(agent_output: Any) -> tuple[bool, str]:
    """Execute react_list_keys with both param sets and compare."""
    from .frontend import REACT_KEY_GENERATION as P

    fn = _exec_impl(P.impl, P.fn)
    items = P.input_payload["items"]

    gold = fn(items, **P.gold_kwargs)
    familiar = fn(items, **P.familiar_kwargs)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_nextjs_route_convention(agent_output: Any) -> tuple[bool, str]:
    """Execute nextjs_routes and compare full vs stripped output."""
    from .frontend import NEXTJS_ROUTE_CONVENTION as P

    fn = _exec_impl(P.impl, P.fn)
    pages = P.input_payload["pages"]

    gold = fn(pages)  # result_shape: no kwargs difference
    # Familiar is the stripped version (no segments/layout)
    familiar = [{"route": r["route"], "dynamic": r["dynamic"]} for r in gold]

    if agent_output == gold:
        return True, f"matches executed gold (full App Router shape): {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (Pages Router stripped shape): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


# ─── Registry ───────────────────────────────────────────────────────────────

DEEP_VERIFIERS: dict[str, Any] = {
    "react_use_effect_cleanup": verify_react_use_effect_cleanup,
    "nextjs_data_fetch_mode": verify_nextjs_data_fetch_mode,
    "angular_change_detection": verify_angular_change_detection,
    "vue_reactivity_mode": verify_vue_reactivity_mode,
    "react_key_generation": verify_react_key_generation,
    "nextjs_route_convention": verify_nextjs_route_convention,
}


def attach_deep_grading() -> None:
    """Patch frontend cartridge probes with execution-backed deep verification."""
    from . import get
    spec = get("frontend")
    for probe in spec.probes:
        if probe.id in DEEP_VERIFIERS:
            object.__setattr__(probe, "_deep_verifier", DEEP_VERIFIERS[probe.id])


def deep_verify(probe_id: str, agent_output: Any) -> tuple[bool, str]:
    """Run the deep verifier for a frontend probe."""
    if probe_id not in DEEP_VERIFIERS:
        raise KeyError(f"no deep verifier for probe {probe_id!r}")
    return DEEP_VERIFIERS[probe_id](agent_output)


def run_all_deep_checks() -> dict[str, tuple[bool, str]]:
    """Run every deep verifier with gold_output. For CI validation."""
    from . import get
    spec = get("frontend")
    results = {}
    for probe in spec.probes:
        if probe.id in DEEP_VERIFIERS:
            passed, detail = DEEP_VERIFIERS[probe.id](probe.gold_output)
            results[probe.id] = (passed, detail)
    return results
