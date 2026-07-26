"""Deep backend grading — execution verifiers for backend probes.

Each verifier dynamically executes the probe's ``impl`` source under both
gold and familiar parameter sets, then compares the agent's output against
the real execution results.  For the Spring Boot probe, ``classpath`` is a
set — the verifier handles the set→list round-trip that JSON serialisation
would cause.

Usage::

    from priorlock.cartridges.deep_backend import run_all_deep_checks
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

def verify_django_queryset_eval(agent_output: Any) -> tuple[bool, str]:
    """Execute django_query with both param sets and compare."""
    from .backend import DJANGO_QUERYSET_EVAL as P

    fn = _exec_impl(P.impl, P.fn)
    records = P.input_payload["records"]
    filters = P.input_payload["filters"]

    gold = fn(records, filters, **P.gold_kwargs)
    familiar = fn(records, filters)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_flask_route_types(agent_output: Any) -> tuple[bool, str]:
    """Execute flask_route with both param sets and compare."""
    from .backend import FLASK_ROUTE_TYPES as P

    fn = _exec_impl(P.impl, P.fn)
    path = P.input_payload["path"]
    params = P.input_payload["params"]

    gold = fn(path, params, **P.gold_kwargs)
    familiar = fn(path, params)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_fastapi_response_model(agent_output: Any) -> tuple[bool, str]:
    """Execute fastapi_serialize with both param sets and compare."""
    from .backend import FASTAPI_RESPONSE_MODEL as P

    fn = _exec_impl(P.impl, P.fn)
    data = P.input_payload["data"]
    model_fields = P.input_payload["model_fields"]

    gold = fn(data, model_fields, **P.gold_kwargs)
    familiar = fn(data, model_fields)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_express_middleware_order(agent_output: Any) -> tuple[bool, str]:
    """Execute express_middleware with both param sets and compare."""
    from .backend import EXPRESS_MIDDLEWARE_ORDER as P

    fn = _exec_impl(P.impl, P.fn)
    middlewares = P.input_payload["middlewares"]
    request = P.input_payload["request"]

    gold = fn(middlewares, request, **P.gold_kwargs)
    familiar = fn(middlewares, request)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_springboot_auto_config(agent_output: Any) -> tuple[bool, str]:
    """Execute springboot_config with both param sets and compare.

    Note: classpath is a set in input_payload but the impl accepts sets,
    so we pass it directly.
    """
    from .backend import SPRINGBOOT_AUTO_CONFIG as P

    fn = _exec_impl(P.impl, P.fn)
    beans = P.input_payload["beans"]
    classpath = P.input_payload["classpath"]

    gold = fn(beans, classpath, **P.gold_kwargs)
    familiar = fn(beans, classpath, **P.familiar_kwargs)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_django_csrf_mode(agent_output: Any) -> tuple[bool, str]:
    """Execute django_csrf with both param sets and compare."""
    from .backend import DJANGO_CSRF_MODE as P

    fn = _exec_impl(P.impl, P.fn)
    views = P.input_payload["views"]

    gold = fn(views, **P.gold_kwargs)
    familiar = fn(views, **P.familiar_kwargs)

    if agent_output == gold:
        return True, f"matches executed gold: {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (prior-locked): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


def verify_fastapi_dependency_scope(agent_output: Any) -> tuple[bool, str]:
    """Execute fastapi_depends and compare full vs stripped output."""
    from .backend import FASTAPI_DEPENDENCY_SCOPE as P

    fn = _exec_impl(P.impl, P.fn)
    dependencies = P.input_payload["dependencies"]
    request_id = P.input_payload["request_id"]

    gold = fn(dependencies, request_id)  # result_shape: no kwargs difference
    # Familiar is the stripped version (no scope/instance_id)
    familiar = [{"name": r["name"], "factory": r["factory"]} for r in gold]

    if agent_output == gold:
        return True, f"matches executed gold (full scope shape): {gold}"
    if agent_output == familiar:
        return False, f"matches familiar (stripped, no scope): {familiar}"
    return False, f"matches neither. executed gold={gold}, familiar={familiar}"


# ─── Registry ───────────────────────────────────────────────────────────────

DEEP_VERIFIERS: dict[str, Any] = {
    "django_queryset_eval": verify_django_queryset_eval,
    "flask_route_types": verify_flask_route_types,
    "fastapi_response_model": verify_fastapi_response_model,
    "express_middleware_order": verify_express_middleware_order,
    "springboot_auto_config": verify_springboot_auto_config,
    "django_csrf_mode": verify_django_csrf_mode,
    "fastapi_dependency_scope": verify_fastapi_dependency_scope,
}


def attach_deep_grading() -> None:
    """Patch backend cartridge probes with execution-backed deep verification."""
    from . import get
    spec = get("backend")
    for probe in spec.probes:
        if probe.id in DEEP_VERIFIERS:
            object.__setattr__(probe, "_deep_verifier", DEEP_VERIFIERS[probe.id])


def deep_verify(probe_id: str, agent_output: Any) -> tuple[bool, str]:
    """Run the deep verifier for a backend probe."""
    if probe_id not in DEEP_VERIFIERS:
        raise KeyError(f"no deep verifier for probe {probe_id!r}")
    return DEEP_VERIFIERS[probe_id](agent_output)


def run_all_deep_checks() -> dict[str, tuple[bool, str]]:
    """Run every deep verifier with gold_output. For CI validation."""
    from . import get
    spec = get("backend")
    results = {}
    for probe in spec.probes:
        if probe.id in DEEP_VERIFIERS:
            passed, detail = DEEP_VERIFIERS[probe.id](probe.gold_output)
            results[probe.id] = (passed, detail)
    return results
