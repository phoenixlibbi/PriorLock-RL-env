# Environment Diversity

Tunable trial conditions so PriorLock is not overfitting to a single scenario.
Analogues to “number of documents / query complexity” here are **probe count**,
**difficulty band**, **max level**, **domain mix**, and **IRT discrimination**.

## Presets

| Preset | Domains | Level | Difficulty | Min discrimination |
|--------|---------|-------|------------|--------------------|
| `coding` | coding catalog only | 1 | — | 0.0 |
| `diverse` | coding, sql, linux, devtools, fundamentals | 1 | 0.3–0.9 | 0.0 |
| `hard` | same multi-domain mix | 2 | 0.6–0.9 | 0.3 |

```bash
priorlock wrap tasks/my-task --preset diverse
priorlock run --output ./t --preset hard --seed demo
```

```python
from priorlock.env import load_environment
env = load_environment(preset="diverse", num_instances=64)
# or: vf.load_environment("priorlock", preset="diverse")
```

Explicit flags always override the preset (`--domain`, `--level`,
`--difficulty LO-HI`, `--min-discrimination`, `-n`).

## Knobs

| Knob | Wrap / run CLI | `load_environment` |
|------|----------------|--------------------|
| Domain mix | `--domain` (repeatable; `all` expands) | `domains=[...]` |
| Probe count | `-n/--count` | `probes_per_instance` |
| Max level | `--level` | `level` |
| Difficulty band | `--difficulty LO-HI` | `difficulty_range=(lo, hi)` |
| IRT floor | `--min-discrimination` | `min_discrimination` |
| Seed namespace | `--seed-suffix` / `--seed` | `seed_prefix` (train/eval disjoint) |
| Episode count | — | `num_instances`, `eval_fraction` |

Optional file: set `PRIORLOCK_DIVERSITY=/path/to/diversity.toml` (or `.json`).
Kwargs / CLI flags win over the file; the file wins over the preset defaults.

## Notes

- Wrap `--difficulty` / `--min-discrimination` apply on both coding and
  `--domain` paths (cross-domain selector uses the same pool filter).
- Pinned `probe_ids` in the RL env rotate deterministically per instance id
  when the pool is larger than `probes_per_instance`.
- Train vs eval stay disjoint via `plx-train-*` / `plx-eval-*` seed prefixes
 . See also [REPRODUCIBILITY.md](REPRODUCIBILITY.md).
