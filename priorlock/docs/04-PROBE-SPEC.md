# PriorLock Probe Specification v1

> **Status:** implemented and gate-verified.
> Supersedes the per-domain authoring requirement described in `02-BUILD-SPEC.md`,
> which remains supported as the "authored domain" path.

---

## 0. The problem this solves

The original PriorLock design required every task author to invent a *silent
deviation*: a behavioural change to a synthetic library that a model would get
wrong confidently. That works, and `tablixdemo` proves it. But it does not scale,
for three reasons:

1. **It is a research skill, not an authoring skill.** Most people who can write
   a good Terminal-Bench task have no idea where a model's prior is
   miscalibrated. Asking them to guess produces deviations that are either too
   obvious (every model reads the docs, gap collapses to zero) or too obscure (no
   prior exists, gap collapses to zero).

2. **The 0.40 baseline had to be re-derived per domain.** Gate G2 checked that a
   prior-locked solution scored exactly 0.40, but reaching that number required
   hand-tuning the grader's component weights against a hand-written familiar
   solution. Get it wrong and the gate still passes while measuring nothing.

3. **It couldn't ride along.** A deviation lived inside a bespoke domain. There
   was no way to ask "what is the prior-override score of this model on an
   *existing* benchmark suite?"

The probe architecture removes all three constraints. Task authors write nothing.

---

## 1. Core claim

> Every probe yields exactly three scores **by construction**, not by empirical
> calibration:
>
> | Score | Meaning |
> |-------|---------|
> | **1.00** | agent read the shipped documentation and acted on it |
> | **0.40** | agent applied its memorized prior — confident but wrong |
> | **0.00** | agent bypassed, tampered, crashed, or produced garbage |

Because the 0.40 rung is structural, **G2 is now a property of the harness rather
than a property of the domain.** Verifying it for a new task is a 30-second
offline check, not a research project.

`FAMILIAR_BASELINE = 0.40` lives in exactly one place: `probes/base.py`.

---

## 2. What a probe measures

A probe measures **one act of verification**: did the agent check what the
environment actually does before relying on what it remembers?

Every probe pairs

- a **synthetic library function** whose *shape* is familiar (the model has seen
  a thousand `dedupe(items, key)` calls) but whose *behaviour* has changed, with
- an **in-container document** that states the change plainly, and
- a **task requirement** that the memorized behaviour fails.

Reading the CHANGELOG is always sufficient to score 1.0. There is no trick, no
hidden state, and no puzzle. The only way to fail is to not look.

---

## 3. The three families

### 3.1 `default_flip`

A keyword argument exists in both versions; its **default value** was inverted.

```python
# shipped: v2.0
dedupe(items, key, keep="last")     # 1.x default was "first"
```

The task requires first-occurrence semantics.

| Agent | Call | Result |
|-------|------|--------|
| Prior-locked | `dedupe(items, "sku")` | last wins — **0.40** |
| Doc-reading | `dedupe(items, "sku", keep="first")` | first wins — **1.00** |

**Signal source: call arguments.** This is the strongest family. There is no
accidental answer — either `keep="first"` appears in the observed call or it
does not.

### 3.2 `value_remap`

The argument and all its accepted values still exist, but one value's **meaning**
was reassigned.

```python
# shipped: v2.0
merge(base, patch, on_conflict="keep")   # "keep" now means keep the NEWER value
                                         # 1.x: "keep" meant keep the EXISTING value
```

| Agent | Call | Result |
|-------|------|--------|
| Prior-locked | `on_conflict="keep"` | patch wins — **0.40** |
| Doc-reading | `on_conflict="keep_left"` | base wins — **1.00** |

**Signal source: call arguments.** Harder than `default_flip` because passing
arguments defensively is not enough — the agent has to read what the value
*means*.

### 3.3 `result_shape`

No argument changed; the **return shape** did. The agent must not "sanity-correct"
the result back to what it expects.

```python
top_k(records, 3, "amount")   # tie-inclusive: may return MORE than 3 records
```

| Agent | Behaviour | Result |
|-------|-----------|--------|
| Prior-locked | slices `[:3]` because "top 3 means 3" | **0.40** |
| Doc-reading | reports all tied records | **1.00** |

