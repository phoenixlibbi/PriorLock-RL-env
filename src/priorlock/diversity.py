"""Tunable trial-condition knobs for wrap, standalone, and RL env paths.

PriorLock's analogues to “number of documents / query complexity” are probe
count, difficulty band, max level, domain mix, and IRT discrimination. Named
presets make wide trial conditions one flag instead of tribal knowledge.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

PRESET_NAMES = ("coding", "diverse", "hard")

# Multi-domain mix used by the diverse / hard presets.
_DIVERSE_DOMAINS = ("coding", "sql", "linux", "devtools", "fundamentals")


@dataclass
class DiversityConfig:
    """Explicit trial-condition configuration."""

    num_instances: int = 200
    probes_per_instance: int = 3
    eval_fraction: float = 0.2
    seed_prefix: str = "plx"
    domains: list[str] | None = None
    level: int = 1
    difficulty_range: tuple[float, float] | None = None
    min_discrimination: float = 0.0
    require_family_diversity: bool = True
    exclude: list[str] = field(default_factory=list)
    preset: str | None = None

    def exclude_set(self) -> set[str]:
        return set(self.exclude)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.difficulty_range is not None:
            d["difficulty_range"] = list(self.difficulty_range)
        return d


PRESETS: dict[str, DiversityConfig] = {
    "coding": DiversityConfig(preset="coding"),
    "diverse": DiversityConfig(
        preset="diverse",
        domains=list(_DIVERSE_DOMAINS),
        level=1,
        difficulty_range=(0.3, 0.9),
    ),
    "hard": DiversityConfig(
        preset="hard",
        domains=list(_DIVERSE_DOMAINS),
        level=2,
        difficulty_range=(0.6, 0.9),
        min_discrimination=0.3,
    ),
}


def parse_difficulty(spec: str | None) -> tuple[float, float] | None:
    """Parse ``LO-HI`` (e.g. ``0.6-1.0``) into a float pair."""
    if not spec:
        return None
    try:
        lo_s, hi_s = spec.split("-", 1)
        return (float(lo_s), float(hi_s))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"difficulty must be LO-HI, e.g. 0.6-1.0 (got {spec!r})") from exc


def _from_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize file / env payload keys into DiversityConfig kwargs."""
    out: dict[str, Any] = {}
    for key in (
        "num_instances",
        "probes_per_instance",
        "eval_fraction",
        "seed_prefix",
        "domains",
        "level",
        "min_discrimination",
        "require_family_diversity",
        "exclude",
        "preset",
    ):
        if key in data and data[key] is not None:
            out[key] = data[key]
    if "difficulty_range" in data and data["difficulty_range"] is not None:
        dr = data["difficulty_range"]
        if isinstance(dr, str):
            out["difficulty_range"] = parse_difficulty(dr)
        else:
            lo, hi = dr
            out["difficulty_range"] = (float(lo), float(hi))
    if "exclude" in out and isinstance(out["exclude"], set):
        out["exclude"] = list(out["exclude"])
    return out


def load_diversity_file(path: str | Path) -> dict[str, Any]:
    """Load diversity knobs from a TOML or JSON file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import tomllib
        except ImportError:  # pragma: no cover — py<3.11
            import tomli as tomllib  # type: ignore
        data = tomllib.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"diversity file must be a mapping: {p}")
    return _from_mapping(data)


def file_overrides_from_env() -> dict[str, Any]:
    """If ``PRIORLOCK_DIVERSITY`` is set, load that file's knobs."""
    path = os.environ.get("PRIORLOCK_DIVERSITY")
    if not path:
        return {}
    return load_diversity_file(path)


def resolve_diversity(
    preset: str | None = None,
    *,
    from_env_file: bool = True,
    **overrides: Any,
) -> DiversityConfig:
    """Merge preset → optional env file → explicit kwargs (kwargs win).

    Unknown override keys with value ``None`` are ignored so callers can pass
    argparse defaults without wiping preset values.
    """
    file_bits = file_overrides_from_env() if from_env_file else {}
    # Explicit preset arg beats file's preset name when provided.
    preset_name = preset if preset is not None else file_bits.pop("preset", None)
    if preset_name is None:
        base = DiversityConfig()
    else:
        if preset_name not in PRESETS:
            raise KeyError(
                f"unknown diversity preset {preset_name!r}; "
                f"choose from {', '.join(PRESET_NAMES)}"
            )
        base = replace(PRESETS[preset_name], preset=preset_name)

    merged: dict[str, Any] = {}
    merged.update(file_bits)
    for k, v in overrides.items():
        if v is None:
            continue
        merged[k] = v

    # Normalize types that arrive from CLI / files.
    if "difficulty_range" in merged and isinstance(merged["difficulty_range"], str):
        merged["difficulty_range"] = parse_difficulty(merged["difficulty_range"])
    if "difficulty_range" in merged and isinstance(merged["difficulty_range"], list):
        lo, hi = merged["difficulty_range"]
        merged["difficulty_range"] = (float(lo), float(hi))
    if "exclude" in merged and isinstance(merged["exclude"], (set, tuple)):
        merged["exclude"] = list(merged["exclude"])
    if "domains" in merged and merged["domains"] is not None:
        doms = list(merged["domains"])
        if "all" in doms:
            from .cartridges import list_domains
            merged["domains"] = list(list_domains())

    allowed = {f.name for f in DiversityConfig.__dataclass_fields__.values()}
    clean = {k: v for k, v in merged.items() if k in allowed}
    return replace(base, **clean)
