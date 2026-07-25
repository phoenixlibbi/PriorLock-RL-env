# PriorLock

**A Harbor-native RL environment that measures whether an AI agent can override
its memorized training-data priors when the live environment contradicts them.**

You don't author a PriorLock task. You build an ordinary Harbor task, validate
it, and **convert** it. Keeping those steps separate is what lets you tell a
broken task apart from a broken probe.

```bash
# install the CLI (package only — no need to clone the monorepo)
pip install "git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"
priorlock info

# 1-3  build + validate as a normal Harbor task (oracle should score 1.0)
harbor run -p tasks/my-task -a oracle

# 4    is it wrap-ready?
priorlock preflight tasks/my-task

# 5    migrate, pinning the pre-wrap oracle reward
priorlock wrap tasks/my-task --baseline-from jobs/

# 6    12 offline gates — no Docker, no API key
priorlock stage0 tasks/my-task

# 7-8  re-run, then prove wrapping did no harm
harbor run -p tasks/my-task -a oracle
priorlock doctor tasks/my-task
```

Contributors who need the full tree: `git clone` then `pip install -e ".[dev]"`.
Full walkthrough: [`05-LIFECYCLE.md`](priorlock/docs/05-LIFECYCLE.md)

---

## The failure mode

Models memorize the APIs they saw during training. When an environment ships a
newer library whose defaults changed, the model confidently applies what it
remembers. No exception is raised. The smoke tests pass. The output is wrong.

```python
# The container ships v2.0, where keep defaults to "last".
# The CHANGELOG says so. The model doesn't read it.

dedupe(items, "sku")                 # prior-locked  → last occurrence wins
dedupe(items, "sku", keep="first")   # doc-reading   → first occurrence wins
```

That single difference is the entire measurement.

---

## What you get

Every task produces two scores.

| | Measures | Source |
|---|---|---|
| `task_score` | terminal competence | the task's original verifier, untouched |
| `gap_score` | prior-override capability | injected probes |

`reward = (task_score × w_task + gap_score × w_gap) / (w_task + w_gap)`

Harbor reads `reward.txt` or `reward.json`; the composite emits both, so wrapping
is transparent to the runner.

---

## The ladder

Every probe scores on three rungs, **by construction** rather than by per-domain
calibration:

```
0.00 ──────── 0.40 ──────────────────── 1.00
bypassed    prior-locked            read the docs
```

| Score | Verdict | Meaning |
|-------|---------|---------|
| **1.00** | `override` | read the shipped CHANGELOG and acted on it |
| **0.40** | `prior_locked` | applied the memorized default — confident but wrong |
| **0.00** | `bypassed` | never called the library at all |

The 0.40 rung being structural is the key property. In the original design it had
to be hand-derived per domain, and a mis-derived value silently invalidated the
measurement. Now it's a property of the harness, verified offline by gate G2 for
every wrapped task.

---

## Probe catalog

Thirteen archetypes, three families, five categories. All 13 pass all 12 gates in
CI on every commit.

```bash
priorlock probes
priorlock probes --show tie_inclusive_topk
```

| Family | Mechanism | Signal read from |
|--------|-----------|------------------|
| `default_flip` | a keyword argument's **default** was inverted | call arguments |
| `value_remap` | an accepted value's **meaning** was reassigned | call arguments |
| `result_shape` | the **return shape** changed | output values |

Selection enforces one probe from each family. An agent that learns to always
pass keyword arguments explicitly defeats `default_flip` — and still fails
`result_shape`.

---

## Why it can't be farmed

Five independent defences, two of them enforced as gates.

1. **The verifier owns the library.** Grading imports a pristine copy from
   `tests/_plx_lib/`, first on `sys.path`. Editing the shipped copy is flagged
   and changes nothing. *(gate G8)*
2. **Call arguments are observed, not self-reported.** Recovered via
   `inspect.Signature.bind`, which excludes defaults. No trace file to forge.