**Signal source: output values.** Catches a failure mode the argument-based
families cannot: an agent that calls correctly and then post-processes according
to its prior.

**Why all three.** An agent that learns to always pass every keyword argument
explicitly defeats `default_flip` — and still fails `result_shape`. Selection
enforces family diversity for exactly this reason.

---

## 4. Scoring

```
per probe:
    not invoked                                  -> 0.00   bypassed
    output == gold      AND call is gold         -> 1.00   override
    output == familiar                           -> 0.40   prior_locked
    call is gold        BUT output is neither    -> 0.00   correct_call_bad_output
    otherwise                                    -> 0.00   incorrect

gap_score  = weighted mean of per-probe scores
task_score = whatever the task's original verifier produced
reward     = (task_score * w_task + gap_score * w_gap) / (w_task + w_gap)
```

Default weights are `0.5 / 0.5`, set per task in `priorlock.toml`. Setting
`w_task = 1.0, w_gap = 0.0` turns a wrapped task back into a plain benchmark task
whose probe results are still recorded for calibration.

**Full credit requires both signals to agree.** Guessing the expected output
without making the correct call does not score.

---

## 5. Anti-reward-hacking

Five independent defences. Each closes an attack that the others do not.

### 5.1 The verifier owns the library

Grading imports a **pristine copy** shipped in `tests/_plx_lib/` and places it
first on `sys.path`. Whatever the agent did to the repo copy is irrelevant to the
measurement. Editing it is reported as a `library_modified` flag but changes no
score.

> Gate **G8** proves this: the harness rewrites the shipped library and asserts
> that a gold solution still scores 1.0 *and* that the flag was raised.

### 5.2 Call arguments are observed, not self-reported

Each probe function is wrapped by the verifier and the arguments the solution
*explicitly supplied* are recovered via `inspect.Signature.bind`, which excludes
defaults. There is no trace file to forge and no log the agent can write to.

Positional and keyword calls are both captured; `dedupe(x, "sku", "first")` and
`dedupe(x, "sku", keep="first")` are treated identically, as they should be.

### 5.3 Bypassing scores zero, not 0.40

An agent that reimplements the function instead of calling it never reaches the
prior-locked rung. **Hand-rolling the familiar behaviour is strictly worse than
calling the library naively**, which removes the incentive to avoid the library
entirely.

> Gate **G7** proves this: a reference solution that hard-codes the familiar
> answers without importing the library must score 0.0 with every probe reporting
> `bypassed`.

### 5.4 Visible tests are non-discriminating by construction

`test_probe_visible.py` asserts container types and key presence only. It is
generated from the probe set, so it cannot accidentally leak a value. Gate **G5**
verifies that gold and familiar solutions both pass it.

### 5.5 Probes rotate per task

Probe selection is seeded on the task ID. A leaked answer for one task is
worthless for the next, and a suite wrapped with `--recursive` gets a different
probe mix per task. Library names rotate through a pool of plausible non-existent
package names, so grep-based memorisation across tasks fails too.

---

## 6. Selection

```
select_probes(task_id, text, count=3)
```

1. **Family diversity first** — one probe from each of `default_flip`,
   `value_remap`, `result_shape` before doubling up. A mixed set cannot be
   defeated by a single behavioural heuristic.
2. **Category fit** — a weighted keyword lexicon ranks the five categories
   (`collection`, `numeric`, `text`, `temporal`, `mapping`) against the task's
   `task.toml` and `instruction.md`, so the injected sub-task feels native.
3. **Calibration confidence** — probes with measured discrimination below a
   threshold are demoted.
4. **Stable hash rotation** — deterministic per task, different across tasks.

Probe validity does not depend on getting the category right. Category fit is
cosmetic; the measurement is not.

---

## 7. Generated artefacts

Agent-visible, inside `environment/`:

```
<repo>/<lib>/__init__.py            synthetic library, honest docstrings
<repo>/docs/<lib>-CHANGELOG.md      authoritative behavioural changes
<repo>/docs/<lib>-api.md            current signatures
<repo>/data/probe_input.json        check inputs
<repo>/tests/test_probe_visible.py  shape-only smoke tests
instruction.md                      "Part 2" appended between markers
```

