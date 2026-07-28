"""Environment diversity: presets, cross-domain filters, instance rotation."""
from __future__ import annotations

from priorlock.cartridges import select_probes_cross
from priorlock.diversity import PRESETS, resolve_diversity
from priorlock.env import build_instances
from priorlock.probes import BY_ID


def test_resolve_diverse_preset():
    cfg = resolve_diversity("diverse", from_env_file=False)
    assert cfg.preset == "diverse"
    assert cfg.domains is not None
    assert "coding" in cfg.domains and "sql" in cfg.domains
    assert cfg.difficulty_range == (0.3, 0.9)
    assert cfg.level == 1


def test_resolve_hard_preset_overrides():
    cfg = resolve_diversity(
        "hard",
        from_env_file=False,
        level=1,
        min_discrimination=0.0,
    )
    assert cfg.level == 1  # explicit override
    assert cfg.min_discrimination == 0.0
    assert cfg.difficulty_range == (0.6, 0.9)
    assert set(PRESETS["hard"].domains or ()) <= set(cfg.domains or ())


def test_filter_pool_difficulty_band_catalog():
    from priorlock.probes import ALL_PROBES, filter_probe_pool

    band = filter_probe_pool(list(ALL_PROBES), difficulty_range=(0.6, 1.0))
    assert band
    assert all(0.6 <= p.difficulty <= 1.0 for p in band)


def test_cross_domain_difficulty_fallthrough_when_band_empty():
    # Cartridge probes currently default difficulty=0.5; a 0.6–1.0 band would
    # empty the pool, so filter_probe_pool falls through rather than failing.
    probes = select_probes_cross(
        task_id="diff-band-a",
        domains=["coding", "sql"],
        count=3,
        level=2,
        difficulty_range=(0.6, 1.0),
        min_discrimination=0.0,
    )
    assert len(probes) == 3


def test_cross_domain_exclude():
    probes = select_probes_cross(
        task_id="exclude-a",
        domains=["coding"],
        count=3,
        level=1,
        exclude={"dedupe_keep_policy"},
    )
    assert all(p.id != "dedupe_keep_policy" for p in probes)


def test_diverse_preset_multi_domain_batch():
    cfg = resolve_diversity("diverse", from_env_file=False)
    rows = build_instances(
        num_instances=12,
        probes_per_instance=3,
        seed_prefix="div",
        domains=cfg.domains,
        level=cfg.level,
        difficulty_range=cfg.difficulty_range,
        min_discrimination=cfg.min_discrimination,
    )
    from priorlock.probes import all_probes_by_id

    merged = {**BY_ID, **all_probes_by_id(cfg.domains)}
    domains_seen: set[str] = set()
    for row in rows:
        for p in row["info"]["probes"]:
            probe = merged.get(p["id"])
            if probe is not None:
                domains_seen.add(probe.domain)
    assert len(domains_seen) >= 2, domains_seen


def test_probe_ids_rotate_across_instances():
    ids = [
        "dedupe_keep_policy",
        "sort_direction_default",
        "range_end_inclusive",
        "merge_precedence_remap",
        "null_sentinel_policy",
    ]
    # Keep only ids that exist
    ids = [i for i in ids if i in BY_ID]
    assert len(ids) >= 4
    rows = build_instances(
        num_instances=8,
        probes_per_instance=2,
        seed_prefix="pin",
        probe_ids=ids,
    )
    mixes = [tuple(p["id"] for p in row["info"]["probes"]) for row in rows]
    assert len(set(mixes)) >= 2, mixes