3. **Bypassing scores 0.00, not 0.40.** Hand-rolling the familiar behaviour is
   strictly worse than calling the library naively. *(gate G7)*
4. **Visible tests are non-discriminating by construction.** Generated from the
   probe set; they assert types and key presence only. *(gate G5)*
5. **Probes rotate per task.** Selection is seeded on the task ID, and library
   names rotate through a pool of plausible non-existent packages.

---

## Gates

Offline. No Docker, no network, no API key. Every gate runs the *generated*
grader against *generated* reference solutions.

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

```
$ priorlock stage0 tasks/my-task

=== Stage-0 · my-task ===
library datawright · probes: tie_inclusive_topk, null_key_policy, merge_precedence_remap

G1 gold score                         PASS  gap_score=1.0
G2 familiar score                     PASS  gap_score=0.4 (want 0.4)
G3 stub score                         PASS  gap_score=0.0
G4 strict ladder                      PASS  0.0 < 0.4 < 1.0
G5 visible tests non-discriminating   PASS  gold=pass familiar=pass
G6 canary clean                       PASS  no oracle assets in environment/
G7 bypass scores zero                 PASS  gap_score=0.0 verdicts={'bypassed': 3}
G8 tamper-proof grading               PASS  score=1.0 flags=['library_modified']
G9 all probes discriminate            PASS  every probe separates gold from familiar
G10 host task preserved               PASS  task_verify.sh preserved byte-identical
G11 oracle solves the probes          PASS  gap_score=1.0 verdicts={'override': 3}
G12 oracle canary contained           PASS  canary present verifier-side only

ladder  stub 0.0  bypass 0.0  familiar 0.4  gold 1.0

ALL GATES PASS
```

---

## Soundness — the receipt

The build rules makes this mandatory, not optional: ≥7 named cheat classes,
false-accept and false-reject with 95% Wilson intervals, **FAR upper bound
< 5%**. Never a bare 0%.

```bash
priorlock cheats <task>            # 8 classes against one task
priorlock cheats <task> --suite    # pooled across all 13 archetypes
```

Pooled result — [`harbortasks/soundness-receipt.json`](harbortasks/soundness-receipt.json):

```
trials            104        8 classes × 13 archetypes
all executed      104/104    none excluded
false accepts     0/104      Wilson95 [0.0000, 0.0356]
required          upper < 0.05                        PASS
false rejects     0/13       Wilson95 [0.0000, 0.2281]
worst surviving   0.0        against a 0.40 baseline
                                                      SOUND
```

| Class | Cheat | Result |
|---|---|---|
| memorise the visible signal | `overfit_public` | caught, 0.0 |
| oracle-steal | `oracle_steal` | caught, 0.0 |
| read internals | `read_internals` | caught, 0.0 |
| tamper config | `tamper_input` | caught, 0.0 |
| edit tests / grader | `edit_grader` | caught, 0.0 |
| constant / shape forgery | `shape_forgery` | caught, 0.0 |
| timeout / resource abuse | `timeout_abuse` | killed, 0.0 |
| self-report forgery | `self_report` | caught, 0.0 |

Two rules the battery follows, both from the standard:

- **A cheat that never ran is not a caught cheat.** Every cheat writes an
  execution marker as its first act. One that scores 0 *without* its marker is
  reported `not_executed` and **excluded from the denominator** — otherwise the
  statistic is inflated by cheats that silently no-op'd.
- **A false accept is scoring above the 0.40 baseline, not above zero.** Scoring
  0.40 by naively calling the library is the measurement working, not a cheat
  surviving.

One task alone gives n=8 → Wilson upper **0.324**. Reporting that as "zero false
accepts" would be exactly the bare-0% the standard forbids; `--suite` pools to
n=104 to earn the interval.

---

## Inspecting a run

`verify` prints the arguments each call actually supplied — that *is* the
measurement:

