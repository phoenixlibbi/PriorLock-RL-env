"""Domain cartridge registry — the extension point for PriorLock generalization.

A *cartridge* packages everything PriorLock needs to measure prior-override in a
specific domain: probes, category lexicon, and display metadata.  The engine
never imports domain logic directly — it receives a ``CartridgeSpec`` and calls
its fields.

Cartridges are discovered automatically:

1. Built-in cartridges in this package (coding, sql, linux, config, cloud,
   finance, math_domain, frontend, backend) are registered at import time.
2. External cartridges installed via ``pip install priorlock-<domain>`` register
   themselves through the ``priorlock.cartridges`` entry-point group.

Usage::

    from priorlock.cartridges import get, list_domains, select_probes_cross

    spec = get("sql")          # CartridgeSpec for the SQL domain
    probes = select_probes_cross(
        task_id="my-task",
        domains=["coding", "sql"],
        count=4,
    )
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from ..probes.base import FAMILIES, Probe

__all__ = [
    "CartridgeSpec", "register", "get", "list_domains",
    "select_probes_cross", "all_probes",
]


# ═════════════════════════════════════════════════════════════════════════════
#  CartridgeSpec
# ═════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CartridgeSpec:
    """Everything a domain cartridge provides to the PriorLock engine.

    The engine's core loop (inject → gate → grade) is identical regardless of
    domain.  The cartridge defines *what* gets injected and *how* the familiar
    prior differs from the documented truth.
    """

    # ── identity ─────────────────────────────────────────────────────────────
    domain: str                          # slug: "coding", "sql", "linux", ...
    display_name: str                    # human: "Python API", "SQL Engine", ...
    description: str                     # one-liner for --help / probe table

    # ── probes ───────────────────────────────────────────────────────────────
    probes: tuple[Probe, ...]            # the domain's probe catalog

    # ── category inference ───────────────────────────────────────────────────
    categories: tuple[str, ...]          # domain-specific category names
    lexicon: dict[str, dict[str, float]] # keyword → weight, per category

    # ── optional overrides ───────────────────────────────────────────────────
    system_prompt_override: str = ""     # if set, replaces the default system prompt
    max_level: int = 1                   # highest L-level any probe in this cartridge reaches

    def __post_init__(self) -> None:
        if not self.domain:
            raise ValueError("domain must be non-empty")
        if not self.probes:
            raise ValueError(f"{self.domain}: cartridge has no probes")
        for p in self.probes:
            if p.domain != self.domain:
                raise ValueError(
                    f"{self.domain}: probe {p.id} declares domain={p.domain!r}"
                )
            if p.category not in self.categories:
                raise ValueError(
                    f"{self.domain}: probe {p.id} declares category={p.category!r}, "
                    f"not in cartridge categories {self.categories!r}"
                )

    @property
    def by_id(self) -> dict[str, Probe]:
        return {p.id: p for p in self.probes}

    @property
    def families_present(self) -> set[str]:
        return {p.family for p in self.probes}

    @property
    def probe_count(self) -> int:
        return len(self.probes)


# ═════════════════════════════════════════════════════════════════════════════
#  Registry
# ═════════════════════════════════════════════════════════════════════════════

_REGISTRY: dict[str, CartridgeSpec] = {}


def register(spec: CartridgeSpec) -> None:
    """Register a cartridge. Overwrites if the domain is already registered."""
    _REGISTRY[spec.domain] = spec


def get(domain: str) -> CartridgeSpec:
    """Return the cartridge for *domain*, or raise KeyError."""
    _ensure_builtins()
    if domain not in _REGISTRY:
        raise KeyError(
            f"unknown domain {domain!r}. "
            f"Available: {', '.join(sorted(_REGISTRY))}"
        )
    return _REGISTRY[domain]


def list_domains() -> list[str]:
    """Return sorted list of registered domain slugs."""
    _ensure_builtins()
    return sorted(_REGISTRY)


def all_probes(domains: list[str] | None = None) -> list[Probe]:
    """Return all probes from the requested domains (or all domains)."""
    _ensure_builtins()
    targets = domains or list(_REGISTRY)
    out: list[Probe] = []
    for d in targets:
        if d in _REGISTRY:
            out.extend(_REGISTRY[d].probes)
    return out


# ═════════════════════════════════════════════════════════════════════════════
#  Cross-cartridge probe selection
# ═════════════════════════════════════════════════════════════════════════════

def select_probes_cross(
    task_id: str,
    domains: list[str] | None = None,
    count: int = 3,
    level: int = 1,
    require_family_diversity: bool = True,
) -> list[Probe]:
    """Select probes across one or more domain cartridges.

    When *domains* spans multiple cartridges, probes are interleaved by domain
    to ensure cross-domain coverage. Family diversity is still enforced within
    the combined pool.
    """
    _ensure_builtins()
    pool = [
        p for p in all_probes(domains)
        if p.level <= level
    ]
    if not pool:
        raise RuntimeError(
            f"no probes at level <= {level} in domains {domains or 'all'}"
        )

    rot = int(hashlib.sha256(task_id.encode()).hexdigest()[:12], 16)

    def sort_key(p: Probe) -> tuple:
        jitter = int(hashlib.sha256(
            f"{task_id}:{p.id}".encode()
        ).hexdigest()[:8], 16) % 1000
        # prefer probes whose domain matches the task_id hash
        domain_rank = hash(p.domain) % 100
        return (domain_rank, jitter)

    chosen: list[Probe] = []

    if require_family_diversity:
        fam_order = list(FAMILIES)
        shift = rot % len(fam_order)
        fam_order = fam_order[shift:] + fam_order[:shift]
        for fam in fam_order:
            if len(chosen) >= count:
                break
            candidates = sorted(
                (p for p in pool if p.family == fam and p not in chosen),
                key=sort_key,
            )
            if candidates:
                chosen.append(candidates[0])

    remaining = sorted(
        (p for p in pool if p not in chosen),
        key=sort_key,
    )
    for p in remaining:
        if len(chosen) >= count:
            break
        # for L2+ probes, pull in dependencies
        if p.dependencies:
            dep_ids = set(p.dependencies)
            chosen_ids = {c.id for c in chosen}
            if not dep_ids.issubset(chosen_ids):
                # pull in missing dependencies if we have room
                by_id = {pp.id: pp for pp in pool}
                missing = [by_id[d] for d in dep_ids - chosen_ids if d in by_id]
                if len(chosen) + len(missing) + 1 <= count:
                    chosen.extend(missing)
                else:
                    continue  # skip this probe — not enough room for deps
        chosen.append(p)

    return chosen[:count]


# ═════════════════════════════════════════════════════════════════════════════
#  Lazy loading of built-in cartridges
# ═════════════════════════════════════════════════════════════════════════════

_BUILTINS_LOADED = False


def _ensure_builtins() -> None:
    """Import all built-in cartridges on first access."""
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    _BUILTINS_LOADED = True

    from . import coding      # noqa: F401
    from . import sql         # noqa: F401
    from . import linux       # noqa: F401
    from . import config      # noqa: F401
    from . import cloud       # noqa: F401
    from . import finance     # noqa: F401
    from . import math_domain # noqa: F401
    from . import frontend    # noqa: F401
    from . import backend     # noqa: F401

    # Load L2 coupled probes and L3 workflow probes, merge into parent cartridges
    from .coupled import ALL_L2_PROBES
    from .workflow import ALL_L3_PROBES
    for probe in (*ALL_L2_PROBES, *ALL_L3_PROBES):
        if probe.domain in _REGISTRY:
            spec = _REGISTRY[probe.domain]
            # Only add if not already present
            if probe.id not in spec.by_id:
                # Rebuild the spec with the extra probe — frozen dataclass
                extended = CartridgeSpec(
                    domain=spec.domain,
                    display_name=spec.display_name,
                    description=spec.description,
                    probes=spec.probes + (probe,),
                    categories=spec.categories,
                    lexicon=spec.lexicon,
                    system_prompt_override=spec.system_prompt_override,
                    max_level=max(spec.max_level, probe.level),
                )
                _REGISTRY[spec.domain] = extended

    # Try loading external cartridges via entry points
    try:
        from importlib.metadata import entry_points
        if hasattr(entry_points, "__call__"):
            try:
                # Python 3.12+ / 3.9+ with select() support
                group = entry_points(group="priorlock.cartridges")
            except TypeError:
                # Python 3.9–3.11 fallback
                eps = entry_points()
                group = eps.get("priorlock.cartridges", [])
        else:
            group = []
        for ep in group:
            try:
                ep.load()
            except Exception:
                pass  # external cartridge failed to load — skip silently
    except ImportError:
        pass
