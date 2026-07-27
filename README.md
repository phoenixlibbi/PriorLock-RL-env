# PriorLock

**PriorLock: A Domain-Agnostic Reinforcement Learning Environment for Measuring
and Training Prior Override in Autonomous Agents**

A Harbor-native RL environment that measures — and can train — whether an agent
overrides stale memorized priors when live environment ground truth contradicts
them. Domain-agnostic by design: wrap any Harbor task; no re-authoring required.

| | |
|---|---|
| **Creator** | [Muhammad Labeeb Tariq](https://github.com/phoenixlibbi) |
| **Email** | [labeebjutt80@gmail.com](mailto:labeebjutt80@gmail.com) |
| **GitHub** | [github.com/phoenixlibbi](https://github.com/phoenixlibbi) |
| **Repository** | [PriorLock-RL-env](https://github.com/phoenixlibbi/PriorLock-RL-env) |

You don't author a PriorLock task. You build an ordinary Harbor task, validate
it, and **convert** it. Keeping those steps separate is what lets you tell a
broken task apart from a broken probe.

```bash
# Install the CLI (Harbor-style — no clone needed)
uv tool install "priorlock @ git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"
# or:  pip install "git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"

priorlock --help
priorlock info

# 1) Prove your Harbor task is sound (expect Mean 1.000)
harbor run -p tasks/my-task -a oracle

# 2) Wrap it — inject prior-override probes
priorlock preflight tasks/my-task
priorlock wrap tasks/my-task --baseline-from jobs/

# 3) Offline gates (no Docker, no API key)
priorlock stage0 tasks/my-task

# 4) Re-run oracle + doctor
harbor run -p tasks/my-task -a oracle
priorlock doctor tasks/my-task
```

### One-command lifecycle (with or without oracle)

```bash
# Full path — baseline + post-wrap + leakprobe via harbor -a oracle
bash harbortasks/run-lifecycle.sh --with-oracle harbortasks/pipeline-drift-calibration-hard

# Fast path — skip all oracle Harbor runs; wrap + gates + model only
# (needs an existing jobs/ oracle trial for --baseline-from)
bash harbortasks/run-lifecycle.sh --without-oracle harbortasks/pipeline-drift-calibration-hard
```

Set `AGENT` / `MODEL` / keys in `harbortasks/model.env`. Default mode can also be
`LIFECYCLE_ORACLE=with|without` (CLI flags override). Details:
[`05-LIFECYCLE.md`](priorlock/docs/05-LIFECYCLE.md).

Once published to PyPI the install becomes simply:

```bash
uv tool install priorlock
# or:  pip install priorlock
```

Contributors who need the full tree: `git clone` then `pip install -e ".[dev]"`.
Full walkthrough: [`05-LIFECYCLE.md`](priorlock/docs/05-LIFECYCLE.md)

---

## The failure mode

Models memorize the APIs they saw during training. When an environment ships a
newer library whose defaults changed, the model confidently applies what it
remembers. No exception is raised. The smoke tests pass. The output is wrong.

The container ships documentation that contradicts common training-data priors.
Code written from memory still runs and still looks right — smoke tests pass —
but the hidden score does not. Reading the in-environment docs is the skill.

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

Dozens of probes across multiple domains and difficulty levels. Exact mechanisms,
IDs, and pass/fail recipes are **not published** — the authoritative specification
is the documentation inside each wrapped task environment.

```bash
priorlock wrap tasks/my-task      # selects probes; authors write nothing
priorlock stage0 tasks/my-task    # offline gates on the generated artefact
```

---

## Why it can't be farmed

Independent defences (several merge-blocking). Public docs intentionally omit
implementation details that would help an attacker. At a high level:

1. Grading uses a verifier-owned library copy — agent-side edits do not help.
2. Scores come from observed behaviour, not agent-written traces.
3. Bypassing the library is worse than being prior-locked.
4. Visible tests do not leak the discriminating signal.
5. Probe sets rotate per task so leaks do not transfer.

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
library <synthetic> · probes: <selected>

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

## Isolation — proven at runtime

A static file-layout check is not isolation. our build rules cites a build
where it passed while the agent could `cat` the oracle on the live box. So the
container gets asked directly.

```bash
priorlock leakprobe <task>                      # generates <task>__leakprobe
harbor run -p <task>__leakprobe -a oracle       # no API key needed
```

```
leak probe: 49 attempts
  positive control: PASS — the agent's own library imports, so absences are meaningful
  oracle reachable from the agent: 0
  runner surface (judged by content, not existence):
    ok   /solution      contains only runner artefacts: probe.py, solve.sh
    ok   /logs/verifier contains only runner artefacts: (empty)
  canary not on the agent surface
  network egress reachable: pypi.org:443, github.com:443, 1.1.1.1:53
    NOTE: the host task declares allow_internet = true — inherited posture,
    measured and reported, not a containment breach.

ISOLATION PROVEN AT RUNTIME
```

12 vectors: `cat`, `find`, `import`, `sys.path`, `pip list`, `walk`, `env`,
`git`, `ps`, `canary`, runner surface, network egress.

Three properties make the trace worth reading:

1. **It is the image under test.** The probe task's `environment/` is copied
   from the host task and asserted **byte-identical by sha256 at build time**.
   Nothing may be added to it — an earlier version wrote the probe in, which
   would have produced a green trace about a different image.
2. **The instrument is verified.** The `import` vector carries a positive
   control: the agent's *own* library must import. A failed control forces
   `INCONCLUSIVE`, **which scores 0.0 exactly like a leak** — a probe that can't
   show it is capable of seeing is not allowed to return a pass.
3. **Content, not existence.** `/solution` and `/logs` exist on any Harbor run.
   The check asks whether host-task oracle assets are sitting in them.

Receipts: [`leakprobe-trace.json`](implementation-progress/receipts/leakprobe-trace.json)
· [`leakprobe-verdict.txt`](implementation-progress/receipts/leakprobe-verdict.txt)

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

`verify` prints per-probe verdicts for a reference solution (gold / familiar /
stub). Exact probe IDs and argument recipes are task-local — do not republish
them in public write-ups.

```
$ priorlock verify tasks/my-task --reference familiar

gap_score 0.4  (familiar.py)
  <probe>   prior_locked   0.40
  …
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

## Author

**Muhammad Labeeb Tariq** · [labeebjutt80@gmail.com](mailto:labeebjutt80@gmail.com) · [@phoenixlibbi](https://github.com/phoenixlibbi)

---

MIT · Created by Muhammad Labeeb Tariq
