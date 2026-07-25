# Task Lifecycle — build once, convert once

## The rule

**You do not author a PriorLock task. You convert a Harbor task you already
trust.**

```
Harbor task  ──[ priorlock wrap ]──▶  Harbor task that also measures prior-override
```

`priorlock wrap` is a conversion step, not a build step and not an authoring
format. You build and validate an ordinary Harbor task first — with its own
oracle, its own verifier, its own difficulty calibration — and only convert it
once you already trust it.

This matters because it decides **what you debug**. If authoring and
prior-override measurement were fused, a bad number could mean either "my task is
broken" or "the probe is wrong", and you would have no way to tell them apart.
Keeping them sequential means the host task is already known-good before probes
ever enter the picture.

> **A note on an earlier version of this document.** It opened by claiming
> Harbor had shipped a `harbor migrate` command for Terminal-Bench 1.0 tasks and
> that PriorLock followed that precedent. That framing was invented and is
> removed. The argument above stands on its own without it: convert rather than
> re-author, because it is the only way to know which layer a bad number came
> from.

---

## The eight steps

```
  1  build          author an ordinary Harbor task
  2  validate       harbor run -p tasks/t -a oracle      → reward 1.0
  3  calibrate      run models, confirm the task discriminates
  ────────────────── the task is now known-good ──────────────────
  4  preflight      priorlock preflight tasks/t                  is it wrap-ready?
  5  convert        priorlock wrap tasks/t --baseline-from jobs/
  6  gate           priorlock stage0 tasks/t                     11 offline gates
  6b soundness      priorlock cheats tasks/t --suite             FAR receipt
  7  re-run         harbor run -p tasks/t -a oracle
  8  doctor         priorlock doctor tasks/t                     did wrapping break it?
```

Steps 1–3 are pure Harbor. Nothing about PriorLock is involved and nothing about
your task changes. Steps 4–8 are the conversion and its two bookend checks.

Steps 4, 5 and 6 need **no Docker, no network and no API key** — together they
take about five seconds.

---

## Step 4 — preflight

Runs before wrapping. Offline, no Docker. Answers *"is this host task actually
healthy and safe to convert?"*

```bash
priorlock preflight tasks/my-task
```

```
P1   task.toml present                PASS  task.toml
P2   task format version declared     PASS  version = 1.0
P3   instruction file present         PASS  instruction.md (1517 chars)
P4   environment/ with Dockerfile     PASS  environment/Dockerfile
P5   agent workdir resolves           PASS  /app/repo → environment/repo
P6   verifier entrypoint present      PASS  tests/test.sh
P7   verifier emits a reward          PASS  writes reward.txt
P8   oracle solution present          PASS  solve.sh
P9   not already wrapped              PASS  clean
P10  no reserved-path collisions      PASS  clean
P11  network disabled                 PASS  allow_internet = false
P12  python present in image          PASS  python referenced in Dockerfile

READY TO WRAP
```

| Check | Level | Why it matters |
|---|---|---|
| P1, P3, P4, P5, P6 | error | wrap needs these to place files correctly |
| P7 | error | the composite reads whichever reward file the verifier writes |
| P9, P10 | error | wrapping would clobber content the task already owns |
| P2, P8, P11, P12 | warn | advisable, not fatal |

`wrap` runs preflight automatically and refuses on a blocking failure. Override
with `--skip-preflight` if you know what you are doing.

**P10 is the one that saves you.** If your task already has a `data/` file called
`probe_input.json`, or its own `tests/task_verify.sh`, wrapping would overwrite
real content. Preflight catches that before anything is written.

---

## Step 5 — migrate, and pin the baseline

```bash
priorlock wrap tasks/my-task --baseline-from jobs/
```

```
✓ tablixdemo-0 wrapped
  library  datawright
  probes   tie_inclusive_topk (result_shape), null_key_policy (default_flip),
           merge_precedence_remap (value_remap)
  weights  task=0.5 gap=0.5
  baseline 1.0  (oracle · tablixdemo-0__fupYgQQ)
  14 files created, 2 modified
```

`--baseline-from` reads your Harbor output directory (./jobs on 0.1.x), finds the most recent
**oracle** run, and pins its reward into `priorlock.toml`:

```toml
[baseline]
# Oracle reward recorded BEFORE wrapping. `priorlock doctor` compares
# the post-wrap task_score against this to prove wrapping did no harm.
reward = 1.0
agent = "oracle"
trial = "tablixdemo-0__fupYgQQ"
task_checksum = "706db01c3396978d487ed366c1076585772c617cda47ba3c19baa6e1d35e9507"
captured_at = "2026-07-25T00:00:30.554570Z"
```

