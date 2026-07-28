# Contributing to PriorLock

**PriorLock: A Domain-Agnostic Reinforcement Learning Environment for Measuring
and Training Prior Override in Autonomous Agents**

Created by **Muhammad Labeeb Tariq** · [labeebjutt80@gmail.com](mailto:labeebjutt80@gmail.com) ·
[@phoenixlibbi](https://github.com/phoenixlibbi)

There are three ways to contribute, in descending order of how often they're
needed.

| | What you do | Time |
|---|---|---|
| **1. Wrap a task** | run one command on an existing Harbor task | seconds |
| **2. Add a probe archetype** | extend the catalog — benefits every wrapped task | ~1 hour |
| **3. Author a domain** | build a bespoke synthetic library | ~30 min |

---

## 1. Wrap a task

The common case. You have a Harbor / Terminal-Bench task and you want it to also
measure prior-override capability. You write nothing.

```bash
# users: install the package only
pip install "git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"

# contributors: clone, then editable install
git clone https://github.com/phoenixlibbi/PriorLock-RL-env
cd PriorLock-RL-env
pip install -e ".[dev]"

priorlock wrap tasks/my-task          # inject 3 pre-calibrated probes
priorlock stage0 tasks/my-task        # 12 offline gates — no Docker, no API key
priorlock cheats tasks/my-task        # 8-class cheat battery
```

That's the whole workflow. `wrap` picks probes from the catalog based on your
task's description, generates a synthetic library plus honest in-container docs,
appends a "Part 2" section to `instruction.md`, and rewrites `tests/test.sh` into
a composite verifier that reports both scores.

Your original verifier is preserved as `tests/task_verify.sh` and still runs
first. Harbor reads `reward.txt` or `reward.json`; the composite emits both, so
wrapping is transparent to the runner.

### Useful flags

```bash
priorlock wrap tasks/ --recursive              # wrap an entire suite
priorlock wrap tasks/t -n 5                    # 5 probes instead of 3
priorlock wrap tasks/t --probe dedupe_keep_policy --probe tie_inclusive_topk
priorlock wrap tasks/t --weight-task 0.7 --weight-gap 0.3
priorlock wrap tasks/t --force                 # regenerate with a new probe mix
priorlock unwrap tasks/t                       # remove everything wrap added
```

### Inspecting the result

```bash
priorlock verify tasks/t --reference familiar   # see exactly which args were passed
priorlock verify tasks/t -s my_solution.py      # grade your own attempt
priorlock probes --show tie_inclusive_topk      # full detail on one probe
```

`verify` prints the arguments each call actually supplied. That's the
measurement, so it's worth looking at once to see what the benchmark reads.

---

## 2. Add a probe archetype

The highest-leverage contribution: a new archetype is immediately available to
every wrapped task, present and future.

### What makes a valid archetype

1. **Familiar shape.** Models must have a strong prior about how a function with
   this name and signature behaves. `dedupe(items, key)` qualifies.
   `xq_reduce_v2(handle, ctx)` does not.
2. **Silent.** The prior-locked path must produce **wrong values**, never a crash
   or a type error. If the agent gets a traceback, it will debug and find the
   answer.
3. **Documented.** Reading `docs/<lib>-CHANGELOG.md` must be *sufficient* to
   score 1.0. No puzzles, no hidden state.
4. **Discriminating.** `gold_output != familiar_output`. Enforced in
   `Probe.__post_init__`.

### How to add one

Add a `Probe(...)` to `src/priorlock/probes/catalog.py` and append it to
`ALL_PROBES`. Pick the family that matches your mechanism:

| Family | Mechanism | Signal read from |
|--------|-----------|------------------|
| `default_flip` | a keyword argument's **default** was inverted | call arguments |
| `value_remap` | an accepted value's **meaning** was reassigned | call arguments |
| `result_shape` | the **return shape** changed | output values |

Fill in every field — `impl`, `changelog`, `api_doc`, `task_clause`,
`input_payload`, `gold_output`, `familiar_output`. The docstrings in
`probes/base.py` describe each one.

Then prove it works:

```bash
python3 - <<'PY'
import shutil
from pathlib import Path
from priorlock.inject import wrap_task
from priorlock.gates import run_stage0

d = Path("/tmp/probe-check")
shutil.rmtree(d, ignore_errors=True)
shutil.copytree("tablixdemo/tasks/tablixdemo-0", d)
wrap_task(d, probe_ids=["my_new_probe"], force=True)
raise SystemExit(0 if run_stage0(d).passed else 1)
PY
```

CI runs exactly this for every probe in the catalog on every commit, so a broken
archetype cannot merge.

### Design notes that save time

**Good:**

- `keep`, `order`, `mode`, `nulls`, `remainder` — argument names models assume
  they know the defaults of
- edge-case triggers: null keys, ties, empty input, boundary indices, trailing
  separators
- a `task_clause` that states **what** is required and never **how**

**Bad:**

- changing a signature → `TypeError`, the agent debugs and wins
- a deviation only reachable on input the agent is unlikely to construct
- a `task_clause` that hints at the deviation ("remember that ties are included")
- anything requiring network access or a real published package

---

## 3. Author a domain

Only when you need something the catalog can't express — a domain-specific API
shape, a multi-step deviation, a non-Python target.

```bash
priorlock new-domain mylib     # scaffolds mylib-domain/ with all files pre-wired
priorlock stage0 mylib-domain  # runs the domain's own scripts/stage0.py
```

Checklist after scaffolding:

- [ ] `deviation_spec.yaml` — your 2+ silent deviations, weights summing to 1.0
- [ ] `src/mylib/__init__.py` — v2.0 with deviations present
- [ ] `src/mylib_familiar/__init__.py` — v1.x, Stage-0 only, never shipped
- [ ] `tasks/mylib-0/environment/repo/data/` — input triggering every deviation
- [ ] `.../docs/CHANGELOG.md` — document every deviation; reading it must suffice
- [ ] `.../docs/api_reference.md` — full v2.0 API
- [ ] `.../tests/test_visible.py` — shape/type only, no exact values
- [ ] `.../solution/solve.sh` — gold solution, must score 1.0
- [ ] `.../tests/grade.py` — component weights summing to 1.0
- [ ] `.../tests/expected.json` — exact gold output
- [ ] `scripts/stage0.py` — `GOLD_CODE`, `FAMILIAR_CODE`, inline grade logic

The authored path requires you to hand-derive the 0.40 familiar baseline through
your grader's component weights. This is the step the probe catalog exists to
eliminate — if you find yourself fighting it, check whether an archetype
(contribution type 2) would serve you better.

**Consider contributing the archetype instead.** A domain helps one task; an
archetype helps every task anyone ever wraps.

---

## CI

Offline unit tests (and Stage-0 when configured) run on every PR:

```bash
pip install -e ".[dev]"
export PYTHONHASHSEED=0
pytest -q
```

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the full third-party validate
recipe (`priorlock evaluate`, `stage0`, `priorlock repro`).

Historical Stage-0 workflow notes (when present under `.github/workflows/`):

1. **Catalog gates** — all 13 archetypes wrapped individually and put through all
   12 gates
2. **Wrapped-task gates** — every `priorlock.toml` in the repo, gated
3. **Authored-domain gates** — every `scripts/stage0.py`, run as before

A PR cannot merge unless everything passes.

## Gate reference

| Gate | Check | Requirement |
|------|-------|-------------|
| G1 | gold score | exactly 1.0 |
| G2 | familiar score | exactly 0.40 |
| G3 | stub score | exactly 0.0 |
| G4 | ladder | 0.0 < 0.40 < 1.0, strictly |
| G5 | visible tests | pass for BOTH gold and familiar |
| G6 | canary | no verifier asset reachable from `environment/` |
| G7 | bypass | hand-rolling scores 0.0, not 0.40 |
| G8 | tamper | editing the library is flagged and changes no score |
| G9 | discrimination | every probe separates gold from familiar |
| G10 | host preserved | the original verifier survived migration intact |
| G11 | oracle | the shipped oracle scores 1.0 on the probes |
| G12 | canary | the oracle canary never reaches the agent surface |

## Soundness receipt

The gates prove the ladder holds. The **cheat battery** proves it cannot be
bought without doing the work:

```bash
priorlock cheats tasks/my-task --suite -o receipt.json
```

Eight classes — memorise-visible, oracle-steal, read-internals, tamper-config,
edit-tests, constant-stub, timeout-abuse, self-report. Every cheat carries an
execution marker; one that scores 0 without reaching its exploit path is
excluded from the false-accept denominator rather than counted as caught.

Current pooled receipt: **FAR 0/104, Wilson95 [0.0000, 0.0356]**, worst
surviving cheat 0.0 against a 0.40 baseline.

G7 and G8 are the anti-reward-hacking gates. G7 makes bypassing the library
strictly worse than using it naively; G8 makes editing it pointless because the
verifier grades against its own pristine copy.

Full detail: [`priorlock/docs/04-PROBE-SPEC.md`](priorlock/docs/04-PROBE-SPEC.md).