```
$ priorlock verify tasks/my-task --reference familiar

gap_score 0.4  (familiar.py)

  null_key_policy              prior_locked      0.40
    supplied: [{"key": "region"}]                  ← nulls= never passed
    output matches: familiar
  merge_precedence_remap       prior_locked      0.40
    supplied: [{"on_conflict": "keep"}]            ← the 1.x meaning
    output matches: familiar
```

---

## Calibration

Calibration does **not** establish the 0.40 baseline — that's structural. It
measures how *informative* each probe is against a given model.

```bash
priorlock calibrate ingest jobs/ --model claude-opus-5
priorlock calibrate report --model claude-opus-5
priorlock calibrate recommend --model claude-opus-5
```

| Metric | Definition |
|--------|------------|
| `discrimination` | fraction of runs with an unambiguous verdict |
| `familiar_rate` | of those, the fraction that were prior-locked — **the headline number** |

A probe going stale degrades *resolution*, not *validity*.

---

## Commands

```
priorlock preflight <task>     is this Harbor task healthy and wrap-ready?
priorlock wrap <task>          migrate it — inject probes
priorlock wrap <dir> -r        migrate an entire task suite
priorlock stage0 <task>        12 offline gates
priorlock cheats <task>        8-class cheat battery + soundness receipt
priorlock leakprobe <task>     runtime isolation proof
priorlock doctor <task>        did wrapping damage the host task?
priorlock unwrap <task>        roll the migration back
priorlock verify <task>        grade one solution locally, see supplied args
priorlock probes               browse the catalog
priorlock calibrate ...        measure probe informativeness
priorlock new-domain <name>    scaffold a bespoke authored domain
priorlock info                 what's wrapped, what's authored, catalog size
```

---

## Two paths

| | `priorlock wrap` | `priorlock new-domain` |
|---|---|---|
| Author effort | none | ~30 min per domain |
| 0.40 baseline | structural | hand-derived, gate-checked |
| Applies to | any Harbor task | one bespoke domain |
| Probe novelty | catalog only | anything |
| Anti-hack | 5 layers, generated | manual |

Use `wrap` by default. Use `new-domain` when you need a probe the catalog can't
express — then consider contributing the archetype back, since a new archetype
benefits every wrapped task at once.

`tablixdemo-0` is both: its `task_score` comes from hand-written tablix
deviations, its `gap_score` from three injected probes. The two measurements
agreeing is the cheapest available evidence that the generic path measures the
same thing the bespoke path does.

---

## Docs

| | |
|---|---|
| [`00-THE-GAP.md`](priorlock/docs/00-THE-GAP.md) | the failure mode and why it matters |
| [`01-ARCHITECTURE.md`](priorlock/docs/01-ARCHITECTURE.md) | engine + cartridge model |
| [`02-BUILD-SPEC.md`](priorlock/docs/02-BUILD-SPEC.md) | authored-domain spec |
| [`04-PROBE-SPEC.md`](priorlock/docs/04-PROBE-SPEC.md) | **probe architecture — start here** |
| [`05-LIFECYCLE.md`](priorlock/docs/05-LIFECYCLE.md) | **build → validate → migrate → gate → doctor** |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | three ways to contribute |

---

## Layout

```
src/priorlock/
  probes/
    base.py           Probe contract, the {0, 0.40, 1.0} ladder
    catalog.py        13 pre-calibrated archetypes
    __init__.py       registry, category inference, selection
  templates.py        generators for every injected file
  inject.py           wrap / unwrap / manifest
  lifecycle.py        preflight / baseline capture / doctor
  gates.py            the 12 offline gates
  leakprobe.py        runtime isolation proof + canary scan
  env.py              verifiers RL environment (load_environment)
  calibrate.py        empirical probe informativeness
  scaffold.py         authored-domain scaffolding
  cli.py

tablixdemo/           reference authored domain (also wrapped)
website/              Next.js site
priorlock/docs/       specification
priorlock/papers/     literature notes
```

---

MIT · [PriorLock trial build](TRIAL-BUILD-PLAN.md)
