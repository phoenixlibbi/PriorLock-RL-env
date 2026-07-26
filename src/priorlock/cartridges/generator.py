"""Template-based automatic cartridge generator — no API key required.

Generates complete, validated ``Probe`` objects from declarative specifications.
The generator takes a structured template describing a function's old vs. new
behaviour and mechanically produces everything the engine needs: implementation,
documentation, test data, and grading criteria.

Usage::

    from priorlock.cartridges.generator import ProbeTemplate, generate_probe, generate_cartridge

    # Define a single probe from a template
    template = ProbeTemplate(
        domain="my_domain",
        fn_name="my_function",
        family="default_flip",
        category="processing",
        param_name="mode",
        old_default="sync",
        new_default="async",
        description="Processing mode changed from synchronous to asynchronous",
        implementation=\"\"\"
def my_function(data, mode="async"):
    if mode == "sync":
        return sorted(data)
    return data  # async: preserves insertion order
\"\"\",
        example_input={"data": [3, 1, 2]},
        gold_value="sync",
        gold_output=[1, 2, 3],
        familiar_output=[3, 1, 2],
        task_requirement="Process `data` in **synchronous** mode.",
    )
    probe = generate_probe(template)

    # Or generate a complete cartridge from multiple templates
    cartridge = generate_cartridge(
        domain="my_domain",
        display_name="My Domain",
        description="Custom domain cartridge",
        templates=[template, ...],
        categories=("processing", "validation"),
    )

The generator enforces the same structural invariants as hand-authored probes:
every generated probe is passed through ``Probe.__post_init__`` validation and
must satisfy gold_output != familiar_output. Invalid templates produce clear
error messages, not silent failures.

For automatic generation from API specifications (OpenAPI, man pages, etc.),
see ``generate_from_spec()`` which parses structured API definitions and
proposes mutation candidates.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from ..probes.base import FAMILIES, Probe
from . import CartridgeSpec, register


# ═════════════════════════════════════════════════════════════════════════════
#  ProbeTemplate — the declarative input
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class ProbeTemplate:
    """Declarative specification for generating a single Probe.

    The template describes *what changed* between v1 and v2 of a function.
    The generator fills in documentation, grading criteria, and task wording
    mechanically.
    """

    # ── identity ─────────────────────────────────────────────────────────────
    domain: str                          # e.g. "my_api"
    fn_name: str                         # e.g. "process"
    family: str                          # "default_flip" | "value_remap" | "result_shape"
    category: str                        # e.g. "processing"
    description: str                     # human-readable summary of the change

    # ── implementation ───────────────────────────────────────────────────────
    implementation: str                  # Python source defining the function (v2 semantics)

    # ── for default_flip / value_remap ───────────────────────────────────────
    param_name: str = ""                 # the kwarg that changed (empty for result_shape)
    old_default: Any = None              # what v1 used as default / what the old value meant
    new_default: Any = None              # what v2 uses as default / what the value now means
    gold_value: Any = None               # what a doc-reading agent passes for this param

    # ── test data ────────────────────────────────────────────────────────────
    example_input: Any = None            # input payload (dict)
    gold_output: Any = None              # output when called correctly
    familiar_output: Any = None          # output when using memorized prior

    # ── task wording ─────────────────────────────────────────────────────────
    task_requirement: str = ""           # what the task tells the agent to do
    output_key: str = ""                 # defaults to fn_name + "Result"

    # ── optional ─────────────────────────────────────────────────────────────
    tags: tuple[str, ...] = ()
    probe_id: str = ""                   # auto-generated from domain + fn_name if empty
    level: int = 1
    dependencies: tuple[str, ...] = ()

    def __post_init__(self):
        if self.family not in FAMILIES:
            raise ValueError(f"unknown family {self.family!r}")
        if self.family != "result_shape" and not self.param_name:
            raise ValueError(f"{self.fn_name}: {self.family} requires param_name")
        if not self.output_key:
            self.output_key = self.fn_name + "Result"
        if not self.probe_id:
            self.probe_id = f"{self.domain}_{self.fn_name}"


# ═════════════════════════════════════════════════════════════════════════════
#  Generator — template → Probe
# ═════════════════════════════════════════════════════════════════════════════

def generate_probe(template: ProbeTemplate) -> Probe:
    """Generate a validated Probe from a ProbeTemplate.

    Raises ValueError if the generated probe fails structural validation.
    """
    t = template

    # Derive signature from the implementation
    sig_match = re.search(rf'def\s+{re.escape(t.fn_name)}\s*\([^)]*\)', t.implementation)
    if not sig_match:
        raise ValueError(f"implementation does not define {t.fn_name}()")
    signature = sig_match.group().replace("def ", "", 1)

    # Build family-specific fields
    if t.family == "result_shape":
        param = None
        gold_kwargs: dict = {}
        familiar_kwargs: dict = {}
        familiar_behaviour = f"returns the old output shape"
        installed_behaviour = f"returns the new output shape"
    elif t.family == "default_flip":
        param = t.param_name
        gold_kwargs = {t.param_name: t.gold_value}
        familiar_kwargs = {}
        familiar_behaviour = (
            f'{t.param_name} defaults to {_repr(t.old_default)}'
        )
        installed_behaviour = (
            f'{t.param_name} defaults to {_repr(t.new_default)}'
        )
    else:  # value_remap
        param = t.param_name
        gold_kwargs = {t.param_name: t.gold_value}
        familiar_kwargs = {t.param_name: t.old_default}
        familiar_behaviour = (
            f'{t.param_name}={_repr(t.old_default)} means {t.description.split("instead of")[-1].strip() if "instead of" in t.description else "the old behaviour"}'
        )
        installed_behaviour = (
            f'{t.param_name}={_repr(t.old_default)} now means {t.description.split("now")[1].strip() if "now" in t.description else "the new behaviour"}'
        )

    # Generate documentation
    api_doc = f'`{signature}` — {t.description}'
    if param:
        api_doc += f' `{param}` accepts {_repr(t.new_default)} (default)'
        if t.family == "default_flip":
            api_doc += f' or {_repr(t.gold_value)}.'
        else:
            api_doc += '.'

    changelog = f'**`{t.fn_name}` — '
    if t.family == "default_flip":
        changelog += (
            f'default `{param}` changed from {_repr(t.old_default)} to '
            f'{_repr(t.new_default)}.** '
            f'Pass `{param}={_repr(t.gold_value)}` to restore the previous behaviour.'
        )
    elif t.family == "value_remap":
        changelog += (
            f'`{param}={_repr(t.old_default)}` was redefined.** '
            f'It now means {t.description}. '
            f'Pass `{param}={_repr(t.gold_value)}` for the previous behaviour.'
        )
    else:
        changelog += f'return shape changed.** {t.description}'

    # Task clause
    task_clause = t.task_requirement or (
        f'Call `{t.fn_name}` on the input data and write the result under '
        f'`{t.output_key}`.'
    )

    probe = Probe(
        id=t.probe_id,
        family=t.family,
        category=t.category,
        summary=t.description,
        fn=t.fn_name,
        signature=signature,
        impl=t.implementation,
        api_doc=api_doc,
        changelog=changelog,
        param=param,
        gold_kwargs=gold_kwargs,
        familiar_kwargs=familiar_kwargs,
        familiar_behaviour=familiar_behaviour,
        installed_behaviour=installed_behaviour,
        task_clause=task_clause,
        output_key=t.output_key,
        input_payload=t.example_input,
        gold_output=t.gold_output,
        familiar_output=t.familiar_output,
        tags=t.tags or (t.domain, t.family),
        domain=t.domain,
        level=t.level,
        dependencies=t.dependencies,
    )
    # Probe.__post_init__ validates the structural invariants
    return probe


def _repr(v: Any) -> str:
    """Concise repr for documentation strings."""
    if isinstance(v, str):
        return f'"{v}"'
    return repr(v)


# ═════════════════════════════════════════════════════════════════════════════
#  Cartridge generator — templates[] → CartridgeSpec
# ═════════════════════════════════════════════════════════════════════════════

def generate_cartridge(
    domain: str,
    display_name: str,
    description: str,
    templates: list[ProbeTemplate],
    categories: tuple[str, ...],
    lexicon: dict[str, dict[str, float]] | None = None,
    auto_register: bool = True,
) -> CartridgeSpec:
    """Generate and optionally register a complete CartridgeSpec from templates.

    Every template is validated individually. If any fails, the entire
    cartridge generation is aborted with a clear error.
    """
    probes: list[Probe] = []
    errors: list[str] = []

    for i, t in enumerate(templates):
        try:
            probe = generate_probe(t)
            probes.append(probe)
        except (ValueError, TypeError) as e:
            errors.append(f"template[{i}] ({t.fn_name}): {e}")

    if errors:
        raise ValueError(
            f"Cartridge generation failed for {domain}:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    if not lexicon:
        # Generate a minimal lexicon from category names
        lexicon = {cat: {cat.replace("_", " "): 2.0} for cat in categories}

    spec = CartridgeSpec(
        domain=domain,
        display_name=display_name,
        description=description,
        probes=tuple(probes),
        categories=categories,
        lexicon=lexicon,
        max_level=max(p.level for p in probes) if probes else 1,
    )

    if auto_register:
        register(spec)

    return spec


# ═════════════════════════════════════════════════════════════════════════════
#  Spec-based generation — API definitions → probe candidates
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class APIFunction:
    """A function from an API specification."""
    name: str
    parameters: list[dict]              # [{name, type, default, description}, ...]
    return_type: str = "Any"
    description: str = ""


def identify_mutation_candidates(functions: list[APIFunction]) -> list[dict]:
    """Analyse API functions and propose prior-override mutations.

    For each function with mutable defaults, proposes:
    - default_flip: invert boolean/enum defaults
    - value_remap: reassign enum value meanings
    - result_shape: change return structure

    Returns a list of mutation proposals, each containing enough information
    to fill a ``ProbeTemplate``.
    """
    candidates: list[dict] = []

    for fn in functions:
        for param in fn.parameters:
            default = param.get("default")
            ptype = param.get("type", "")
            pname = param.get("name", "")

            if default is None or pname in ("self", "cls"):
                continue

            # Boolean flip
            if isinstance(default, bool):
                candidates.append({
                    "fn_name": fn.name,
                    "family": "default_flip",
                    "param_name": pname,
                    "old_default": not default,
                    "new_default": default,
                    "gold_value": not default,
                    "mutation": f"flip {pname} from {not default} to {default}",
                    "description": param.get("description", ""),
                })

            # String enum flip
            elif isinstance(default, str) and ptype in ("str", "string", ""):
                candidates.append({
                    "fn_name": fn.name,
                    "family": "default_flip",
                    "param_name": pname,
                    "old_default": f"_{default}_old",  # placeholder
                    "new_default": default,
                    "gold_value": f"_{default}_old",
                    "mutation": f"change default {pname} from old value to {default!r}",
                    "description": param.get("description", ""),
                })

            # Numeric default change
            elif isinstance(default, (int, float)):
                candidates.append({
                    "fn_name": fn.name,
                    "family": "default_flip",
                    "param_name": pname,
                    "old_default": default * 2 if default != 0 else 1,
                    "new_default": default,
                    "gold_value": default * 2 if default != 0 else 1,
                    "mutation": f"change default {pname} from old value to {default}",
                    "description": param.get("description", ""),
                })

        # Result shape mutation for every function
        candidates.append({
            "fn_name": fn.name,
            "family": "result_shape",
            "param_name": None,
            "mutation": f"change return shape of {fn.name}",
            "description": fn.description,
        })

    return candidates


def generate_from_spec(
    domain: str,
    display_name: str,
    functions: list[APIFunction],
    categories: tuple[str, ...] = ("general",),
    max_probes: int = 10,
) -> list[dict]:
    """Analyse an API spec and return mutation candidates.

    This does NOT produce finished probes — it produces structured proposals
    that a human (or LLM with API key) can turn into ``ProbeTemplate`` objects
    by filling in ``implementation``, ``example_input``, ``gold_output``,
    and ``familiar_output``.

    Returns a list of candidate dicts, ranked by mutation quality.
    """
    candidates = identify_mutation_candidates(functions)

    # Rank: prefer boolean flips (cleanest signal), then enum flips, then numeric
    def rank(c: dict) -> int:
        if c["family"] == "result_shape":
            return 2
        if isinstance(c.get("old_default"), bool):
            return 0
        return 1

    candidates.sort(key=rank)
    return candidates[:max_probes]


# ═════════════════════════════════════════════════════════════════════════════
#  CLI helper — `priorlock cartridge generate`
# ═════════════════════════════════════════════════════════════════════════════

def cartridge_table(spec: CartridgeSpec) -> str:
    """Human-readable summary of a cartridge."""
    lines = [
        f"Domain:      {spec.domain}",
        f"Name:        {spec.display_name}",
        f"Description: {spec.description}",
        f"Categories:  {', '.join(spec.categories)}",
        f"Max level:   L{spec.max_level}",
        f"Probes:      {spec.probe_count}",
        "",
        f"{'ID':<35s}  {'FAMILY':<15s}  {'CAT':<15s}  L   SUMMARY",
        f"{'-'*35}  {'-'*15}  {'-'*15}  --  -------",
    ]
    for p in spec.probes:
        lines.append(
            f"{p.id:<35s}  {p.family:<15s}  {p.category:<15s}  "
            f"L{p.level}  {p.summary[:60]}"
        )
    return "\n".join(lines)
