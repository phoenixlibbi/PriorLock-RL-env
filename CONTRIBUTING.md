# Contributing a Domain to PriorLock

Anyone can add a new domain. A domain is a self-contained cartridge: a synthetic
library + deviation spec + task templates. You don't touch the engine.

## What makes a valid domain

1. **A synthetic library** — never published anywhere, so no training data exists.
   Must have ≥2 functions with silent behavioral deviations from a familiar API shape.
2. **Silent deviations** — the familiar (wrong) solution must not crash or produce
   wrong types. It must produce wrong *values* only. Visible tests must pass for both.
3. **Stage-0 gates pass** — G1 gold=1.0, G2 familiar=0.40, G3 stub=0.0, G4 ladder,
   G5 visible tests pass both paths, G6 oracle files absent from agent surface.

## Quickstart

```bash
# 1. Fork + clone
git clone https://github.com/phoenixlibbi/PriorLock-RL-env
cd PriorLock-RL-env
pip install -e ".[dev]"

# 2. Scaffold your domain
priorlock new-domain mylib
# → creates mylib-domain/ with all files pre-wired, TODOs to fill

# 3. Fill in the TODOs (see checklist below)

# 4. Verify Stage-0 passes
priorlock stage0 mylib-domain

# 5. Submit a PR
```

## Filling in the TODOs (checklist)

After `priorlock new-domain mylib`:

- [ ] `deviation_spec.yaml` — define your ≥2 deviations with trigger, familiar vs
      installed behaviour, and grade weight (must sum to 1.0)
- [ ] `src/mylib/__init__.py` — implement v2.0 with deviations present
- [ ] `src/mylib_familiar/__init__.py` — implement v1.x (no deviations); Stage-0 only
- [ ] `tasks/mylib-0/environment/repo/data/` — add input data that triggers both
      deviations (at least one record per trap)
- [ ] `tasks/mylib-0/environment/repo/docs/CHANGELOG.md` — document both deviations
      clearly; agents who read this must be able to write the gold solution
- [ ] `tasks/mylib-0/environment/repo/docs/api_reference.md` — full API docs for v2.0
- [ ] `tasks/mylib-0/environment/repo/tests/test_visible.py` — smoke tests that pass
      for BOTH familiar and gold solutions (shape/type checks only, no exact values)
- [ ] `tasks/mylib-0/solution/solve.sh` — gold solution (must score 1.0)
- [ ] `tasks/mylib-0/tests/grade.py` — scoring: 0.40×core + 0.30×dev1 + 0.30×dev2
- [ ] `tasks/mylib-0/tests/expected.json` — exact expected output from gold solution
- [ ] `scripts/stage0.py` — fill GOLD_CODE, FAMILIAR_CODE, inline grade logic

## Stage-0 gate requirements

| Gate | Check | Must pass |
|------|-------|-----------|
| G1 | Gold score | 1.0 exactly |
| G2 | Familiar score | 0.40 exactly (±1e-6) |
| G3 | Stub score | 0.0 |
| G4 | Ladder | 0.0 < 0.40 < 1.0 |
| G5 | Visible tests | Pass for BOTH gold and familiar |
| G6 | Canary | grade.py / expected.json / *_familiar absent from environment/ |

G2 is the most important gate. If familiar≠0.40, your deviation isn't in the
"confident but wrong" zone and the prior-override signal won't be valid.

## Deviation design tips

**Good deviation:** familiar API behaviour agents have strong memorized priors about,
but the installed version changes it silently on specific edge-case inputs.

- `group_by` null keys → familiar excludes, installed collects under `"__missing__"`
- `top_n` ties → familiar strict `[:n]` cut, installed returns all tied records
- `sort` stability → familiar unstable, installed stable on equal keys
- `join` null matching → familiar excludes null-key rows, installed treats null as a key

**Bad deviation:**
- Changes function signature (agent gets NameError, not wrong values)
- Only affects inputs the agent is unlikely to use
- Produces a crash or type error (agent debugs and finds it)
- Is so obscure no model has ever seen a similar API

## CI

Every PR that touches a domain directory automatically runs Stage-0 for that
domain via GitHub Actions. The PR cannot be merged unless all 6 gates pass.
