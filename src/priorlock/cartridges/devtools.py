"""Developer toolkit cartridge — source-code-only prior override measurement.

Five probes targeting common developer utility patterns where LLMs have strong
memorized priors: environment variable fallback values, log level thresholds,
JSON formatting conventions, rounding modes, and tokenizer return shapes.

**Source-code-only design (1-source).** This cartridge declares only
``source_code`` as its information source.  No changelog and no API reference
are emitted into the agent container.  The model must discover API behaviour
purely by reading the library source — the ``ExploraCoder`` /
``CodeUpdateArena`` paradigm.

Because there is no second information source, the injection engine writes
library defaults in cleartext (``hide_defaults=False``).  The structural
{0.00, 0.40, 1.00} ladder still works: a model that reads the source and
trusts it scores 1.0; a model that ignores the source and applies its
training prior scores 0.40.

**Shadow naming:** function names (``get_env``, ``log_filter``,
``pretty_print``, ``round_values``, ``tokenize``) deliberately shadow
well-known stdlib / utility APIs so the model's training prior fires on the
call shape.

**Context priming:** each probe carries a ``CONTEXT_SNIPPETS`` entry — a
realistic code fragment that uses the function with familiar (prior)
semantics.  These are planted in the repo during ``wrap`` to reinforce the
model's memorized expectations before it reads the library source.
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register, SOURCE_CODE


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

ENV_FALLBACK = Probe(
    id="env_fallback",
    family="default_flip",
    category="environment",
    summary='get_env() now returns "UNSET" by default when a key is missing, not None.',
    fn="get_env",
    signature='get_env(mapping, name, fallback="UNSET")',
    impl='''
def get_env(mapping, name, fallback="UNSET"):
    """Look up *name* in *mapping* (simulates environment variable lookup).

    fallback="UNSET"  (default) — return the string "UNSET" when key is absent
    fallback=None                — return None when key is absent
    fallback=<any>               — return that value when key is absent
    """
    return mapping.get(name, fallback)
''',
    api_doc='`get_env(mapping, name, fallback="UNSET")` — look up `name` in '
            '`mapping`. Returns `fallback` when the key is absent. '
            'Default fallback is the string `"UNSET"`, not `None`.',
    changelog='**`get_env` — default `fallback` changed from `None` to '
              '`"UNSET"`.** Prior releases returned `None` for missing keys '
              '(matching `os.environ.get()`). The current release returns '
              'the string `"UNSET"` by default. Pass `fallback=None` to '
              'restore the previous behaviour.',
    param="fallback",
    gold_kwargs={"fallback": None},
    familiar_kwargs={},
    familiar_behaviour="fallback defaults to None — missing keys return None",
    installed_behaviour='fallback defaults to "UNSET" — missing keys return the string "UNSET"',
    task_clause="Look up `name` in `mapping`. If the key is missing, the result "
                "should be `None` (not a string). Write the result under `env`.",
    output_key="env",
    input_payload={
        "mapping": {"HOME": "/home/user", "PATH": "/usr/bin", "LANG": "en_US"},
        "name": "MISSING_KEY",
    },
    gold_output=None,
    familiar_output="UNSET",
    tags=("environment", "fallback", "get_env", "none"),
    domain="devtools",
)


LOG_LEVEL = Probe(
    id="log_level",
    family="default_flip",
    category="logging",
    summary='log_filter() now defaults to min_level="debug" instead of "info".',
    fn="log_filter",
    signature='log_filter(entries, min_level="debug")',
    impl='''
def log_filter(entries, min_level="debug"):
    """Filter log *entries* keeping those at or above *min_level*.

    Level ordering: debug(0) < info(1) < warn(2) < error(3).

    min_level="debug"  (default) — keep everything including debug
    min_level="info"             — drop debug entries
    min_level="warn"             — drop debug and info
    min_level="error"            — keep only errors
    """
    levels = {"debug": 0, "info": 1, "warn": 2, "error": 3}
    threshold = levels.get(min_level, 0)
    return [e for e in entries if levels.get(e.get("level", "debug"), 0) >= threshold]
''',
    api_doc='`log_filter(entries, min_level="debug")` — filter log entries. '
            '`min_level` sets the floor: `"debug"` (default, keeps all), '
            '`"info"`, `"warn"`, or `"error"`.',
    changelog='**`log_filter` — default `min_level` changed from `"info"` to '
              '`"debug"`.** Prior releases filtered out debug entries by '
              'default. The current release keeps everything including debug. '
              'Pass `min_level="info"` to drop debug entries.',
    param="min_level",
    gold_kwargs={"min_level": "info"},
    familiar_kwargs={},
    familiar_behaviour='min_level defaults to "info" — debug entries are dropped',
    installed_behaviour='min_level defaults to "debug" — all entries including debug are kept',
    task_clause="Filter `entries` keeping only those at level **info or above** "
                "(drop debug entries). Write the result under `logs`.",
    output_key="logs",
    input_payload={
        "entries": [
            {"msg": "starting up", "level": "debug"},
            {"msg": "connected", "level": "info"},
            {"msg": "high latency", "level": "warn"},
            {"msg": "retrying", "level": "debug"},
            {"msg": "request ok", "level": "info"},
        ],
    },
    gold_output=[
        {"msg": "connected", "level": "info"},
        {"msg": "high latency", "level": "warn"},
        {"msg": "request ok", "level": "info"},
    ],
    familiar_output=[
        {"msg": "starting up", "level": "debug"},
        {"msg": "connected", "level": "info"},
        {"msg": "high latency", "level": "warn"},
        {"msg": "retrying", "level": "debug"},
        {"msg": "request ok", "level": "info"},
    ],
    tags=("logging", "filter", "level", "debug", "log_filter"),
    domain="devtools",
)


PRETTY_INDENT = Probe(
    id="pretty_indent",
    family="default_flip",
    category="formatting",
    summary="pretty_print() now defaults to 4-space indentation instead of 2.",
    fn="pretty_print",
    signature="pretty_print(obj, indent=4)",
    impl='''
def pretty_print(obj, indent=4):
    """Format *obj* as a human-readable JSON string.

    indent=4  (default) — four spaces per nesting level
    indent=2            — two spaces per nesting level
    indent=0            — no indentation (compact)
    """
    import json
    return json.dumps(obj, indent=indent, sort_keys=True, ensure_ascii=False)
''',
    api_doc='`pretty_print(obj, indent=4)` — JSON-format `obj` with `indent` '
            'spaces per nesting level. Default is `4` spaces.',
    changelog='**`pretty_print` — default `indent` changed from `2` to `4`.** '
              'Prior releases used 2-space indentation (matching common JSON '
              'convention). The current release uses 4 spaces by default. '
              'Pass `indent=2` to restore 2-space formatting.',
    param="indent",
    gold_kwargs={"indent": 2},
    familiar_kwargs={},
    familiar_behaviour="indent defaults to 2 — standard 2-space JSON formatting",
    installed_behaviour="indent defaults to 4 — wider 4-space JSON formatting",
    task_clause="Format `obj` as a JSON string with **2-space** indentation. "
                "Write the result under `formatted`.",
    output_key="formatted",
    input_payload={"obj": {"name": "test", "value": 42}},
    gold_output='{\n  "name": "test",\n  "value": 42\n}',
    familiar_output='{\n    "name": "test",\n    "value": 42\n}',
    tags=("formatting", "json", "indent", "pretty_print"),
    domain="devtools",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

ROUND_MODE = Probe(
    id="round_mode",
    family="value_remap",
    category="arithmetic",
    summary='round_values()\'s mode="half_up" now means round-away-from-zero, '
            'not banker\'s rounding.',
    fn="round_values",
    signature='round_values(values, decimals, mode="half_up")',
    impl='''
def round_values(values, decimals, mode="half_up"):
    """Round each value in *values* to *decimals* decimal places.

    mode="half_even" — banker's rounding: ties go to the nearest even digit
                        (matches Python's built-in round())
    mode="half_up"   (default) — round ties away from zero (school rounding)
    mode="truncate"  — truncate toward zero (drop fractional digits)
    """
    import decimal as _dec
    results = []
    for v in values:
        d = _dec.Decimal(str(v))
        if mode == "truncate":
            factor = _dec.Decimal(10) ** decimals
            results.append(float(int(d * factor) / factor))
        elif mode == "half_even":
            results.append(float(round(v, decimals)))
        else:  # "half_up"
            quant = _dec.Decimal(10) ** -decimals if decimals > 0 else _dec.Decimal(1)
            results.append(float(d.quantize(quant, rounding=_dec.ROUND_HALF_UP)))
    return results
''',
    api_doc='`round_values(values, decimals, mode="half_up")` — round each '
            'value to `decimals` places. `mode="half_even"` for banker\'s '
            'rounding (Python `round()`). `mode="half_up"` (default) rounds '
            'ties away from zero. `mode="truncate"` truncates toward zero.',
    changelog='**`round_values` — the `mode="half_up"` value was redefined.** '
              'Prior releases treated `"half_up"` as equivalent to Python\'s '
              'built-in `round()` (banker\'s rounding / half-to-even). The '
              'current release makes `"half_up"` do true round-half-up '
              '(away from zero). Use `mode="half_even"` for Python-style '
              'banker\'s rounding.',
    param="mode",
    gold_kwargs={"mode": "half_even"},
    familiar_kwargs={"mode": "half_up"},
    familiar_behaviour='mode="half_up" means Python-style banker\'s rounding (half_even)',
    installed_behaviour='mode="half_up" means round-half-away-from-zero (school rounding)',
    task_clause="Round `values` to `decimals` places using **Python's standard "
                "rounding** (banker's rounding / half-to-even, where ties round "
                "to the nearest even digit). Write the result under `rounded`.",
    output_key="rounded",
    input_payload={"values": [2.5, 3.5, 4.5, -1.5], "decimals": 0},
    gold_output=[2.0, 4.0, 4.0, -2.0],
    familiar_output=[3.0, 4.0, 5.0, -2.0],
    tags=("rounding", "decimal", "banker", "half-up", "round_values"),
    domain="devtools",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

TOKENIZE_SHAPE = Probe(
    id="tokenize_shape",
    family="result_shape",
    category="text",
    summary="tokenize() now returns a dict with tokens and count, not a flat list.",
    fn="tokenize",
    signature="tokenize(text, sep=None)",
    impl='''
def tokenize(text, sep=None):
    """Split *text* on *sep* (default: whitespace).

    Returns a dict with two fields:
      - "tokens": the list of split parts
      - "count": how many tokens were produced

    This differs from Python's str.split() which returns a plain list.
    """
    parts = text.split(sep) if sep else text.split()
    return {"tokens": parts, "count": len(parts)}
''',
    api_doc='`tokenize(text, sep=None)` — split `text` on `sep`, returning '
            '`{"tokens": [str, ...], "count": int}` (a dict, not a list).',
    changelog='**`tokenize` now returns a dict, not a list.** '
              'Prior releases returned `text.split(sep)` — a plain list of '
              'strings (matching Python\'s `str.split()`). The current release '
              'returns `{"tokens": [...], "count": N}`. Callers that expected '
              'a list must index `["tokens"]` to get the token list.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="returns a plain list of strings (like str.split())",
    installed_behaviour='returns {"tokens": [...], "count": N}',
    task_clause="Split `text` on `sep` using the library's `tokenize` helper. "
                "Write the **complete return value** from the library, unmodified, "
                "under `tokenized`.",
    output_key="tokenized",
    input_payload={"text": "the quick brown fox", "sep": " "},
    gold_output={"tokens": ["the", "quick", "brown", "fox"], "count": 4},
    familiar_output=["the", "quick", "brown", "fox"],
    tags=("tokenize", "split", "text", "result-shape"),
    domain="devtools",
)


# ═════════════════════════════════════════════════════════════════════════════
#  Context priming snippets (1.x-style usage to reinforce model priors)
# ═════════════════════════════════════════════════════════════════════════════

CONTEXT_SNIPPETS = {
    "env_fallback": '''
def load_database_url():
    """Read DB connection string from environment."""
    url = {lib}.get_env(os.environ, "DATABASE_URL")
    if url is None:
        return "sqlite:///default.db"
    return url
''',
    "log_level": '''
def get_application_logs(raw_entries):
    """Filter to application-level messages (info+)."""
    return {lib}.log_filter(raw_entries)  # default drops debug noise
''',
    "pretty_indent": '''
def save_config(config, path):
    """Dump config as formatted JSON."""
    with open(path, "w") as f:
        f.write({lib}.pretty_print(config))  # standard 2-space JSON
''',
    "round_mode": '''
def display_prices(raw_prices):
    """Round prices for display (standard Python rounding)."""
    return {lib}.round_values(raw_prices, 2)  # half_up = standard rounding
''',
    "tokenize_shape": '''
def word_count(text):
    """Count the number of words in text."""
    return len({lib}.tokenize(text, " "))  # tokenize returns a list
''',
}


# ═════════════════════════════════════════════════════════════════════════════
#  Assembly
# ═════════════════════════════════════════════════════════════════════════════

DEVTOOLS_PROBES = (
    ENV_FALLBACK,
    LOG_LEVEL,
    PRETTY_INDENT,
    ROUND_MODE,
    TOKENIZE_SHAPE,
)

CATEGORIES = ("environment", "logging", "formatting", "arithmetic", "text")

LEXICON = {
    "environment": {
        "env": 2.5, "variable": 2.0, "config": 1.5, "setting": 1.5,
        "lookup": 2.0, "get": 1.0, "missing": 1.5, "default": 1.5,
    },
    "logging": {
        "log": 2.5, "filter": 2.0, "level": 2.5, "debug": 2.0,
        "info": 2.0, "warn": 2.0, "error": 2.0, "severity": 1.5,
    },
    "formatting": {
        "format": 2.5, "json": 2.0, "pretty": 2.0, "indent": 2.5,
        "print": 1.5, "output": 1.0, "style": 1.0, "serialize": 1.5,
    },
    "arithmetic": {
        "round": 2.5, "decimal": 2.0, "precision": 2.0, "math": 1.5,
        "number": 1.0, "truncate": 2.0, "banker": 2.0, "even": 1.5,
    },
    "text": {
        "token": 2.5, "split": 2.5, "parse": 2.0, "word": 1.5,
        "delimiter": 2.0, "separator": 2.0, "text": 1.5, "string": 1.0,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="devtools",
    display_name="Developer Toolkit",
    description="Prior override via source-code-only reading — env variables, "
                "log filtering, JSON formatting, rounding modes, and tokenizer "
                "return shapes. 1-source domain: no changelog or API docs, only "
                "library source code. Based on CodeUpdateArena / ExploraCoder.",
    probes=DEVTOOLS_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    # 1-source: source code only — no changelog, no API docs
    information_sources=(SOURCE_CODE,),
    max_level=1,
)

register(CARTRIDGE)