This is the single most important artefact of the migration. Without it, a wrap
that quietly broke your original verifier would show up later as a *model
regression* rather than a *harness bug* — and you would go looking in entirely
the wrong place.

Use `--baseline-agent` to pin against something other than the oracle.

---

## Step 6 — gate

```bash
priorlock stage0 tasks/my-task
```

Eleven offline gates. G1–G9 validate the probe measurement; **G10 and G11
validate the conversion itself.**

| Gate | Check |
|---|---|
| G1–G4 | the {0.0, 0.40, 1.0} ladder holds exactly |
| G5 | visible tests don't discriminate |
| G6 | no verifier asset reachable from `environment/` |
| G7 | bypassing scores 0.0, not 0.40 |
| G8 | tampering is flagged and changes no score |
| G9 | every probe separates gold from familiar |
| **G10** | **the host task's original verifier survived intact** |
| **G11** | **the shipped oracle scores 1.0 on the probes** |

G10 asserts three things about the migration:

1. the original verifier was copied aside **byte-identically** (sha256 recorded
   at wrap time),
2. the composite entrypoint **actually invokes it**, and
3. it runs **before** the probe grader — otherwise its `reward.json` would be
   overwritten before `task_score` could be read.

All three failure modes are verified to fail:

```
G10 passed=False  detail=task_verify.sh missing — original verifier was lost
G10 passed=False  detail=task_verify.sh was modified after wrapping
G10 passed=False  detail=probe grader runs before the host verifier
```

---

## Step 8 — doctor

Runs after the post-wrap re-run. Answers *"did wrapping damage the host task?"*

```bash
priorlock doctor tasks/my-task -t jobs/
```

```
=== Doctor · tablixdemo-0 ===

  baseline task_score  1.0000   (oracle, before wrapping)
  observed task_score  1.0000   (oracle, after wrapping)
  drift                0.0000
  gap_score            1.0000   (prior-override, new signal)

    tie_inclusive_topk           override         1.00
    null_key_policy              override         1.00
    merge_precedence_remap       override         1.00

HEALTHY
  task_score is unchanged — wrapping did not perturb the host task
```

Four verdicts:

| Verdict | Meaning | What to do |
|---|---|---|
| `healthy` | `task_score` unchanged | ship it |
| `regressed` | `task_score` dropped | check the composite's workdir and that `task_verify.sh` still resolves its paths |
| `inflated` | `task_score` rose — impossible for an oracle | the original verifier probably is not executing at all |
| `no-baseline` / `no-data` | nothing to compare | re-wrap with `--baseline-from`, or re-run the oracle |

**A healthy migration leaves `task_score` at exactly the value it had before.**
Any drift is a harness bug, not a model result. That is the whole point of
pinning the baseline.

---

## What each layer owns

```
task_score   ←  your original verifier, byte-identical, running first
                 "can the agent do the job?"
                 guaranteed unchanged by G10 + doctor

gap_score    ←  the injected probes
                 "does the agent verify its assumptions?"
                 guaranteed to sit on {0.0, 0.40, 1.0} by G1–G4

reward       =  (task_score × w_task + gap_score × w_gap) / (w_task + w_gap)
```

Harbor reads `reward.txt` (the `harbor tasks init` default) or `reward.json`.
The composite reads whichever the original verifier wrote and re-emits both, so
the whole arrangement is invisible to the runner. Set `w_gap = 0.0` and a wrapped task behaves exactly like the
original while still recording probe verdicts for calibration.

---

## Reversibility

```bash
priorlock unwrap tasks/my-task
```

Removes every file `wrap` wrote, strips the instruction addendum between its
markers, and restores `tests/task_verify.sh` back to `tests/test.sh`. The task
returns to being an ordinary Harbor task.

Because migration is reversible and gated on both ends, it is safe to run across
a whole suite and roll back:

```bash
priorlock preflight tasks/ --recursive
priorlock wrap tasks/ --recursive --baseline-from jobs/
priorlock stage0 tasks/
```

---

## Why not fuse authoring and probes?

It was the obvious alternative, and it is worse for three reasons.

1. **Debuggability.** A fused format means a bad number has two possible causes.
   Sequential means the host task is already known-good.
2. **Adoption.** Nobody re-authors a working benchmark suite. Harbor learned this
   with TB 1.0. A migration path costs an existing suite one command.
3. **Independence.** `task_score` comes from a verifier PriorLock never wrote and
   cannot influence. That separation is what makes the two numbers comparable —
   and it is exactly what G10 exists to protect.
