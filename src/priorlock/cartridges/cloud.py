"""Cloud domain cartridge — prior override on a synthetic cloud infrastructure
API covering S3-style object storage and Kubernetes-style orchestration and
DNS primitives that LLMs have strong memorized priors about.
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

S3_CHECKSUM_DEFAULT = Probe(
    id="s3_checksum_default",
    family="default_flip",
    category="storage",
    summary="cloud_put_object() now requires checksum verification by default instead of skipping it.",
    fn="cloud_put_object",
    signature='cloud_put_object(bucket, key, data, checksum_mode="required")',
    impl='''
def cloud_put_object(bucket, key, data, checksum_mode="required"):
    """Upload *data* (a dict with "body" and caller-declared "checksum") to
    *bucket*/*key* in the simulated object store.

    checksum_mode="required" (default) — the SHA-256 checksum (first 12 hex
                                          chars) of data["body"] is computed
                                          and compared against the caller's
                                          declared data["checksum"]; on
                                          mismatch the upload is rejected
    checksum_mode="skip"                — the object is stored without any
                                          checksum verification
    """
    import hashlib

    body = data["body"]
    declared = data.get("checksum")
    actual = hashlib.sha256(body.encode()).hexdigest()[:12]

    if checksum_mode == "required" and declared != actual:
        return {"status": "error", "error": f"ChecksumMismatch: declared={declared} actual={actual}"}

    return {
        "status": "success",
        "bucket": bucket,
        "key": key,
        "size": len(body),
        "checksum_verified": checksum_mode == "required",
    }
''',
    api_doc='`cloud_put_object(bucket, key, data, checksum_mode="required")` — '
            'upload `data` (a dict with `"body"` and a caller-declared '
            '`"checksum"`) to `bucket`/`key`. `checksum_mode` is `"required"` '
            '(default, verifies `data["checksum"]` against the computed '
            'SHA-256 of `data["body"]` and rejects on mismatch) or `"skip"` '
            '(stores the object without verifying any checksum).',
    changelog='**`cloud_put_object` — default `checksum_mode` changed from '
              '`"skip"` to `"required"`.** Prior releases stored the object '
              'body as-is regardless of any declared checksum. The current '
              'release verifies the caller-declared checksum against the '
              'computed SHA-256 of the body by default and rejects the '
              'upload on mismatch. Pass `checksum_mode="skip"` to restore '
              'the old behaviour of storing the object unconditionally.',
    param="checksum_mode",
    gold_kwargs={"checksum_mode": "skip"},
    familiar_kwargs={},
    familiar_behaviour='checksum_mode defaults to "required" — mismatched checksums reject the upload',
    installed_behaviour='checksum_mode defaults to "required" — pass "skip" to store unconditionally',
    task_clause="Upload the artifact described by `data` to `bucket`/`key` "
                "so that it is stored **regardless of whether its declared "
                "checksum matches** — this system's declared checksums come "
                "from a legacy build pipeline known to be unreliable, and "
                "uploads must not be rejected because of them. Write the "
                "resulting dict under `result`.",
    output_key="result",
    input_payload={
        "bucket": "release-artifacts",
        "key": "builds/app-1.2.3.tar.gz",
        "data": {"body": "release-artifact-payload-v1.2.3", "checksum": "aaaaaaaaaaaa"},
    },
    gold_output={
        "status": "success",
        "bucket": "release-artifacts",
        "key": "builds/app-1.2.3.tar.gz",
        "size": len("release-artifact-payload-v1.2.3"),
        "checksum_verified": False,
    },
    familiar_output={
        "status": "error",
        "error": "ChecksumMismatch: declared=aaaaaaaaaaaa actual=99f506bb8f9a",
    },
    tags=("s3", "checksum", "storage"),
    domain="cloud",
)


DNS_TTL_UNIT = Probe(
    id="dns_ttl_unit",
    family="default_flip",
    category="networking",
    summary="cloud_dns_record() now interprets ttl as seconds by default instead of minutes.",
    fn="cloud_dns_record",
    signature='cloud_dns_record(name, record_type, ttl, ttl_unit="seconds")',
    impl='''
def cloud_dns_record(name, record_type, ttl, ttl_unit="seconds"):
    """Build a DNS record dict for *name* of type *record_type* with the
    given *ttl*.

    ttl_unit="seconds" (default) — *ttl* is interpreted as seconds directly
    ttl_unit="minutes"           — *ttl* is interpreted as minutes and
                                    converted to seconds (ttl * 60)
    """
    ttl_seconds = ttl * 60 if ttl_unit == "minutes" else ttl
    return {"name": name, "type": record_type, "ttl_seconds": ttl_seconds}
''',
    api_doc='`cloud_dns_record(name, record_type, ttl, ttl_unit="seconds")` — '
            'build a DNS record dict for `name` of type `record_type` with '
            '`ttl`. `ttl_unit` is `"seconds"` (default, `ttl` used directly) '
            'or `"minutes"` (`ttl` is multiplied by 60 before being stored '
            'as `ttl_seconds`).',
    changelog='**`cloud_dns_record` — default `ttl_unit` changed from '
              '`"minutes"` to `"seconds"`.** Prior releases interpreted the '
              '`ttl` argument as minutes by default, matching this '
              'organization\'s legacy zone-file convention. The current '
              'release interprets `ttl` as seconds by default, matching '
              'most public DNS APIs. Pass `ttl_unit="minutes"` to restore '
              'the legacy minutes-based interpretation.',
    param="ttl_unit",
    gold_kwargs={"ttl_unit": "minutes"},
    familiar_kwargs={},
    familiar_behaviour='ttl_unit defaults to "seconds" — the raw ttl value is stored as-is',
    installed_behaviour='ttl_unit defaults to "seconds" — pass "minutes" to convert ttl * 60',
    task_clause="Create the DNS record for `name` with the given `ttl`, "
                "where `ttl` is expressed in **minutes** as this "
                "organization's zone files have always specified TTLs — "
                "convert it to seconds accordingly. Write the resulting "
                "dict under `record`.",
    output_key="record",
    input_payload={"name": "api.example.com", "record_type": "A", "ttl": 5},
    gold_output={"name": "api.example.com", "type": "A", "ttl_seconds": 300},
    familiar_output={"name": "api.example.com", "type": "A", "ttl_seconds": 5},
    tags=("dns", "ttl", "networking"),
    domain="cloud",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

K8S_APPLY_STRATEGY = Probe(
    id="k8s_apply_strategy",
    family="value_remap",
    category="orchestration",
    summary='cloud_apply() with strategy="merge" now does a strategic merge patch instead of a JSON merge patch.',
    fn="cloud_apply",
    signature='cloud_apply(manifest, patch, strategy="merge")',
    impl='''
def cloud_apply(manifest, patch, strategy="merge"):
    """Apply *patch* to *manifest*, returning the merged manifest.

    strategy="merge"      (default) — strategic merge patch: dicts merge
                                       recursively; lists of dicts that share
                                       a "name" key merge item-by-item on
                                       that key, leaving unmatched items and
                                       unspecified fields untouched
    strategy="json_merge"           — RFC 7396 JSON merge patch: dicts merge
                                       recursively, but any list value in
                                       *patch* replaces the corresponding
                                       list in *manifest* wholesale
    """
    import copy

    def _json_merge(base, p):
        if not isinstance(p, dict):
            return p
        if not isinstance(base, dict):
            base = {}
        out = dict(base)
        for k, v in p.items():
            if v is None:
                out.pop(k, None)
            elif isinstance(v, dict):
                out[k] = _json_merge(out.get(k), v)
            else:
                out[k] = v  # lists (and scalars) replace wholesale
        return out

    def _strategic_merge(base, p):
        if not isinstance(p, dict):
            return p
        if not isinstance(base, dict):
            base = {}
        out = dict(base)
        for k, v in p.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = _strategic_merge(out[k], v)
            elif (
                isinstance(v, list)
                and isinstance(out.get(k), list)
                and all(isinstance(x, dict) and "name" in x for x in v)
            ):
                merged_list = [dict(x) for x in out[k]]
                by_name = {x.get("name"): idx for idx, x in enumerate(merged_list)}
                for item in v:
                    name = item.get("name")
                    if name in by_name:
                        idx = by_name[name]
                        merged_list[idx] = _strategic_merge(merged_list[idx], item)
                    else:
                        merged_list.append(item)
                out[k] = merged_list
            else:
                out[k] = v
        return out

    result = copy.deepcopy(manifest)
    if strategy == "json_merge":
        return _json_merge(result, patch)
    return _strategic_merge(result, patch)
''',
    api_doc='`cloud_apply(manifest, patch, strategy="merge")` — apply `patch` '
            'to `manifest`. `strategy` is `"merge"` (default, strategic '
            'merge patch — list items sharing a `"name"` key merge '
            'field-by-field, unmatched items and unspecified fields are '
            'preserved) or `"json_merge"` (RFC 7396 JSON merge patch — any '
            'list in `patch` replaces the corresponding list in `manifest` '
            'wholesale).',
    changelog='**`cloud_apply` — the meaning of `strategy="merge"` changed.** '
              'Prior releases used `strategy="merge"` to mean RFC 7396 JSON '
              'merge patch, where a list in `patch` replaces the '
              'corresponding list in `manifest` wholesale. The current '
              'release repurposes `strategy="merge"` (the default) to mean '
              'a Kubernetes-style strategic merge patch, where list items '
              'are matched and merged by their `"name"` key instead of being '
              'replaced outright. Pass `strategy="json_merge"` to restore '
              'the old wholesale-replacement semantics.',
    param="strategy",
    gold_kwargs={"strategy": "json_merge"},
    familiar_kwargs={"strategy": "merge"},
    familiar_behaviour='strategy="merge" performs a strategic merge patch — unmatched list items are preserved',
    installed_behaviour='strategy="merge" performs a strategic merge patch; pass "json_merge" for wholesale list replacement',
    task_clause="Apply `patch` to `manifest` using RFC 7396 JSON merge patch "
                "semantics: any list present in `patch` must **replace the "
                "corresponding list in `manifest` wholesale**, not merge "
                "item-by-item. Write the resulting manifest dict under "
                "`applied`.",
    output_key="applied",
    input_payload={
        "manifest": {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "web"},
            "spec": {
                "replicas": 1,
                "containers": [
                    {"name": "app", "image": "app:1.0", "ports": [{"containerPort": 8080}]},
                    {"name": "sidecar", "image": "proxy:2.0"},
                ],
            },
        },
        "patch": {
            "spec": {
                "containers": [
                    {"name": "app", "image": "app:2.0"},
                ],
            },
        },
    },
    gold_output={
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "web"},
        "spec": {
            "replicas": 1,
            "containers": [
                {"name": "app", "image": "app:2.0"},
            ],
        },
    },
    familiar_output={
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "web"},
        "spec": {
            "replicas": 1,
            "containers": [
                {"name": "app", "image": "app:2.0", "ports": [{"containerPort": 8080}]},
                {"name": "sidecar", "image": "proxy:2.0"},
            ],
        },
    },
    tags=("k8s", "apply", "merge-patch", "orchestration"),
    domain="cloud",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

LIST_OBJECTS_PAGINATION = Probe(
    id="list_objects_pagination",
    family="result_shape",
    category="storage",
    summary="cloud_list_objects() now returns a paginated envelope instead of a flat list of keys.",
    fn="cloud_list_objects",
    signature='cloud_list_objects(bucket, prefix="")',
    impl='''
def cloud_list_objects(bucket, prefix=""):
    """List objects in *bucket* whose key starts with *prefix*.

    Returns {"items": [...], "next_token": str | None, "truncated": bool},
    where each item is {"key": str, "size": int}. "next_token" is None and
    "truncated" is False when the full listing fits in one page.
    """
    catalog = {
        "release-artifacts": [
            {"key": "builds/app-1.0.0.tar.gz", "size": 1024},
            {"key": "builds/app-1.1.0.tar.gz", "size": 2048},
            {"key": "builds/app-1.2.0.tar.gz", "size": 4096},
        ],
    }
    objects = catalog.get(bucket, [])
    items = [o for o in objects if o["key"].startswith(prefix)]
    return {"items": items, "next_token": None, "truncated": False}
''',
    api_doc='`cloud_list_objects(bucket, prefix="")` — list objects in '
            '`bucket` whose key starts with `prefix`. Returns '
            '`{"items": [...], "next_token": str | None, "truncated": bool}`, '
            'where each item is `{"key": str, "size": int}`.',
    changelog='**`cloud_list_objects` — return shape changed.** Prior '
              'releases returned a flat list of object key strings. The '
              'current release returns a paginated envelope dict '
              '`{"items": [...], "next_token": str | None, "truncated": '
              'bool}`, where each item is a `{"key", "size"}` dict, to '
              'support cursor-based pagination on large buckets. There is '
              'no flag to restore the old flat-list shape — callers that '
              'need just the keys must extract them from `items` '
              'themselves.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="returns a flat list of object key strings",
    installed_behaviour="returns a paginated envelope dict with items/next_token/truncated",
    task_clause="Using the library's `cloud_list_objects` helper, list the "
                "objects in `bucket` under `prefix` exactly as the installed "
                "function returns them — do not reshape or flatten the "
                "result. Write the resulting value under `listing`.",
    output_key="listing",
    input_payload={"bucket": "release-artifacts", "prefix": "builds/"},
    gold_output={
        "items": [
            {"key": "builds/app-1.0.0.tar.gz", "size": 1024},
            {"key": "builds/app-1.1.0.tar.gz", "size": 2048},
            {"key": "builds/app-1.2.0.tar.gz", "size": 4096},
        ],
        "next_token": None,
        "truncated": False,
    },
    familiar_output=[
        "builds/app-1.0.0.tar.gz",
        "builds/app-1.1.0.tar.gz",
        "builds/app-1.2.0.tar.gz",
    ],
    tags=("s3", "pagination", "list", "storage"),
    domain="cloud",
)


CLOUD_PROBES = (
    S3_CHECKSUM_DEFAULT,
    DNS_TTL_UNIT,
    K8S_APPLY_STRATEGY,
    LIST_OBJECTS_PAGINATION,
)

CATEGORIES = ("storage", "orchestration", "networking", "compute")

LEXICON = {
    "storage": {
        "s3": 2.5, "bucket": 2.5, "object": 2.0, "checksum": 2.0,
        "upload": 1.5, "key": 1.0, "pagination": 1.5, "list": 1.0,
    },
    "orchestration": {
        "k8s": 2.5, "kubernetes": 2.5, "apply": 2.0, "patch": 2.0,
        "manifest": 2.0, "merge": 1.5, "strategic": 1.5, "container": 1.0,
    },
    "networking": {
        "dns": 2.5, "ttl": 2.5, "record": 2.0, "zone": 1.5,
        "domain": 1.0, "resolve": 1.0, "seconds": 1.0, "minutes": 1.0,
    },
    "compute": {
        "instance": 2.0, "vm": 2.0, "cluster": 1.5, "node": 1.5,
        "scale": 1.5, "deploy": 1.5, "workload": 1.0, "pod": 1.0,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="cloud",
    display_name="Cloud Infrastructure API",
    description="Prior override on a synthetic cloud infrastructure library — "
                "S3-style object storage, Kubernetes-style manifest apply, and "
                "DNS record management idioms that LLMs have strong memorized "
                "priors about.",
    probes=CLOUD_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    max_level=1,
)

register(CARTRIDGE)