Verifier-only, inside `tests/` (never mounted into the agent session):

```
tests/_plx_lib/<lib>/__init__.py    pristine copy — this is what grades
tests/probe_grade.py                generated, self-contained grader
tests/probe_input.json              grader's own copy of the inputs
tests/_plx_reference/gold.py        doc-reading reference      -> 1.00
tests/_plx_reference/familiar.py    prior-locked reference     -> 0.40
tests/_plx_reference/stub.py        raises                     -> 0.00
tests/_plx_reference/bypass.py      hand-rolled, no import     -> 0.00
tests/task_verify.sh                the task's original verifier, preserved
tests/test.sh                       composite verifier
```

Task root:

```
priorlock.toml                      manifest: probes, weights, hashes
```

**Nothing generated imports PriorLock.** A wrapped task is a plain Harbor task
that anyone can run, inspect, or vendor without installing this package.

---

## 8. Gate suite

Runs offline: no Docker, no network, no API key. Every gate executes the
*generated* grader against *generated* reference solutions, so it validates the
artefact that will actually run in the container.

| Gate | Check | Requirement |
|------|-------|-------------|
| **G1** | gold score | exactly 1.0 |
| **G2** | familiar score | exactly 0.40 |
| **G3** | stub score | exactly 0.0 |
| **G4** | ladder | 0.0 < 0.40 < 1.0, strictly |
| **G5** | visible tests | pass for BOTH gold and familiar |
| **G6** | canary | no verifier asset reachable from `environment/` |
| **G7** | bypass | hand-rolling scores 0.0, not 0.40 |
| **G8** | tamper | editing the library is flagged and changes no score |
| **G9** | discrimination | every individual probe separates gold from familiar |
| **G10** | host preserved | the task's original verifier survived intact |
| **G11** | oracle | the shipped oracle scores 1.0 on the probes |

```bash
priorlock stage0 <task-dir>
priorlock stage0 tasks/ --json     # whole suite, machine-readable
```

---

## 9. Calibration

Calibration does **not** establish the 0.40 baseline. It measures how
*informative* each probe is against a given model.

| Metric | Definition | Use |
|--------|------------|-----|
| `discrimination` | fraction of runs with an unambiguous verdict | < 0.60 → probe confuses agents, demote it |
| `familiar_rate` | of those, the fraction that were `prior_locked` | **the headline prior-lock rate** |

```bash
priorlock calibrate ingest trials/ --model claude-opus-5
priorlock calibrate report --model claude-opus-5
priorlock calibrate recommend --model claude-opus-5
```

A probe with `familiar_rate` above 0.90 is a floor for that model and one below
0.10 is a ceiling; neither carries much information. `recommend` ranks probes by
`discrimination × (1 − 2·|rate − 0.5|)`, favouring probes that genuinely split
the model's behaviour.

Because the ladder is structural, a probe going stale degrades *resolution*, not
*validity*. That is the property the authored-deviation model could not offer.

---

## 10. Scope

**Works when** the function shape is familiar enough that a prior exists, the
deviation is silent (wrong values, never a crash), and the correct behaviour is
documented in-container.

**Does not work when** the API is genuinely novel (no prior to override), the
deviation would crash (the agent debugs and finds it), or the library is real and
published (training contamination makes "familiar" undefined).

Every probe in the catalog satisfies these conditions and is verified against all
eleven gates in CI on every commit.

---

## 11. Relationship to the authored-domain path

Both paths coexist and can run on the same task.

| | Wrapped task | Authored domain |
|---|---|---|
| Author effort | none | ~30 min per domain |
| 0.40 baseline | structural | hand-derived, gate-checked |
| Applies to | any Harbor task | one bespoke domain |
| Probe novelty | catalog only | anything |
| Anti-hack | 5 layers, generated | manual |

Use `priorlock wrap` by default. Use `priorlock new-domain` when you need a probe
the catalog does not cover — and consider contributing it back, since a new
archetype benefits every wrapped task at once.

`tablixdemo-0` is wrapped *and* authored: its `task_score` comes from the
hand-written tablix deviations and its `gap_score` from three injected probes.
The two measurements agree, which is the cheapest available evidence that the
generic path measures the same thing the bespoke path does.
