"""Backend framework domain cartridge — prior override on synthetic
backend framework helper wrappers.

Seven probes across the three PriorLock families, exercising the parts of
Django, Flask, FastAPI, Express, and Spring Boot semantics that LLMs have
the strongest memorized priors about: Django ORM queryset evaluation,
Flask route parameter types, FastAPI response model serialization,
Express middleware chain ordering, Spring Boot auto-configuration,
Django CSRF enforcement, and FastAPI dependency injection scope.
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register, SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

DJANGO_QUERYSET_EVAL = Probe(
    id="django_queryset_eval",
    family="default_flip",
    category="django",
    summary="django_query() now evaluates lazily by default, returning a queryset descriptor instead of a list.",
    fn="django_query",
    signature="django_query(records, filters, eager=False)",
    impl='''
def django_query(records, filters, eager=False):
    """Simulate Django ORM queryset evaluation.

    records  — list of dicts (model instances)
    filters  — dict of field→value filters

    eager=True  — evaluate immediately, return list of matching records
    eager=False (default) — return a queryset descriptor {"type": "queryset",
                             "sql": ..., "count": ..., "evaluated": False}
    """
    matches = [
        r for r in records
        if all(r.get(k) == v for k, v in filters.items())
    ]
    if eager:
        return matches
    return {
        "type": "queryset",
        "sql": f"SELECT * FROM table WHERE {' AND '.join(f'{k}={v!r}' for k, v in filters.items())}",
        "count": len(matches),
        "evaluated": False,
    }
''',
    api_doc='`django_query(records, filters, eager=False)` — filter `records` by '
            '`filters`. `eager=True` returns the list immediately. '
            '`eager=False` (default) returns a queryset descriptor with SQL, count, '
            'and evaluated=False.',
    changelog='**`django_query` — default `eager` changed from `True` to `False`.** '
              'Prior releases eagerly evaluated the queryset and returned a list '
              'of matching records. The current release returns a lazy queryset '
              'descriptor by default, matching Django\'s actual lazy evaluation. '
              'Pass `eager=True` to force immediate evaluation.',
    param="eager",
    gold_kwargs={"eager": True},
    familiar_kwargs={},
    familiar_behaviour="eager defaults to True — returns list of matching records immediately",
    installed_behaviour="eager defaults to False — returns lazy queryset descriptor",
    task_clause="Filter `records` by `filters`, evaluating the query **eagerly** "
                "to return the matching records as a list. Write the result under `results`.",
    output_key="results",
    input_payload={
        "records": [
            {"id": 1, "status": "active", "role": "admin"},
            {"id": 2, "status": "inactive", "role": "user"},
            {"id": 3, "status": "active", "role": "user"},
        ],
        "filters": {"status": "active"},
    },
    gold_output=[
        {"id": 1, "status": "active", "role": "admin"},
        {"id": 3, "status": "active", "role": "user"},
    ],
    familiar_output={
        "type": "queryset",
        "sql": "SELECT * FROM table WHERE status='active'",
        "count": 2,
        "evaluated": False,
    },
    tags=("django", "orm", "queryset", "lazy-evaluation"),
    domain="backend",
)


FLASK_ROUTE_TYPES = Probe(
    id="flask_route_types",
    family="default_flip",
    category="flask",
    summary="flask_route() now enforces strict type coercion on URL parameters by default.",
    fn="flask_route",
    signature="flask_route(path, params, strict_types=True)",
    impl='''
def flask_route(path, params, strict_types=True):
    """Simulate Flask URL parameter extraction and type coercion.

    path         — route pattern like "/users/<int:id>"
    params       — dict of raw parameter values (all strings from URL)

    strict_types=True  (default) — coerce to declared types; raise on failure
    strict_types=False           — pass all params as raw strings
    """
    import re
    type_specs = dict(re.findall(r"<(\\w+):(\\w+)>", path))
    coerced = {}
    errors = []

    for name, raw_value in params.items():
        if not strict_types or name not in type_specs:
            coerced[name] = raw_value
            continue
        declared = type_specs[name]
        try:
            if declared == "int":
                coerced[name] = int(raw_value)
            elif declared == "float":
                coerced[name] = float(raw_value)
            elif declared == "path":
                coerced[name] = str(raw_value)
            else:
                coerced[name] = raw_value
        except (ValueError, TypeError):
            errors.append({"param": name, "type": declared, "value": raw_value})

    result = {"params": coerced}
    if errors:
        result["errors"] = errors
    return result
''',
    api_doc='`flask_route(path, params, strict_types=True)` — extract and coerce '
            'URL parameters. `strict_types=True` (default) coerces to declared '
            'types. `strict_types=False` passes raw strings.',
    changelog='**`flask_route` — default `strict_types` changed from `False` to '
              '`True`.** Prior releases passed all URL parameters as raw strings, '
              'leaving type coercion to the view function. The current release '
              'automatically coerces parameters to their declared types '
              '(`<int:id>` becomes an int). Pass `strict_types=False` to '
              'restore raw-string behavior.',
    param="strict_types",
    gold_kwargs={"strict_types": False},
    familiar_kwargs={},
    familiar_behaviour="strict_types defaults to False — all params are raw strings",
    installed_behaviour="strict_types defaults to True — params coerced to declared types",
    task_clause="Extract URL parameters from `path` without type coercion, "
                "passing all values as **raw strings**. Write the result under `route`.",
    output_key="route",
    input_payload={
        "path": "/users/<int:id>/posts/<int:page>",
        "params": {"id": "42", "page": "3"},
    },
    gold_output={"params": {"id": "42", "page": "3"}},
    familiar_output={"params": {"id": 42, "page": 3}},
    tags=("flask", "routing", "type-coercion"),
    domain="backend",
)


FASTAPI_RESPONSE_MODEL = Probe(
    id="fastapi_response_model",
    family="default_flip",
    category="fastapi",
    summary="fastapi_serialize() now excludes None fields from response by default.",
    fn="fastapi_serialize",
    signature="fastapi_serialize(data, model_fields, exclude_none=True)",
    impl='''
def fastapi_serialize(data, model_fields, exclude_none=True):
    """Simulate FastAPI response_model serialization.

    data         — dict of response data
    model_fields — list of field names in the response model

    exclude_none=True  (default) — omit fields whose value is None
    exclude_none=False           — include all fields, even if None
    """
    result = {}
    for field in model_fields:
        value = data.get(field)
        if value is None and exclude_none:
            continue
        result[field] = value
    return result
''',
    api_doc='`fastapi_serialize(data, model_fields, exclude_none=True)` — serialize '
            'response data. `exclude_none=True` (default) omits None fields. '
            '`exclude_none=False` includes all model fields.',
    changelog='**`fastapi_serialize` — default `exclude_none` changed from '
              '`False` to `True`.** Prior releases included all model fields in '
              'the response, even those with None values — matching Pydantic v1 '
              'behavior. The current release omits None fields by default, '
              'matching Pydantic v2 conventions. Pass `exclude_none=False` to '
              'restore full-field output.',
    param="exclude_none",
    gold_kwargs={"exclude_none": False},
    familiar_kwargs={},
    familiar_behaviour="exclude_none defaults to False — all fields included, even None",
    installed_behaviour="exclude_none defaults to True — None fields omitted",
    task_clause="Serialize `data` against `model_fields`, including **all fields** "
                "in the response even if their value is None. Write the result "
                "under `response`.",
    output_key="response",
    input_payload={
        "data": {"name": "Alice", "email": "alice@example.com", "bio": None, "avatar": None},
        "model_fields": ["name", "email", "bio", "avatar"],
    },
    gold_output={"name": "Alice", "email": "alice@example.com", "bio": None, "avatar": None},
    familiar_output={"name": "Alice", "email": "alice@example.com"},
    tags=("fastapi", "pydantic", "serialization"),
    domain="backend",
)


EXPRESS_MIDDLEWARE_ORDER = Probe(
    id="express_middleware_order",
    family="default_flip",
    category="express",
    summary="express_middleware() now runs error handlers in registration order by default instead of LIFO.",
    fn="express_middleware",
    signature="express_middleware(middlewares, request, error_order='fifo')",
    impl='''
def express_middleware(middlewares, request, error_order="fifo"):
    """Simulate Express.js middleware chain execution.

    middlewares  — list of {"name": str, "type": "normal"|"error", "transform": str}
    request      — dict representing the request

    error_order="fifo" (default) — error handlers run in registration order (FIFO)
    error_order="lifo"           — error handlers run in reverse order (LIFO)

    Returns {"chain": [names_executed], "request": final_request_state}
    """
    chain = []
    result = dict(request)

    # Run normal middlewares first
    for mw in middlewares:
        if mw["type"] == "normal":
            chain.append(mw["name"])
            if mw.get("transform"):
                result[mw["transform"]] = True

    # Run error handlers
    error_mws = [mw for mw in middlewares if mw["type"] == "error"]
    if error_order == "lifo":
        error_mws = list(reversed(error_mws))

    for mw in error_mws:
        chain.append(mw["name"])
        if mw.get("transform"):
            result[mw["transform"]] = True

    return {"chain": chain, "request": result}
''',
    api_doc='`express_middleware(middlewares, request, error_order="fifo")` — run '
            'middleware chain. `error_order="fifo"` (default) runs error handlers '
            'in registration order. `error_order="lifo"` reverses error handler order.',
    changelog='**`express_middleware` — default `error_order` changed from '
              '`"lifo"` to `"fifo"`.** Prior releases ran error handlers in '
              'reverse registration order (last registered runs first), matching '
              'older Express behavior. The current release runs them in FIFO '
              'order. Pass `error_order="lifo"` to restore reverse ordering.',
    param="error_order",
    gold_kwargs={"error_order": "lifo"},
    familiar_kwargs={},
    familiar_behaviour='error_order defaults to "lifo" — error handlers run in reverse order',
    installed_behaviour='error_order defaults to "fifo" — error handlers run in registration order',
    task_clause="Run the middleware chain on `request`, with error handlers "
                "executing in **reverse registration order** (LIFO). Write the "
                "result under `pipeline`.",
    output_key="pipeline",
    input_payload={
        "middlewares": [
            {"name": "auth", "type": "normal", "transform": "authenticated"},
            {"name": "logger", "type": "normal", "transform": "logged"},
            {"name": "notFound", "type": "error", "transform": "handled_404"},
            {"name": "serverError", "type": "error", "transform": "handled_500"},
        ],
        "request": {"path": "/api/users", "method": "GET"},
    },
    gold_output={
        "chain": ["auth", "logger", "serverError", "notFound"],
        "request": {"path": "/api/users", "method": "GET", "authenticated": True, "logged": True, "handled_404": True, "handled_500": True},
    },
    familiar_output={
        "chain": ["auth", "logger", "notFound", "serverError"],
        "request": {"path": "/api/users", "method": "GET", "authenticated": True, "logged": True, "handled_404": True, "handled_500": True},
    },
    tags=("express", "middleware", "error-handling"),
    domain="backend",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

SPRINGBOOT_AUTO_CONFIG = Probe(
    id="springboot_auto_config",
    family="value_remap",
    category="springboot",
    summary='springboot_config()\'s mode="auto" now means conditional-on-class instead of unconditional.',
    fn="springboot_config",
    signature='springboot_config(beans, classpath, mode="auto")',
    impl='''
def springboot_config(beans, classpath, mode="auto"):
    """Simulate Spring Boot auto-configuration.

    beans       — list of {"name": str, "requires": list[str]} bean definitions
    classpath   — set of available class names

    mode="unconditional" — register all beans regardless of classpath
    mode="conditional"   — only register beans whose requires are all in classpath
    mode="auto" (default) — conditional-on-class (same as "conditional")
    """
    registered = []
    for bean in beans:
        if mode == "unconditional":
            registered.append({"name": bean["name"], "status": "registered"})
        else:
            required = set(bean.get("requires", []))
            if required.issubset(classpath):
                registered.append({"name": bean["name"], "status": "registered"})
            else:
                missing = required - classpath
                registered.append({"name": bean["name"], "status": "skipped",
                                   "missing": sorted(missing)})
    return registered
''',
    api_doc='`springboot_config(beans, classpath, mode="auto")` — simulate '
            'auto-configuration. `mode="unconditional"` registers all beans. '
            '`mode="conditional"` or `mode="auto"` (default) only registers '
            'beans whose required classes are on the classpath.',
    changelog='**`springboot_config` — the `mode="auto"` value now means '
              'conditional-on-class, not unconditional.** Prior releases '
              'treated `"auto"` as unconditional — all beans were registered '
              'regardless of classpath. The current release checks each bean\'s '
              '`requires` list against the classpath. Pass '
              '`mode="unconditional"` to register everything.',
    param="mode",
    gold_kwargs={"mode": "unconditional"},
    familiar_kwargs={"mode": "auto"},
    familiar_behaviour='mode="auto" registers all beans unconditionally',
    installed_behaviour='mode="auto" only registers beans whose requires are satisfied',
    task_clause="Register `beans` **unconditionally** (ignore classpath requirements, "
                "register every bean). Write the list under `config`.",
    output_key="config",
    input_payload={
        "beans": [
            {"name": "DataSource", "requires": ["javax.sql.DataSource", "com.mysql.Driver"]},
            {"name": "WebServer", "requires": ["javax.servlet.Servlet"]},
            {"name": "CacheManager", "requires": ["org.cache.Cache"]},
        ],
        "classpath": {"javax.servlet.Servlet", "javax.sql.DataSource"},
    },
    gold_output=[
        {"name": "DataSource", "status": "registered"},
        {"name": "WebServer", "status": "registered"},
        {"name": "CacheManager", "status": "registered"},
    ],
    familiar_output=[
        {"name": "DataSource", "status": "skipped", "missing": ["com.mysql.Driver"]},
        {"name": "WebServer", "status": "registered"},
        {"name": "CacheManager", "status": "skipped", "missing": ["org.cache.Cache"]},
    ],
    tags=("spring-boot", "auto-configuration", "conditional"),
    domain="backend",
)


DJANGO_CSRF_MODE = Probe(
    id="django_csrf_mode",
    family="value_remap",
    category="django",
    summary='django_csrf()\'s policy="auto" now means per-view enforcement instead of global middleware.',
    fn="django_csrf",
    signature='django_csrf(views, policy="auto")',
    impl='''
def django_csrf(views, policy="auto"):
    """Simulate Django CSRF enforcement across views.

    views  — list of {"name": str, "method": str, "has_token": bool, "exempt": bool}

    policy="global"   — enforce CSRF on all non-exempt POST/PUT/DELETE views
    policy="per-view" — enforce only on views explicitly decorated, skip others
    policy="auto"     (default) — per-view enforcement (same as "per-view")

    Returns list of {"name": str, "allowed": bool, "reason": str}
    """
    results = []
    unsafe_methods = {"POST", "PUT", "DELETE", "PATCH"}

    for view in views:
        method = view["method"].upper()
        if method not in unsafe_methods:
            results.append({"name": view["name"], "allowed": True, "reason": "safe_method"})
            continue

        if view.get("exempt", False):
            results.append({"name": view["name"], "allowed": True, "reason": "exempt"})
            continue

        if policy == "global":
            # Global middleware: all non-exempt unsafe methods need token
            if view.get("has_token", False):
                results.append({"name": view["name"], "allowed": True, "reason": "valid_token"})
            else:
                results.append({"name": view["name"], "allowed": False, "reason": "missing_token"})
        else:
            # Per-view: only enforce if view has csrf_protect decorator (indicated by not being exempt)
            # Without explicit decoration, the view is allowed through
            results.append({"name": view["name"], "allowed": True, "reason": "no_enforcement"})

    return results
''',
    api_doc='`django_csrf(views, policy="auto")` — simulate CSRF enforcement. '
            '`policy="global"` enforces on all unsafe methods. '
            '`policy="per-view"` or `policy="auto"` (default) only enforces on '
            'explicitly decorated views.',
    changelog='**`django_csrf` — the `policy="auto"` value now means per-view '
              'enforcement, not global middleware.** Prior releases applied CSRF '
              'checks to all non-exempt POST/PUT/DELETE views globally. The '
              'current release only enforces on views with explicit `@csrf_protect`. '
              'Pass `policy="global"` for blanket CSRF middleware.',
    param="policy",
    gold_kwargs={"policy": "global"},
    familiar_kwargs={"policy": "auto"},
    familiar_behaviour='policy="auto" enforces CSRF globally on all unsafe methods',
    installed_behaviour='policy="auto" only enforces CSRF on explicitly decorated views',
    task_clause="Enforce CSRF using **global middleware** (all non-exempt unsafe "
                "methods require a valid token). Write the results under `csrf`.",
    output_key="csrf",
    input_payload={
        "views": [
            {"name": "create_post", "method": "POST", "has_token": True, "exempt": False},
            {"name": "delete_user", "method": "DELETE", "has_token": False, "exempt": False},
            {"name": "list_items", "method": "GET", "has_token": False, "exempt": False},
            {"name": "webhook", "method": "POST", "has_token": False, "exempt": True},
        ],
    },
    gold_output=[
        {"name": "create_post", "allowed": True, "reason": "valid_token"},
        {"name": "delete_user", "allowed": False, "reason": "missing_token"},
        {"name": "list_items", "allowed": True, "reason": "safe_method"},
        {"name": "webhook", "allowed": True, "reason": "exempt"},
    ],
    familiar_output=[
        {"name": "create_post", "allowed": True, "reason": "no_enforcement"},
        {"name": "delete_user", "allowed": True, "reason": "no_enforcement"},
        {"name": "list_items", "allowed": True, "reason": "safe_method"},
        {"name": "webhook", "allowed": True, "reason": "exempt"},
    ],
    tags=("django", "csrf", "security", "middleware"),
    domain="backend",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

FASTAPI_DEPENDENCY_SCOPE = Probe(
    id="fastapi_dependency_scope",
    family="result_shape",
    category="fastapi",
    summary="fastapi_depends() now returns scope metadata alongside the resolved dependency.",
    fn="fastapi_depends",
    signature="fastapi_depends(dependencies, request_id)",
    impl='''
def fastapi_depends(dependencies, request_id):
    """Resolve FastAPI dependencies for a request.

    dependencies — list of {"name": str, "factory": str, "cached": bool}
    request_id   — unique request identifier

    Returns resolved dependencies with scope metadata: each entry includes
    "scope" ("request" if cached, "call" otherwise) and "instance_id".
    """
    resolved = []
    cache = {}
    counter = 0

    for dep in dependencies:
        if dep.get("cached") and dep["name"] in cache:
            instance_id = cache[dep["name"]]
        else:
            counter += 1
            instance_id = f"{request_id}:{counter}"
            if dep.get("cached"):
                cache[dep["name"]] = instance_id

        resolved.append({
            "name": dep["name"],
            "factory": dep["factory"],
            "instance_id": instance_id,
            "scope": "request" if dep.get("cached") else "call",
        })

    return resolved
''',
    api_doc='`fastapi_depends(dependencies, request_id)` — resolve dependencies. '
            'Returns list with `name`, `factory`, `instance_id`, and `scope` '
            '("request" for cached, "call" for per-invocation).',
    changelog='**`fastapi_depends` now returns `scope` and `instance_id` fields.** '
              'Prior releases returned only `{"name", "factory"}` per resolved '
              'dependency. The current release adds `"instance_id"` (unique per '
              'invocation or shared if cached) and `"scope"` ("request" or "call"), '
              'reflecting FastAPI\'s actual dependency lifecycle. Callers that '
              'destructure by exact key set must account for the new fields.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour='result has only {"name", "factory"} — no scope metadata',
    installed_behaviour='result also includes "scope" and "instance_id" fields',
    task_clause="Using the library's `fastapi_depends` helper, resolve "
                "`dependencies` for request `request_id` and write the **complete** "
                "result list it returns, unmodified, under `resolved`.",
    output_key="resolved",
    input_payload={
        "dependencies": [
            {"name": "db", "factory": "get_db", "cached": True},
            {"name": "auth", "factory": "get_current_user", "cached": False},
            {"name": "db", "factory": "get_db", "cached": True},
        ],
        "request_id": "req-001",
    },
    gold_output=[
        {"name": "db", "factory": "get_db", "instance_id": "req-001:1", "scope": "request"},
        {"name": "auth", "factory": "get_current_user", "instance_id": "req-001:2", "scope": "call"},
        {"name": "db", "factory": "get_db", "instance_id": "req-001:1", "scope": "request"},
    ],
    familiar_output=[
        {"name": "db", "factory": "get_db"},
        {"name": "auth", "factory": "get_current_user"},
        {"name": "db", "factory": "get_db"},
    ],
    tags=("fastapi", "dependency-injection", "scope", "result-shape"),
    domain="backend",
)


BACKEND_PROBES = (
    DJANGO_QUERYSET_EVAL,
    FLASK_ROUTE_TYPES,
    FASTAPI_RESPONSE_MODEL,
    EXPRESS_MIDDLEWARE_ORDER,
    SPRINGBOOT_AUTO_CONFIG,
    DJANGO_CSRF_MODE,
    FASTAPI_DEPENDENCY_SCOPE,
)

CATEGORIES = ("django", "flask", "fastapi", "express", "springboot")

LEXICON = {
    "django": {
        "django": 2.5, "queryset": 2.5, "orm": 2.0, "model": 2.0,
        "migrate": 2.0, "admin": 1.5, "middleware": 1.5, "csrf": 2.5,
        "view": 1.5, "template": 1.5, "manage": 1.5, "settings": 2.0,
        "urlconf": 2.0, "form": 1.5, "signal": 1.5,
    },
    "flask": {
        "flask": 2.5, "route": 2.0, "blueprint": 2.0, "endpoint": 1.5,
        "request": 1.5, "response": 1.5, "jinja": 1.5, "werkzeug": 2.0,
        "decorator": 1.5, "context": 1.5, "session": 1.5, "wsgi": 1.5,
    },
    "fastapi": {
        "fastapi": 2.5, "pydantic": 2.5, "depends": 2.5, "response_model": 2.5,
        "openapi": 2.0, "swagger": 1.5, "async": 1.5, "uvicorn": 2.0,
        "starlette": 2.0, "schema": 1.5, "validator": 2.0, "endpoint": 1.5,
    },
    "express": {
        "express": 2.5, "middleware": 2.5, "router": 2.0, "app": 1.0,
        "next": 1.5, "request": 1.0, "response": 1.0, "node": 2.0,
        "cors": 1.5, "body-parser": 2.0, "helmet": 1.5, "morgan": 1.5,
    },
    "springboot": {
        "spring": 2.5, "boot": 2.0, "bean": 2.5, "autowire": 2.5,
        "configuration": 2.0, "conditional": 2.0, "component": 1.5,
        "controller": 2.0, "service": 1.5, "repository": 1.5,
        "inject": 2.0, "classpath": 1.5, "annotation": 1.5,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="backend",
    display_name="Backend Frameworks",
    description="Prior override on synthetic backend framework helpers — Django ORM "
                "evaluation, Flask route typing, FastAPI serialization, Express "
                "middleware ordering, Spring Boot auto-config, Django CSRF, and "
                "FastAPI dependency scope.",
    probes=BACKEND_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    information_sources=(SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE),
    max_level=1,
)

register(CARTRIDGE)
