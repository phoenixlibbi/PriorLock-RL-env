"""Frontend framework domain cartridge — prior override on synthetic
frontend framework helper wrappers.

Six probes across the three PriorLock families, exercising the parts of
React, Next.js, Angular, and Vue semantics that LLMs have the strongest
memorized priors about: React's useEffect cleanup return, Next.js page
data-fetching method, Angular change detection strategy default, Vue
reactivity system (ref vs reactive), React key prop generation, and
Next.js routing convention.
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

REACT_USE_EFFECT_CLEANUP = Probe(
    id="react_use_effect_cleanup",
    family="default_flip",
    category="react",
    summary="react_use_effect() now runs cleanup before every re-render by default, not just on unmount.",
    fn="react_use_effect",
    signature="react_use_effect(effect_fn, deps, cleanup_on_every=True)",
    impl='''
def react_use_effect(effect_fn, deps, cleanup_on_every=True):
    """Simulate React useEffect lifecycle for a component render sequence.

    effect_fn    — callable returning a cleanup function (or None)
    deps         — list of dependency snapshots per render (list of lists)
    cleanup_on_every=True  (default) — cleanup runs before every re-render
                                         where deps changed AND on unmount
    cleanup_on_every=False           — cleanup runs only on unmount (final render)

    Returns a list of event strings in execution order.
    """
    events = []
    prev_deps = None
    cleanup = None

    for i, d in enumerate(deps):
        deps_changed = prev_deps is None or d != prev_deps

        if deps_changed:
            if cleanup is not None and cleanup_on_every:
                events.append(f"cleanup:render_{i}")
            result = effect_fn(i)
            events.append(f"effect:render_{i}")
            cleanup = result if callable(result) else None

        prev_deps = d

    # Unmount cleanup always runs
    if cleanup is not None:
        events.append("cleanup:unmount")

    return events
''',
    api_doc='`react_use_effect(effect_fn, deps, cleanup_on_every=True)` — simulate '
            'useEffect across a render sequence. `cleanup_on_every=True` (default) '
            'runs cleanup before each re-render with changed deps. '
            '`cleanup_on_every=False` runs cleanup only on unmount.',
    changelog='**`react_use_effect` — default `cleanup_on_every` changed from '
              '`False` to `True`.** Prior releases only ran cleanup on unmount, '
              'matching older React class-component behavior. The current release '
              'runs cleanup before every re-render where deps changed, matching '
              'React 18+ strict mode behavior. Pass `cleanup_on_every=False` '
              'to restore unmount-only cleanup.',
    param="cleanup_on_every",
    gold_kwargs={"cleanup_on_every": False},
    familiar_kwargs={},
    familiar_behaviour="cleanup_on_every defaults to False — cleanup only on unmount",
    installed_behaviour="cleanup_on_every defaults to True — cleanup before every re-render",
    task_clause="Simulate the useEffect lifecycle across `deps` render snapshots, "
                "running cleanup **only on unmount** (not before re-renders). "
                "Write the event list under `events`.",
    output_key="events",
    input_payload={
        "deps": [[1], [2], [2], [3]],
    },
    gold_output=["effect:render_0", "effect:render_1", "effect:render_3", "cleanup:unmount"],
    familiar_output=["effect:render_0", "cleanup:render_1", "effect:render_1", "cleanup:render_3", "effect:render_3", "cleanup:unmount"],
    tags=("react", "useEffect", "cleanup", "lifecycle"),
    domain="frontend",
)


NEXTJS_DATA_FETCH_MODE = Probe(
    id="nextjs_data_fetch_mode",
    family="default_flip",
    category="nextjs",
    summary="nextjs_get_data() now uses server-side rendering (SSR) by default instead of static generation (SSG).",
    fn="nextjs_get_data",
    signature='nextjs_get_data(pages, mode="ssr")',
    impl='''
def nextjs_get_data(pages, mode="ssr"):
    """Simulate Next.js data fetching for a list of page configs.

    Each page is {"route": str, "data": any, "revalidate": int | None}.

    mode="ssr"  (default) — server-side render: data fetched on every request,
                             result includes {"cache": "no-store"}
    mode="ssg"           — static generation: data fetched at build time,
                             result includes {"cache": "force-cache"}
                             If revalidate is set, adds ISR config.
    """
    results = []
    for page in pages:
        entry = {"route": page["route"], "data": page["data"]}
        if mode == "ssg":
            entry["cache"] = "force-cache"
            if page.get("revalidate") is not None:
                entry["revalidate"] = page["revalidate"]
        else:
            entry["cache"] = "no-store"
        results.append(entry)
    return results
''',
    api_doc='`nextjs_get_data(pages, mode="ssr")` — simulate Next.js data '
            'fetching. `mode="ssr"` (default) adds `cache: "no-store"` (SSR). '
            '`mode="ssg"` adds `cache: "force-cache"` with optional ISR `revalidate`.',
    changelog='**`nextjs_get_data` — default `mode` changed from `"ssg"` to '
              '`"ssr"`.** Prior releases defaulted to static generation '
              '(`getStaticProps` style), where data was fetched at build time. '
              'The current release defaults to server-side rendering (App Router '
              'style), fetching data on every request. Pass `mode="ssg"` to '
              'restore build-time static generation.',
    param="mode",
    gold_kwargs={"mode": "ssg"},
    familiar_kwargs={},
    familiar_behaviour='mode defaults to "ssg" — static generation, data at build time',
    installed_behaviour='mode defaults to "ssr" — server-side rendering, data on every request',
    task_clause="Fetch data for `pages` using **static generation** (build-time data, "
                "with ISR revalidation where specified). Write the results under `fetched`.",
    output_key="fetched",
    input_payload={
        "pages": [
            {"route": "/blog", "data": ["post1", "post2"], "revalidate": 60},
            {"route": "/about", "data": {"team": 5}, "revalidate": None},
        ],
    },
    gold_output=[
        {"route": "/blog", "data": ["post1", "post2"], "cache": "force-cache", "revalidate": 60},
        {"route": "/about", "data": {"team": 5}, "cache": "force-cache"},
    ],
    familiar_output=[
        {"route": "/blog", "data": ["post1", "post2"], "cache": "no-store"},
        {"route": "/about", "data": {"team": 5}, "cache": "no-store"},
    ],
    tags=("nextjs", "data-fetching", "ssr", "ssg"),
    domain="frontend",
)


ANGULAR_CHANGE_DETECTION = Probe(
    id="angular_change_detection",
    family="default_flip",
    category="angular",
    summary="ng_component() now uses OnPush change detection by default instead of Default.",
    fn="ng_component",
    signature='ng_component(components, strategy="onpush")',
    impl='''
def ng_component(components, strategy="onpush"):
    """Simulate Angular change detection for a component tree.

    Each component is {"name": str, "inputs_changed": bool, "event_fired": bool}.

    strategy="default" — check all components on every cycle
    strategy="onpush"  (default) — only check if inputs changed or event fired
    """
    checked = []
    for comp in components:
        if strategy == "default":
            checked.append({"name": comp["name"], "checked": True})
        else:  # onpush
            should_check = comp.get("inputs_changed", False) or comp.get("event_fired", False)
            checked.append({"name": comp["name"], "checked": should_check})
    return checked
''',
    api_doc='`ng_component(components, strategy="onpush")` — simulate Angular '
            'change detection. `strategy="default"` checks all components. '
            '`strategy="onpush"` only checks components with changed inputs or events.',
    changelog='**`ng_component` — default `strategy` changed from `"default"` to '
              '`"onpush"`.** Prior releases checked all components on every '
              'change detection cycle, matching Angular\'s Default strategy. '
              'The current release uses OnPush by default, only checking '
              'components whose inputs changed or that fired events. Pass '
              '`strategy="default"` to restore full-tree checking.',
    param="strategy",
    gold_kwargs={"strategy": "default"},
    familiar_kwargs={},
    familiar_behaviour='strategy defaults to "default" — all components checked every cycle',
    installed_behaviour='strategy defaults to "onpush" — only changed/evented components checked',
    task_clause="Run change detection on `components` using **Default strategy** "
                "(check all components regardless of input changes). Write the "
                "results under `checked`.",
    output_key="checked",
    input_payload={
        "components": [
            {"name": "AppRoot", "inputs_changed": True, "event_fired": False},
            {"name": "Sidebar", "inputs_changed": False, "event_fired": False},
            {"name": "UserList", "inputs_changed": False, "event_fired": True},
            {"name": "Footer", "inputs_changed": False, "event_fired": False},
        ],
    },
    gold_output=[
        {"name": "AppRoot", "checked": True},
        {"name": "Sidebar", "checked": True},
        {"name": "UserList", "checked": True},
        {"name": "Footer", "checked": True},
    ],
    familiar_output=[
        {"name": "AppRoot", "checked": True},
        {"name": "Sidebar", "checked": False},
        {"name": "UserList", "checked": True},
        {"name": "Footer", "checked": False},
    ],
    tags=("angular", "change-detection", "onpush"),
    domain="frontend",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

VUE_REACTIVITY_MODE = Probe(
    id="vue_reactivity_mode",
    family="value_remap",
    category="vue",
    summary='vue_state()\'s kind="auto" now means deep reactive proxy instead of shallow ref.',
    fn="vue_state",
    signature='vue_state(initial, kind="auto")',
    impl='''
def vue_state(initial, kind="auto"):
    """Create a Vue-style reactive state wrapper.

    kind="ref"      — shallow ref: only .value reassignment is reactive,
                       nested properties are NOT tracked
    kind="reactive" — deep reactive proxy: all nested property mutations
                       are tracked automatically
    kind="auto"     (default) — deep reactive proxy (same as "reactive")

    Returns {"value": wrapped_data, "tracking": list_of_tracked_paths}
    """
    if kind == "ref":
        return {"value": initial, "tracking": [".value"]}

    # "reactive" or "auto" — deep tracking
    tracked = []
    def walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{path}.{k}" if path else k
                tracked.append(p)
                walk(v, p)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                p = f"{path}[{i}]"
                tracked.append(p)
                walk(v, p)
    walk(initial)
    return {"value": initial, "tracking": tracked if tracked else [".value"]}
''',
    api_doc='`vue_state(initial, kind="auto")` — create reactive state. '
            '`kind="ref"` for shallow ref (tracks `.value` only). '
            '`kind="reactive"` or `kind="auto"` (default) for deep reactive proxy '
            '(tracks all nested paths).',
    changelog='**`vue_state` — the `kind="auto"` value now means deep reactive '
              'proxy, not shallow ref.** Prior releases treated `"auto"` as a '
              'synonym for `"ref"` — only `.value` reassignment was reactive. '
              'The current release makes `"auto"` equivalent to `"reactive"`, '
              'deeply tracking all nested properties. Pass `kind="ref"` if you '
              'need shallow reactivity.',
    param="kind",
    gold_kwargs={"kind": "ref"},
    familiar_kwargs={"kind": "auto"},
    familiar_behaviour='kind="auto" creates a shallow ref (only .value tracked)',
    installed_behaviour='kind="auto" creates a deep reactive proxy (all nested paths tracked)',
    task_clause="Create a reactive state wrapper for `initial` using **shallow ref** "
                "semantics (only `.value` reassignment is reactive, no nested tracking). "
                "Write the result under `state`.",
    output_key="state",
    input_payload={
        "initial": {"user": {"name": "Alice", "prefs": {"theme": "dark"}}},
    },
    gold_output={"value": {"user": {"name": "Alice", "prefs": {"theme": "dark"}}}, "tracking": [".value"]},
    familiar_output={
        "value": {"user": {"name": "Alice", "prefs": {"theme": "dark"}}},
        "tracking": ["user", "user.name", "user.prefs", "user.prefs.theme"],
    },
    tags=("vue", "reactivity", "ref", "reactive"),
    domain="frontend",
)


REACT_KEY_GENERATION = Probe(
    id="react_key_generation",
    family="value_remap",
    category="react",
    summary='react_list_keys()\'s strategy="auto" now uses stable content hash instead of array index.',
    fn="react_list_keys",
    signature='react_list_keys(items, strategy="auto")',
    impl='''
def react_list_keys(items, strategy="auto"):
    """Generate React list keys for *items*.

    strategy="index"   — use array index as key (fragile on reorder)
    strategy="content" — use stable hash of item content
    strategy="auto"    (default) — use stable content hash (same as "content")

    Returns list of {"item": ..., "key": ...}.
    """
    import hashlib
    result = []
    for i, item in enumerate(items):
        if strategy == "index":
            key = str(i)
        else:  # "content" or "auto"
            key = hashlib.md5(str(item).encode()).hexdigest()[:8]
        result.append({"item": item, "key": key})
    return result
''',
    api_doc='`react_list_keys(items, strategy="auto")` — generate keys for list '
            'rendering. `strategy="index"` uses array position. '
            '`strategy="content"` or `strategy="auto"` (default) uses content hash.',
    changelog='**`react_list_keys` — the `strategy="auto"` value now means '
              'content-based hash keys, not index-based keys.** Prior releases '
              'treated `"auto"` as a synonym for `"index"`, using the array '
              'position as the key. The current release generates a stable '
              'content hash (MD5 prefix). Pass `strategy="index"` if you need '
              'position-based keys.',
    param="strategy",
    gold_kwargs={"strategy": "index"},
    familiar_kwargs={"strategy": "auto"},
    familiar_behaviour='strategy="auto" generates index-based keys',
    installed_behaviour='strategy="auto" generates content-hash keys',
    task_clause="Generate keys for `items` using **array index** as key "
                "(position-based, not content-based). Write the list under `keyed`.",
    output_key="keyed",
    input_payload={
        "items": ["apple", "banana", "cherry"],
    },
    gold_output=[
        {"item": "apple", "key": "0"},
        {"item": "banana", "key": "1"},
        {"item": "cherry", "key": "2"},
    ],
    familiar_output=[
        {"item": "apple", "key": "1f3bfb24"},
        {"item": "banana", "key": "72b302bf"},
        {"item": "cherry", "key": "3b2ea239"},
    ],
    tags=("react", "keys", "list-rendering"),
    domain="frontend",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

NEXTJS_ROUTE_CONVENTION = Probe(
    id="nextjs_route_convention",
    family="result_shape",
    category="nextjs",
    summary="nextjs_routes() now returns App Router format with layout segments instead of Pages Router flat paths.",
    fn="nextjs_routes",
    signature="nextjs_routes(pages)",
    impl='''
def nextjs_routes(pages):
    """Parse Next.js page definitions into route metadata.

    Each page is {"file": str, "dynamic": bool}.

    Returns route entries with App Router format: each route includes a
    "segments" list (path parts) and a "layout" field indicating the
    nearest layout boundary.
    """
    routes = []
    for page in pages:
        path = page["file"]
        # Strip file extensions and index
        route = path.replace(".tsx", "").replace(".jsx", "")
        route = route.replace("/page", "").replace("/index", "")
        if not route:
            route = "/"

        parts = [p for p in route.strip("/").split("/") if p]
        segments = parts if parts else ["/"]

        # Determine layout boundary (nearest parent with layout.tsx convention)
        layout = "/" + "/".join(segments[:-1]) if len(segments) > 1 else "/"

        entry = {
            "route": "/" + "/".join(parts) if parts else "/",
            "segments": segments,
            "layout": layout,
            "dynamic": page.get("dynamic", False),
        }
        routes.append(entry)
    return routes
''',
    api_doc='`nextjs_routes(pages)` — parse page definitions into route metadata. '
            'Returns entries with `route`, `segments` (path parts), `layout` '
            '(nearest layout boundary), and `dynamic` flag.',
    changelog='**`nextjs_routes` now returns App Router format with `segments` '
              'and `layout` fields.** Prior releases returned flat `{"route", "dynamic"}` '
              'objects matching the Pages Router convention. The current release '
              'includes `segments` (an array of path parts) and `layout` (the '
              'nearest layout boundary), reflecting the App Router\'s nested '
              'layout architecture. Callers that destructure by exact key set '
              'must account for the new fields.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour='result has only {"route", "dynamic"} — Pages Router flat format',
    installed_behaviour='result also includes "segments" and "layout" — App Router format',
    task_clause="Using the library's `nextjs_routes` helper, parse `pages` and "
                "write the **complete** result list it returns, unmodified, under `routes`.",
    output_key="routes",
    input_payload={
        "pages": [
            {"file": "/page.tsx", "dynamic": False},
            {"file": "/blog/page.tsx", "dynamic": False},
            {"file": "/blog/[slug]/page.tsx", "dynamic": True},
        ],
    },
    gold_output=[
        {"route": "/", "segments": ["/"], "layout": "/", "dynamic": False},
        {"route": "/blog", "segments": ["blog"], "layout": "/", "dynamic": False},
        {"route": "/blog/[slug]", "segments": ["blog", "[slug]"], "layout": "/blog", "dynamic": True},
    ],
    familiar_output=[
        {"route": "/", "dynamic": False},
        {"route": "/blog", "dynamic": False},
        {"route": "/blog/[slug]", "dynamic": True},
    ],
    tags=("nextjs", "routing", "app-router", "result-shape"),
    domain="frontend",
)


FRONTEND_PROBES = (
    REACT_USE_EFFECT_CLEANUP,
    NEXTJS_DATA_FETCH_MODE,
    ANGULAR_CHANGE_DETECTION,
    VUE_REACTIVITY_MODE,
    REACT_KEY_GENERATION,
    NEXTJS_ROUTE_CONVENTION,
)

CATEGORIES = ("react", "nextjs", "angular", "vue")

LEXICON = {
    "react": {
        "react": 2.5, "component": 2.0, "hook": 2.5, "useEffect": 2.5,
        "useState": 2.0, "render": 2.0, "jsx": 2.0, "props": 2.0,
        "state": 1.5, "lifecycle": 2.0, "key": 1.5, "virtual": 1.5,
        "dom": 1.5, "memo": 2.0, "context": 1.5, "ref": 1.5,
    },
    "nextjs": {
        "next": 2.5, "nextjs": 2.5, "page": 1.5, "route": 2.0, "ssr": 2.5,
        "ssg": 2.5, "isr": 2.0, "getServerSideProps": 2.5, "getStaticProps": 2.5,
        "app-router": 2.5, "server-component": 2.0, "layout": 2.0,
        "fetch": 1.5, "revalidate": 2.0, "middleware": 1.5,
    },
    "angular": {
        "angular": 2.5, "component": 1.5, "directive": 2.0, "service": 1.5,
        "module": 1.5, "change-detection": 2.5, "onpush": 2.5, "zone": 2.0,
        "rxjs": 2.0, "observable": 2.0, "pipe": 1.5, "inject": 2.0,
        "template": 1.5, "binding": 2.0, "decorator": 1.5,
    },
    "vue": {
        "vue": 2.5, "reactive": 2.5, "ref": 2.0, "computed": 2.0,
        "watch": 2.0, "composition": 2.0, "options": 1.5, "proxy": 2.0,
        "setup": 2.0, "defineComponent": 2.0, "emit": 1.5, "slot": 1.5,
        "directive": 1.5, "store": 1.5, "pinia": 2.0,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="frontend",
    display_name="Frontend Frameworks",
    description="Prior override on synthetic frontend framework helpers — React "
                "useEffect lifecycle, Next.js data fetching, Angular change detection, "
                "Vue reactivity, React keys, and Next.js routing conventions.",
    probes=FRONTEND_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    max_level=1,
)

register(CARTRIDGE)
