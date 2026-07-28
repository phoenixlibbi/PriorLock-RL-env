"""Config domain cartridge — prior override on a synthetic config-file processing
library covering YAML/TOML/JSON parsing, merging, variable expansion, and
serialization idioms that LLMs have strong memorized priors about.
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register, SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

YAML_BOOL_PARSING = Probe(
    id="yaml_bool_parsing",
    family="default_flip",
    category="parsing",
    summary="parse_yaml_values() now treats yes/no/on/off as strings by default instead of booleans.",
    fn="parse_yaml_values",
    signature="parse_yaml_values(data, legacy_bools=False)",
    impl='''
def parse_yaml_values(data, legacy_bools=False):
    """Coerce YAML-style scalar strings in the flat dict *data*.

    legacy_bools=False (default) — "yes"/"no"/"on"/"off" (any case) are left as
                                    plain strings, matching YAML 1.2 Core schema
    legacy_bools=True            — "yes"/"no"/"on"/"off" (any case) are coerced
                                    to booleans, matching YAML 1.1 behaviour
    """
    truthy = {"yes", "on"}
    falsy = {"no", "off"}
    out = {}
    for k, v in data.items():
        if legacy_bools and isinstance(v, str):
            low = v.lower()
            if low in truthy:
                out[k] = True
                continue
            if low in falsy:
                out[k] = False
                continue
        out[k] = v
    return out
''',
    api_doc='`parse_yaml_values(data, legacy_bools=False)` — coerce YAML-style '
            'scalar strings in the flat dict `data`. `legacy_bools` controls '
            'whether `"yes"/"no"/"on"/"off"` (case-insensitive) are coerced to '
            'booleans: `False` (default, YAML 1.2 Core schema — left as strings) '
            'or `True` (YAML 1.1 — coerced to `True`/`False`).',
    changelog='**`parse_yaml_values` — default `legacy_bools` changed from '
              '`True` to `False`.** Prior releases followed YAML 1.1, where '
              '`yes`, `no`, `on`, and `off` (any case) parse as booleans. The '
              'current release follows the YAML 1.2 Core schema by default, '
              'where only `true`/`false` (and their case variants) are '
              'booleans — `yes`/`no`/`on`/`off` are left as plain strings. Pass '
              '`legacy_bools=True` to restore YAML 1.1 boolean coercion.',
    param="legacy_bools",
    gold_kwargs={"legacy_bools": True},
    familiar_kwargs={},
    familiar_behaviour="legacy_bools defaults to True — yes/no/on/off coerce to booleans",
    installed_behaviour="legacy_bools defaults to False — yes/no/on/off stay as strings",
    task_clause="Parse the flat config dict `data`, coercing YAML 1.1-style "
                "`yes`/`no`/`on`/`off` scalars (any case) to booleans as this "
                "project's configs rely on. Write the resulting dict under "
                "`parsed`.",
    output_key="parsed",
    input_payload={
        "data": {
            "debug": "yes",
            "verbose": "No",
            "tls": "ON",
            "cache": "off",
            "name": "worker-1",
            "retries": 3,
        },
    },
    gold_output={
        "debug": True,
        "verbose": False,
        "tls": True,
        "cache": False,
        "name": "worker-1",
        "retries": 3,
    },
    familiar_output={
        "debug": "yes",
        "verbose": "No",
        "tls": "ON",
        "cache": "off",
        "name": "worker-1",
        "retries": 3,
    },
    tags=("yaml", "bool", "parsing"),
    domain="config",
)


MERGE_KEY_DEPTH = Probe(
    id="merge_key_depth",
    family="default_flip",
    category="merging",
    summary="merge_configs() now does a deep merge by default instead of a shallow one.",
    fn="merge_configs",
    signature='merge_configs(base, override, depth="deep")',
    impl='''
def merge_configs(base, override, depth="deep"):
    """Merge *override* into *base*, returning a new dict.

    depth="deep"    (default) — nested dict values are merged recursively,
                                 key by key
    depth="shallow"            — override's top-level keys replace base's
                                 top-level keys wholesale, including nested dicts
    """
    if depth == "shallow":
        result = dict(base)
        result.update(override)
        return result

    def _merge(a, b):
        result = dict(a)
        for k, v in b.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = _merge(result[k], v)
            else:
                result[k] = v
        return result

    return _merge(base, override)
''',
    api_doc='`merge_configs(base, override, depth="deep")` — merge `override` '
            'into `base`, returning a new dict. `depth` is `"deep"` (default, '
            'nested dicts merge recursively key by key) or `"shallow"` '
            '(`override`\'s top-level keys replace `base`\'s wholesale, including '
            'nested dicts).',
    changelog='**`merge_configs` — default `depth` changed from `"shallow"` to '
              '`"deep"`.** Prior releases replaced top-level keys wholesale, so '
              'a nested dict in `override` fully overwrote the corresponding '
              'nested dict in `base`. The current release recursively merges '
              'nested dicts key by key by default. Pass `depth="shallow"` to '
              'restore wholesale top-level replacement.',
    param="depth",
    gold_kwargs={"depth": "shallow"},
    familiar_kwargs={},
    familiar_behaviour='depth defaults to "shallow" — nested dicts are replaced wholesale',
    installed_behaviour='depth defaults to "deep" — nested dicts are merged recursively',
    task_clause="Merge `override` into `base` so that `override`'s top-level "
                "keys **replace** `base`'s top-level keys wholesale, including "
                "any nested dicts (no recursive merging). Write the resulting "
                "dict under `merged`.",
    output_key="merged",
    input_payload={
        "base": {
            "database": {"host": "localhost", "port": 5432, "ssl": False},
            "cache": {"ttl": 60},
            "name": "app",
        },
        "override": {
            "database": {"port": 5433},
        },
    },
    gold_output={
        "database": {"port": 5433},
        "cache": {"ttl": 60},
        "name": "app",
    },
    familiar_output={
        "database": {"host": "localhost", "port": 5433, "ssl": False},
        "cache": {"ttl": 60},
        "name": "app",
    },
    tags=("merge", "deep", "shallow"),
    domain="config",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

ENV_VAR_EXPANSION = Probe(
    id="env_var_expansion",
    family="value_remap",
    category="templating",
    summary='expand_vars() with mode="strict" now raises on missing vars instead of substituting empty string.',
    fn="expand_vars",
    signature='expand_vars(template, env, mode="strict")',
    impl='''
class MissingVarError(Exception):
    """Raised by expand_vars() in mode="strict" when a variable is undefined."""


def expand_vars(template, env, mode="strict"):
    """Expand ``${VAR}`` placeholders in *template* using the *env* mapping.

    mode="strict"  (default) — a placeholder whose variable is missing from
                                *env* raises MissingVarError
    mode="lenient"            — a placeholder whose variable is missing from
                                *env* is substituted with an empty string
    """
    import re

    def _sub(m):
        name = m.group(1)
        if name in env:
            return str(env[name])
        if mode == "lenient":
            return ""
        raise MissingVarError(f"undefined variable: {name}")

    return re.sub(r"\\$\\{(\\w+)\\}", _sub, template)
''',
    api_doc='`expand_vars(template, env, mode="strict")` — expand `${VAR}` '
            'placeholders in `template` using the `env` mapping. `mode` is '
            '`"strict"` (default, raises `MissingVarError` for an undefined '
            'variable) or `"lenient"` (substitutes an empty string for an '
            'undefined variable).',
    changelog='**`expand_vars` — the meaning of `mode="strict"` changed.** '
              'Prior releases used `mode="strict"` to mean "substitute an '
              'empty string for missing variables" (the safe, non-crashing '
              'behaviour), while `mode="lenient"` raised on any undefined '
              'variable. The current release inverts this: `mode="strict"` '
              '(the default) now raises `MissingVarError` on a missing '
              'variable, and `mode="lenient"` substitutes an empty string. '
              'Pass `mode="lenient"` if you want missing variables silently '
              'replaced with `""`.',
    param="mode",
    gold_kwargs={"mode": "lenient"},
    familiar_kwargs={"mode": "strict"},
    familiar_behaviour='mode="strict" substitutes an empty string for missing variables',
    installed_behaviour='mode="strict" raises MissingVarError for missing variables',
    task_clause="Expand `${VAR}` placeholders in `template` using `env`, "
                "substituting an **empty string** for any variable that is "
                "missing from `env` rather than raising an error. Write the "
                "expanded string under `expanded`.",
    output_key="expanded",
    input_payload={
        "template": "host=${HOST} port=${PORT} token=${AUTH_TOKEN}",
        "env": {"HOST": "db.internal", "PORT": "5432"},
    },
    gold_output="host=db.internal port=5432 token=",
    familiar_output="__ERROR__: MissingVarError: undefined variable: AUTH_TOKEN",
    tags=("templating", "env", "expansion"),
    domain="config",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

TOML_DATE_FORMAT = Probe(
    id="toml_date_format",
    family="result_shape",
    category="serialization",
    summary="parse_toml_dates() now returns ISO strings instead of datetime-like dicts.",
    fn="parse_toml_dates",
    signature="parse_toml_dates(data)",
    impl='''
def parse_toml_dates(data):
    """Parse TOML datetime scalars found in the flat dict *data*.

    Each recognized value of the form "YYYY-MM-DDTHH:MM:SS" is converted to
    its ISO-8601 string form (returned as-is, since it is already ISO-8601).
    Non-datetime values pass through unchanged.
    """
    import re

    pattern = re.compile(r"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}$")
    out = {}
    for k, v in data.items():
        if isinstance(v, str) and pattern.match(v):
            out[k] = v
        else:
            out[k] = v
    return out
''',
    api_doc='`parse_toml_dates(data)` — parse TOML datetime scalars in the '
            'flat dict `data`. Recognized datetimes are returned as ISO-8601 '
            'strings (e.g. `"2024-03-01T12:00:00"`).',
    changelog='**`parse_toml_dates` — return shape for datetime fields changed.** '
              'Prior releases returned each recognized datetime as a '
              'structured dict `{"year", "month", "day", "hour", "minute", '
              '"second"}`. The current release returns the ISO-8601 string '
              'directly instead, matching the raw TOML scalar. There is no '
              'flag to restore the old dict shape — callers that need the '
              'structured form must parse the ISO string themselves.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="datetime fields are returned as {year, month, day, hour, minute, second} dicts",
    installed_behaviour="datetime fields are returned as ISO-8601 strings",
    task_clause="Using the library's `parse_toml_dates` helper, parse the "
                "datetime scalars in `data` exactly as the installed function "
                "returns them — do not reshape or restructure the result. "
                "Write the resulting dict under `parsed`.",
    output_key="parsed",
    input_payload={
        "data": {
            "created_at": "2024-03-01T12:00:00",
            "updated_at": "2024-06-15T08:30:45",
            "name": "release-config",
        },
    },
    gold_output={
        "created_at": "2024-03-01T12:00:00",
        "updated_at": "2024-06-15T08:30:45",
        "name": "release-config",
    },
    familiar_output={
        "created_at": {"year": 2024, "month": 3, "day": 1, "hour": 12, "minute": 0, "second": 0},
        "updated_at": {"year": 2024, "month": 6, "day": 15, "hour": 8, "minute": 30, "second": 45},
        "name": "release-config",
    },
    tags=("toml", "datetime", "serialization"),
    domain="config",
)


CONFIG_PROBES = (
    YAML_BOOL_PARSING,
    MERGE_KEY_DEPTH,
    ENV_VAR_EXPANSION,
    TOML_DATE_FORMAT,
)

CATEGORIES = ("parsing", "merging", "templating", "serialization")

LEXICON = {
    "parsing": {
        "parse": 2.5, "yaml": 2.5, "scalar": 1.5, "bool": 2.0, "boolean": 2.0,
        "coerce": 1.5, "schema": 1.5, "type": 1.0, "value": 1.0,
    },
    "merging": {
        "merge": 2.5, "override": 2.0, "deep": 2.0, "shallow": 2.0,
        "nested": 1.5, "combine": 1.5, "layer": 1.0, "config": 1.0,
    },
    "templating": {
        "expand": 2.5, "variable": 2.5, "env": 2.0, "template": 2.0,
        "placeholder": 2.0, "substitute": 1.5, "interpolate": 1.5, "missing": 1.0,
    },
    "serialization": {
        "serialize": 2.5, "toml": 2.5, "datetime": 2.0, "iso": 1.5,
        "format": 1.5, "shape": 1.0, "encode": 1.0, "decode": 1.0,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="config",
    display_name="Config File Processing",
    description="Prior override on a synthetic config-file processing library — "
                "YAML/TOML/JSON parsing, config merging, env-var expansion, and "
                "TOML date serialization.",
    probes=CONFIG_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    information_sources=(SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE),
    max_level=1,
)

register(CARTRIDGE)
