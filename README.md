# PriorLock

> **An open building block for measuring, and rewarding, whether coding agents read the docs or code from memory.** When an installed library's behaviour has changed, code written from memory runs, passes every visible test, and is wrong. PriorLock turns that failure into tasks, a hardened verifier and a reward you can benchmark with, wrap into existing benchmarks, or train on, and it is built to be extended.

[![tests](https://github.com/phoenixlibbi/PriorLock-RL-env/actions/workflows/test.yml/badge.svg)](https://github.com/phoenixlibbi/PriorLock-RL-env/actions/workflows/test.yml)
[![Stage-0 gates](https://github.com/phoenixlibbi/PriorLock-RL-env/actions/workflows/stage0.yml/badge.svg)](https://github.com/phoenixlibbi/PriorLock-RL-env/actions/workflows/stage0.yml)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

**Where it stands**

| | |
|---|---|
| **Solid** (tested, in CI) | An isolated grader that scores the library calls the code actually made · 12 offline integrity gates · a 12-class cheat battery built from an outside red-team (0 of 156 cheat runs beat the do-nothing baseline) · per-seed tasks whose answers cannot be reused · non-destructive wrapping of Harbor / Terminal-Bench tasks · a four-condition model benchmark |
| **Preliminary** | Bench v2 in realistic repositories is running on the free models (results below, updated as each finishes). A pilot on four free models from three vendors: Every model applies the change when the docs are in the prompt (96–100%, except a 7B model at 62%), but when it has to find them, right calls fall to 12–27%: some models read only the code, one never looks (see Results) |
| **Open, for you to build** | A multi-turn tool environment · a trained policy · tasks on real libraries · other languages. See [Build on it](#build-on-it) and [Open questions](#open-questions) |

**Start here:** [Quickstart](#quickstart-no-model-one-minute) (one minute, no model) · [Starter recipes](#starter-recipes) (your own behaviour change, your own agent, your own RL loop) · [Open questions](#open-questions)

Models learn libraries from a frozen snapshot of the internet. When a project pins a version whose behaviour changed, a model that codes from memory writes code that **runs, passes every visible test, and is wrong**. Nothing crashes, so nothing tells the agent to look. The documentation that would have saved it is sitting in the repository.

Prior work measured the knowledge side of this. [LibEvoBench](https://arxiv.org/abs/2606.25402) finds that telling a model the target version gives no benefit, while handing it the relevant documentation significantly boosts accuracy; [GitChameleon 2.0](https://arxiv.org/abs/2507.12367) finds enterprise models solve 48–51% of version-conditioned problems even with the version stated; [CodeUpdateArena](https://arxiv.org/abs/2407.06249) tests whether a model can use a synthetic API update it was given. PriorLock asks the agentic question: **does the agent go and read the docs when nobody hands them over**, and can that behaviour be rewarded.

```
                 the installed library changed a default; the CHANGELOG says so
                                              │
          ┌───────────────────────────────────┼───────────────────────────────────┐
          ▼                                   ▼                                   ▼
   never calls the library          calls it the memorized way          reads the docs, calls it
   (hand-rolls the logic)           (runs clean, tests pass)            the way THIS version needs
        0.00  bypassed                   0.40  prior-locked                  1.00  override
```

| Command | What it does | Docker / model needed |
|---|---|---|
| `priorlock bench` | Benchmark a model on all 13 probe archetypes under four conditions: closed-book, open-book, agentic, agentic with the hints removed | optional (grading sandbox) / any OpenAI-compatible endpoint, including local Ollama |
| `priorlock run` | Generate a self-contained task (synthetic library, docs, data, smoke test) and grade a solution | no / no |
| `priorlock wrap` | Inject prior-override probes into an existing Harbor / Terminal-Bench task; its original verifier is kept byte-identical | no / no |
| `priorlock stage0` | 12 offline gates on a wrapped task: the reference ladder, non-discriminating visible tests, canaries, bypass, tamper | no / no |
| `priorlock cheats` | 12-class cheat battery with a soundness receipt | no / no |
| `priorlock leakprobe` | Runtime isolation proof: an adversarial task that tries 12 leak vectors inside the real container | yes (Harbor) / no |
| `vf.load_environment("priorlock")` | The probes as a `verifiers` RL environment (single-turn, see below) | no / your trainer |

---

## Results

### Bench v2: realistic repositories (running now, updated as each model finishes)

The pilot below uses small task folders with the change written in a CHANGELOG. Bench v2 asks the same question in a setting a skeptic would accept:

- **36 behaviour changes** (the original 13 plus 23 new everyday ones: time units, percentiles, page numbering, CSV headers, slugs, week starts, log levels, version ordering, config parsing, …) in **24 tasks**, two task sets that each cover all 36.
- **Each task is a small, realistic project**: application code, tests, CI, a runbook, ADRs and a vendored library with its own docs, so finding the right note takes real searching.
- **The change is written in exactly one place**, the task's *channel*: the library's CHANGELOG, a migration guide, API reference pages, the type stub (`.pyi`) or an "Upgrading" section of its README. A check (`check_channel_isolation`) proves it appears nowhere else.
- **Conditions**: docs pasted in the prompt (ceiling) · library source readable · library compiled with no hint · three hints ("upgraded to 2.0" / "check the documentation" / "defaults changed, the docs describe it") · compiled plus a **RUN** tool that executes Python in a sandbox. The agent also has **GREP**.
- **Verified before any model ran**: on all 24 tasks the Docker grader gives the reference solutions exactly 1.0 / 0.40 / 0 / 0 (gold, memorized, bypass, empty); 53 tests pass; every model reply is kept in the results.

Run it yourself: `priorlock bench --suite v2 --model <model> …`, report with `priorlock bench --report results/bench_v2/*.jsonl`. Full tables: [results/bench_v2/REPORT.md](results/bench_v2/REPORT.md); logs: [results/bench_v2/logs](results/bench_v2/logs).

<!-- V2_FINDINGS_START -->
**What it shows so far** (Gemini 3.5 Flash-Lite on the first task set; other free models are queued; each cell is about six tasks, so treat these as directions, not estimates):

1. **The v1 result holds in realistic repos.** Docs in the prompt: 100% right calls. Library compiled, no hint: 29%.
2. **The failure is not looking, not misunderstanding.** When the model found the note describing the change it made the right call 87% of the time; when it did not, 26%.
3. **Saying the version changed does not help; saying what to do does.** "Upgraded to 2.0" left it at 28%, in line with [LibEvoBench](https://arxiv.org/abs/2606.25402)'s finding that stating the target version gives no benefit. Pointing at the documentation, and saying defaults changed, raised it to 38% and 61%. A behaviour a sentence can shift is a behaviour a reward can shift.
4. **Running the code beats reading it.** With the RUN tool and no hint, it tested the library's behaviour directly and reached 72%.
5. **Agents look next to the code, not in the docs folder.** A change written in the type stub inside the library was found in every task; one written in the CHANGELOG or migration guide was not found in any.
<!-- V2_FINDINGS_END -->

<!-- V2_TABLES_START -->
_Last updated 2026-10-29 04:01 · 76 runs · gemini-3.5-flash-lite (45 runs), openai/gpt-oss-120b (31 runs)._

### Right calls by condition (the hint ladder)

| Model | repo_open | repo_source | repo_docs | repo_docs_h1 | repo_docs_h2 | repo_docs_h3 | repo_run |
|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | 100% | 78% | 29% | 28% | 38% | 61% | 72% |
| openai/gpt-oss-120b | 100% | – | 8% | – | 10% | – | 5% |

### Where the change was written (all models pooled)

| Channel | Open book: right call | Compiled, no hint: right call | Compiled, no hint: found the change |
|---|---|---|---|
| changelog | 100% (12/12) | 17% (2/12) | 0% (0/4) |
| migration | 100% (12/12) | 0% (0/12) | 0% (0/4) |
| api_reference | 100% (9/9) | 11% (1/9) | 33% (1/3) |
| stub | 100% (9/9) | 50% (3/6) | 50% (1/2) |
| readme | 100% (6/6) | 33% (2/6) | 0% (0/2) |

### By probe family (compiled library, all hints and RUN pooled)

| Family | Right call | Prior-locked |
|---|---|---|
| default_flip | 24% (22/90) | 51% (46/90) |
| value_remap | 17% (8/48) | 42% (20/48) |
| result_shape | 75% (18/24) | 0% (0/24) |

### Did finding the change help? (compiled library, all hints and RUN pooled)

| Model | Right call when it found the change | Right call when it did not |
|---|---|---|
| gemini-3.5-flash-lite | 87% (26/30) | 26% (17/66) |
| openai/gpt-oss-120b | 0% (0/3) | 8% (5/63) |

<details><summary>Every model and condition (found / looked / GREP / RUN / turns)</summary>

### Every model and condition

| Model | Condition | Tasks | Right call [95% CI] | Prior-locked | Found the change | Looked at the library | Used GREP | Used RUN | Mean turns |
|---|---|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | repo_open | 7 | **100%** [100%, 100%] | 0% (0/21) | 100% (7/7) | 0% (0/7) | 0% (0/7) | 0% (0/7) | 1.0 |
| gemini-3.5-flash-lite | repo_source | 6 | **78%** [56%, 94%] | 6% (1/18) | 0% (0/6) | 100% (6/6) | 0% (0/6) | 0% (0/6) | 4.3 |
| gemini-3.5-flash-lite | repo_docs | 7 | **29%** [10%, 48%] | 48% (10/21) | 29% (2/7) | 86% (6/7) | 14% (1/7) | 0% (0/7) | 5.1 |
| gemini-3.5-flash-lite | repo_docs_h1 | 6 | **28%** [11%, 50%] | 44% (8/18) | 17% (1/6) | 100% (6/6) | 17% (1/6) | 0% (0/6) | 5.0 |
| gemini-3.5-flash-lite | repo_docs_h2 | 7 | **38%** [19%, 62%] | 52% (11/21) | 43% (3/7) | 100% (7/7) | 43% (3/7) | 0% (0/7) | 9.3 |
| gemini-3.5-flash-lite | repo_docs_h3 | 6 | **61%** [39%, 83%] | 17% (3/18) | 50% (3/6) | 100% (6/6) | 50% (3/6) | 0% (0/6) | 9.3 |
| gemini-3.5-flash-lite | repo_run | 6 | **72%** [50%, 89%] | 28% (5/18) | 17% (1/6) | 83% (5/6) | 0% (0/6) | 100% (6/6) | 8.7 |
| openai/gpt-oss-120b | repo_open | 9 | **100%** [100%, 100%] | 0% (0/27) | 100% (9/9) | 0% (0/9) | 0% (0/9) | 0% (0/9) | 1.0 |
| openai/gpt-oss-120b | repo_docs | 8 | **8%** [0%, 21%] | 58% (14/24) | 0% (0/8) | 0% (0/8) | 0% (0/8) | 0% (0/8) | 1.0 |
| openai/gpt-oss-120b | repo_docs_h2 | 7 | **10%** [0%, 24%] | 48% (10/21) | 0% (0/7) | 0% (0/7) | 0% (0/7) | 0% (0/7) | 2.0 |
| openai/gpt-oss-120b | repo_run | 7 | **5%** [0%, 14%] | 24% (5/21) | 14% (1/7) | 14% (1/7) | 14% (1/7) | 0% (0/7) | 12.4 |

</details>
<!-- V2_TABLES_END -->

### 1. The instrument, before any model runs

Every number below regenerates offline from this repository.

| Check | Result | Command |
|---|---|---|
| Reference ladder on a freshly wrapped task | stub 0.0 · bypass 0.0 · familiar 0.40 · gold 1.00, **12/12 gates pass** | `priorlock wrap <task> && priorlock stage0 <task>` |
| Cheat battery: 12 attack classes, each run against all 13 archetypes | **every class caught on every archetype**; best cheat score 0.40, never above the do-nothing baseline | `priorlock cheats <task> --suite` · [receipt](results/receipts/soundness-receipt.json) |
| Runtime isolation (Harbor, 49 attempts) | 0 oracle assets reachable from the agent; canary only verifier-side | `priorlock leakprobe <task>` · [trace](results/receipts/leakprobe-trace.json) |
| Sandboxed bench grader | gold 1.00, familiar 0.40, stub 0.00 inside `docker run --network none` | `pytest tests/test_bench.py` (runs when Docker is available) |

The receipt pools 156 runs (12 classes × 13 archetypes) for a Wilson upper bound of 2.4% on false accepts. Runs of the same class are correlated, so read that number as "no class got through anywhere", not as 156 independent trials.

### 2. Headline: agents that seem to read the docs are reading the code

Same models, same tasks, no hints in the instruction. The only change: in the second column the library ships compiled, so its source cannot be read, and the change is written only in the CHANGELOG and API reference, as for many real packages (`priorlock bench --condition agentic_docs_only`).

| Model | Library code readable | Library compiled, docs readable | Opened the docs |
|---|---|---|---|
| Gemini 3.5 Flash-Lite | **100%** right call | **23%** [0%, 46%], 58% coded from memory | 0 of 8 tasks |
| Gemini 3.1 Flash-Lite | **100%** | **27%** [8%, 50%], 50% coded from memory | 1 of 8 tasks |
| gpt-oss-120b (Groq) | **12%** [3%, 24%], never opened a file | **25%** [6%, 47%], never opened a file | 0 of 10 tasks |
| Qwen2.5-Coder 7B (local) | 15% [0%, 38%] | 15% [0%, 38%] | 0 of 4 tasks |

Handed the docs in the prompt, gpt-oss-120b scores **100%** (32 of 32 calls), so the tasks are solvable; in the agentic conditions it wrote its answer on the first turn without looking at anything. That is a second way to fail: the Gemini models look, but only at the code; gpt-oss does not look at all. Its two agentic rows are effectively the same condition for a model that never opens a file, so the 12-point gap between them is run-to-run noise, a useful reminder of how wide these intervals are.

On the two probe families that genuinely require the docs (`default_flip`, `value_remap`), the Gemini models made **1 right call out of 40**; their remaining right calls came from `result_shape` probes, which the instruction gives away. Handed the same docs in the prompt, the same models score 96–100%. So the skill was never "reads the documentation": with readable code they read the code, and without it they looked at the library, found nothing, and fell back on memory instead of opening the CHANGELOG.

### 3. Pilot: what models do with the docs

Three free models: two Gemini Flash-Lite versions through the free API tier (2 task sets each) and Qwen2.5-Coder 7B run locally with Ollama (1 task set). Every task set covers all 13 behaviour changes.

| Model | Docs handed over (open-book) | Must look for itself (agentic, no hints) | What it opened when it looked |
|---|---|---|---|
| Gemini 3.5 Flash-Lite | 100% right call | **100%** right call | the library source, 8 of 8 tasks; the docs, 0 |
| Gemini 3.1 Flash-Lite | 96% | **100%** | the library source, 8 of 8; the docs, 0 |
| Qwen2.5-Coder 7B | 62% | **15%** (38% coded from memory) | the library source, 1 of 4; the docs, 0 |

**What it shows so far.**
1. **The prior is real.** With no docs and no source (closed-book), Gemini 3.5 Flash-Lite used the memorized behaviour 46% of the time [23%, 73%], and on every one of the 8 `value_remap` probes, the family only reading can solve.
2. **Models differ in whether they look.** Both Gemini models looked on every task and got everything right. Qwen could use the docs when handed them (62%) but rarely went to look, and fell to 15%. The 47-point drop is the cost of not looking, which is what PriorLock is built to isolate.
3. **Nobody read the CHANGELOG.** Every look was at the library's own source, whose docstrings also describe the new behaviour. Section 2 tests what happens when that source is not readable.

Qwen in closed-book mostly reimplemented the logic instead of calling the library (scored `bypassed`), so that condition says little about it. Gemini 3.5 Flash and 2.5 Flash could not be run on the free tier (daily quota, model retired) and are not reported.

<details>
<summary>Full table: every condition, verdict mix and per-family breakdown</summary>

| Model | Condition | Probes | Opened docs / source | Prior-locked (memorized behaviour) | Right call (installed behaviour) | Fully correct | Other |
|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | open | 26 | — | 4% [0%, 12%] | 96% [88%, 100%] | 96% [88%, 100%] | 0 |
| gemini-3.1-flash-lite | agentic_uncued | 26 | 0 / 8 of 8 tasks | 0% [0%, 0%] | 100% [100%, 100%] | 100% [100%, 100%] | 0 |
| gemini-3.5-flash-lite | closed | 26 | — | 46% [23%, 73%] | 50% [27%, 73%] | 50% [27%, 73%] | 1 |
| gemini-3.5-flash-lite | open | 26 | — | 0% [0%, 0%] | 100% [100%, 100%] | 96% [88%, 100%] | 0 |
| gemini-3.5-flash-lite | agentic | 26 | 0 / 8 of 8 tasks | 0% [0%, 0%] | 100% [100%, 100%] | 100% [100%, 100%] | 0 |
| gemini-3.5-flash-lite | agentic_uncued | 26 | 0 / 8 of 8 tasks | 0% [0%, 0%] | 100% [100%, 100%] | 100% [100%, 100%] | 0 |
| qwen2.5-coder:7b | closed | 13 | — | 0% [0%, 0%] | 0% [0%, 0%] | 0% [0%, 0%] | 13 |
| qwen2.5-coder:7b | open | 13 | — | 8% [0%, 23%] | 62% [38%, 85%] | 54% [31%, 77%] | 4 |
| qwen2.5-coder:7b | agentic_uncued | 13 | 0 / 1 of 4 tasks | 38% [15%, 69%] | 15% [0%, 38%] | 15% [0%, 38%] | 6 |

Right call by probe family (prior-locked in brackets):

| Model | Condition | default_flip | value_remap | result_shape |
|---|---|---|---|---|
| gemini-3.1-flash-lite | open | 12/12 (0) | 8/8 (0) | 5/6 (1) |
| gemini-3.1-flash-lite | agentic_uncued | 12/12 (0) | 8/8 (0) | 6/6 (0) |
| gemini-3.5-flash-lite | closed | 7/12 (4) | 0/8 (8) | 6/6 (0) |
| gemini-3.5-flash-lite | open | 12/12 (0) | 8/8 (0) | 6/6 (0) |
| gemini-3.5-flash-lite | agentic | 12/12 (0) | 8/8 (0) | 6/6 (0) |
| gemini-3.5-flash-lite | agentic_uncued | 12/12 (0) | 8/8 (0) | 6/6 (0) |
| qwen2.5-coder:7b | closed | 0/6 (0) | 0/4 (0) | 0/3 (0) |
| qwen2.5-coder:7b | open | 6/6 (0) | 2/4 (1) | 0/3 (0) |
| qwen2.5-coder:7b | agentic_uncued | 0/6 (5) | 0/4 (0) | 2/3 (0) |

</details>

**How to read it.**
- **Closed-book** shows the prior: the model sees the instruction, the input file and the function signatures with defaults hidden, but no docs or source. A high prior-locked rate here is what makes a probe meaningful.
- **Open-book** is the ceiling: the docs pasted into the prompt.
- **Agentic** gives `LIST` and `READ` over the repository; the model has to decide to look. **Agentic, uncued** removes the instruction's hints (the version tag, the pointer to `docs/`, the bold on the required behaviour), which is closer to how real tasks read. **Agentic, docs-only** is uncued with the library shipped compiled: reading it shows a one-line `__init__.py` and a native binary, so the docs are the only source.
- Every condition gets the task's input file, so differences between conditions are not about guessing the input layout.
- **Right call** means every call to the probed function used the installed version's behaviour; **fully correct** additionally means the output was right. **Opened docs / source** counts agentic tasks where the model read a `docs/` file or the library's own source.

Intervals resample whole archetypes (the 13 behaviour changes), not individual probes, because repeats of one archetype are correlated. This is a pilot, not a leaderboard: three free models, temperature 0, 13 behaviour changes per task set. Every answer, every file the agent read and every per-probe verdict is in [`results/bench/`](results/bench/).

---

## The failure mode

Every probe is a library function whose behaviour changed in the installed major version **without changing its signature**:

| Family | Example (names and data vary per task) |
|---|---|
| `default_flip` | `bucket()` now collects null keys under `"__unset__"` instead of dropping them |
| `value_remap` | `merge(on_conflict="keep")` now means keep the *newer* value |
| `result_shape` | `top_k()` returns every record tied at the cut-off, so `len(result)` may exceed `k` |

The library's `CHANGELOG.md`, its API reference and its own source all say so. Code written against the old behaviour still runs, still returns the right types, and still passes the visible smoke tests, which deliberately cannot tell the two apart (gate G5). Only the hidden grader can.

Each task seed gets its own library name and its own data: ids, quantities and sequence values are shifted, category labels are relabelled, amounts are rescaled, and the expected answers are recomputed by running the reference solutions against the library. A solution copied from one task does not carry its answers to another (`tests/test_grader_isolation.py`).

## How the score is earned

The grader never runs the solution in its own process. A child process (`python -I`, empty environment) imports a **pristine copy of the library**, wraps each probed function, and records the arguments the solution *explicitly supplied* (`inspect.Signature.bind`, defaults excluded). While it runs, every answer-bearing file is removed from disk; when grading runs as root (Harbor, the Docker sandbox), the child also drops to `nobody` and the tests directory is made private. The grader ignores everything the child prints. Then, per probe:

| Score | Verdict | Requires |
|---|---|---|
| **1.00** | `override` | every call uses the documented behaviour **and** the output is right |
| **0.40** | `prior_locked` | the memorized call, producing the memorized output |
| **0.40** | `correct_output_other_call` | the right output reached some other way (for example post-processing the new default by hand) |
| **0.00** | `inconsistent_calls` | the probed argument took different values across calls (trying options and keeping what works) |
| **0.00** | `bypassed` | the function was never called |
| 0.00 | `incorrect`, `correct_call_bad_output` | anything else |

The 0.40 rung is a fixed design constant: it is what the memorized solution earns, gate G2 checks it on every wrapped task, and no other route earns more without the documented call. Wrapped tasks emit two scores and a composite:

`reward = (task_score × w_task + gap_score × w_gap) / (w_task + w_gap)`

where `task_score` is the host task's original verifier, untouched, and `gap_score` is the probes. The composite replaces the host task's `reward.txt`; pass `--weight-gap 0` to keep a leaderboard's own semantics and read `gap_score` as a side metric.

## Why it is hard to farm

| Attack (cheat class) | What stops it |
|---|---|
| Overfit the visible tests (`overfit_public`) | visible tests pass for gold *and* familiar (G5) |
| Read the grader or reference on disk (`oracle_steal`, `reference_exec`) | answer files are removed while the solution runs; root grading also drops privileges |
| Reach into the grading process (`grader_introspect`) | the solution runs in a separate process with no answer key |
| Print a fake report (`stdout_forgery`, `self_report`) | the grader ignores the child's output and writes its own report |
| Spray every argument value (`spray_known_output`, white-box: knows the right outputs) | all calls must agree on the probed argument |
| Edit the library or the tests (`edit_grader`, `tamper_input`, `read_internals`) | the verifier owns a pristine copy; tampering is flagged and changes no score (G8) |
| Constant outputs, timeouts (`shape_forgery`, `timeout_abuse`) | wrong values score 0; the child is killed |

Two rules keep the receipt honest: **a cheat that never ran is not a caught cheat** (each writes an execution marker first; markerless zeros are excluded from the denominator), and **a false accept means scoring above the 0.40 baseline**, not above zero.

**Residual risk, stated plainly.** The solution and the call recorder share the child process, so a solution can forge its own call record. That only helps if it already knows the documented argument, which is the knowledge the probe measures. When grading runs unprivileged (`priorlock run --grade` or `verify` on a laptop), answer files are hidden by removal rather than by permissions; the report notes this as `unprivileged_grading`.

---

## Install

```bash
pip install "git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"
# or as a tool:  uv tool install "priorlock @ git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"
priorlock info
```

Python 3.10–3.13, standard library only. Docker is optional (it sandboxes model-written code in `bench`). Harbor is only needed for `wrap` → `harbor run` and `leakprobe`.

## Quickstart (no model, one minute)

```bash
priorlock run -o my-task --seed demo                # synthetic library + docs + data + smoke test
priorlock run --grade my-task --reference gold      # 1.0
priorlock run --grade my-task --reference familiar  # 0.40  (the memorized answer)
priorlock run --grade my-task --reference stub      # 0.0
```

Hand `my-task/instruction.md` to any model or agent, let it write `probe_solution.py`, then `priorlock run --grade my-task`.

## Starter recipes

Three runnable scripts in [`examples/`](examples/), each under 80 lines and checked in CI:

| Recipe | What it shows |
|---|---|
| [`01_your_own_behaviour_change.py`](examples/01_your_own_behaviour_change.py) | Define one `Probe` (a function whose behaviour changed silently, the documented call and the memorized call) and get a complete gated task. Prints gold 1.00 · familiar 0.40 · stub 0.00. |
| [`02_plug_in_your_agent.py`](examples/02_plug_in_your_agent.py) | Measure any agent or code-writing function across all 13 archetypes with the hidden grader. |
| [`03_reward_for_your_rl_loop.py`](examples/03_reward_for_your_rl_loop.py) | Use the grader as the reward in your own RL loop, one fresh task per seed. |

## Benchmark a model

```bash
# local, free: any Ollama model
ollama pull qwen2.5-coder:7b
priorlock bench --provider ollama --model qwen2.5-coder:7b

# any OpenAI-compatible endpoint (Gemini, OpenAI, vLLM, LM Studio, …)
export GEMINI_API_KEY=…
priorlock bench --provider gemini --model gemini-3.5-flash-lite --rpm 15
priorlock bench --base-url http://localhost:8000/v1 --model my-model

# tables for finished runs
priorlock bench --report results/bench/*.jsonl
```

- `--repeats N` generates N task sets; each covers all 13 archetypes once (4 tasks per set) with its own seed, data and answers. Tasks regenerate byte-identically from their seeds.
- `--condition closed|open|agentic|agentic_uncued` (repeatable) picks conditions; the default is all four.
- Runs are resumable: one JSON line per (task, condition) with the code, the files read, the turns and the per-probe verdicts.
- Model-written code is graded in `docker run --network none --memory 512m` by default; `--sandbox none` grades in-process (with a warning).

## Use it as an RL environment

**Training (`verifiers`).** `load_environment()` returns a single-turn environment: the prompt contains the library's API reference, CHANGELOG and the input, and the reward is the ladder above. Each instance draws its own mix of archetypes and its own data, and **evaluation holds out whole archetypes** (one per family) that training never sees, so eval measures transfer. The system prompt is neutral: it does not say that anything changed.

```python
import verifiers as vf
env = vf.load_environment("priorlock")      # pip install "priorlock[rl]"
```

Be clear about what this trains: the docs are in the prompt, so it rewards *acting on* documentation that contradicts the prior, not *deciding to look*. The looking condition exists today as `bench`'s agentic loop; a multi-turn tool environment is on the roadmap. No policy was trained in this repository.

**Evaluation (Harbor).** Wrap any Terminal-Bench / Harbor task; the probes ride along and the original verifier is preserved byte-for-byte (G10):

```bash
harbor run -p tasks/my-task -a oracle       # 1) prove the host task is sound
priorlock preflight tasks/my-task
priorlock wrap tasks/my-task                # 2) inject probes (authors write nothing)
priorlock stage0 tasks/my-task              # 3) 12 offline gates
priorlock leakprobe tasks/my-task           # 4) runtime isolation proof
harbor run -p tasks/my-task__leakprobe -a oracle
priorlock doctor tasks/my-task              # 5) wrapping did not damage the host task
priorlock unwrap tasks/my-task              # removes exactly what wrap added
```

`--domain sql --domain linux` and `--preset diverse` draw probes from 11 domain cartridges (76 probes: backend, cloud, coding, config, devtools, finance, frontend, fundamentals, linux, math, sql). `priorlock wrap <dir> -r` wraps a whole suite. Wrapping adds a clearly separated section to the instruction and, for some domains, 1.x-style usage examples under `utils/` (skipped if the host already has a `utils/`).

## Reviewed before release

Before publishing, the project was put in front of ten independent AI reviewers, each given the code and none given my conclusions. Five played roles: a frontier-lab eval researcher, an RL post-training engineer, an adversarial red-teamer, a Harbor benchmark maintainer and a coding-agent product engineer. Five more each read one lab's public 2025–26 research (xAI, Meta, Google DeepMind, Microsoft, Alibaba Qwen) and judged PriorLock against it.

They found real problems, and this version fixes them:

| Found in review | Fix |
|---|---|
| The solution ran inside the grader: it could read the answer key, patch the scorer or print a fake report (each scored 1.0) | out-of-process child, answers hidden during the run, report never read from the solution; four new cheat classes |
| Calling a function with every value and hand-writing the output scored 1.0 | all calls must agree; correct output by another route is capped at 0.40 |
| A correct solution that post-processed the new default scored below the memorized one | it now earns the 0.40 baseline, never less |
| Seeds changed names but not data, so a leaked answer key worked everywhere | per-seed data with recomputed answers |
| The agentic pilot gap was mostly the agent not seeing the input file | every condition gets the input file |
| Instructions hinted at the trap | an uncued agentic condition, reported separately |
| Closed-book could only guess argument names | closed-book sees signatures with defaults hidden |
| Intervals treated renamed repeats as independent | archetype-clustered bootstrap intervals |
| The RL environment was one task repeated, train equalled eval, and its prompt said "read the CHANGELOG" | archetype rotation, per-instance data, held-out eval archetypes, neutral prompt |
| `unwrap` could delete a host task's own `utils/` | the manifest records what wrap wrote; unwrap removes only that |
| Missing closest prior work | CodeUpdateArena and knowledge-conflict studies are cited |

## Build on it

PriorLock is meant as a foundation more than a finished leaderboard. Its parts are separable, and each is useful on its own:

| Piece | Reuse it for | Where |
|---|---|---|
| **Call-observing grader** | Any RL environment where *how* the agent used an API matters, not only the final output. Records the arguments actually passed, against a library copy the agent cannot touch, in an isolated process. | `templates.py` (`GRADER`, `CHILD_SOURCE`) |
| **Structural reward ladder** | A dense reward with a meaningful middle rung: the "plausible but wrong" answer earns a fixed partial score, cheating can never beat it. | `probes/base.py` |
| **Probe injection (`wrap`)** | Adding a second, orthogonal measurement to an existing benchmark without re-authoring its tasks or touching its verifier. | `inject.py`, `gates.py` |
| **Cheat battery** | Red-teaming any verifier: execution markers, "false accept = above baseline", white-box attackers, pooled receipts. | `cheats.py` |
| **Condition harness** | Separating *not knowing* from *not looking* for any grounding skill (closed / open / agentic / uncued), with archetype-clustered intervals. | `bench.py` |
| **Per-seed variation** | Making generated tasks resistant to leaked answers: perturb inputs, recompute answers by running reference solutions. | `variation.py` |

To extend it:
- **New behaviour change:** add a `Probe` (a function, its old and new behaviour, gold and familiar arguments) to `probes/catalog.py` or a cartridge; gates G1–G12 and the cheat battery check it automatically. [`CONTRIBUTING.md`](CONTRIBUTING.md) walks through it.
- **New model or agent:** any OpenAI-compatible endpoint works with `bench`; a full agent can be measured by wrapping Harbor tasks and running it there.
- **New condition:** `bench.solve` is one function per condition; a read budget, code execution or a docs-search tool are each a few dozen lines.

## Open questions

The pilot answers one question and raises better ones. Each is testable with this repository and a modest compute budget, and each has an open issue to discuss or pick up:

1. **Does looking drop when it costs something?** ([#1](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/1)) In a small repo two pilot models read the library every time and one rarely did. Bury the probes in a large repository, cap the number of reads, and measure the prior-locked rate as the budget shrinks.
2. **Docs or source?** ([#2](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/2)) Answered in part by the pilot: with the source unreadable, two models fell back on memory instead of opening the CHANGELOG. Open: does this hold for frontier models and full agents that can search, and does a hint like "check the release notes" close the gap?
3. **Habit or knowledge?** ([#3](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/3)) On `default_flip` probes, always passing arguments explicitly is enough. Compare `default_flip` against `value_remap`, where only reading helps, across models.
4. **Do synthetic scores predict real ones?** ([#4](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/4)) Inject the same kinds of silent change into forks of real libraries (or use post-cutoff releases) and correlate with the synthetic results.
5. **Can RL teach looking?** ([#5](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/5)) Train a small open model on the agentic condition and test transfer to held-out archetypes and to real-library drift, without regressing on general coding.

## Roadmap

What the reviewers asked for that is still open, in the order they ranked it:

1. **A multi-turn tool environment** (bash, file reads, test runs), docs never pasted in, uncued, packaged for `verifiers` and OpenEnv.
2. **A trained-policy result:** a small GRPO run on an open model, with transfer to held-out archetypes and to real-library drift, and no regression on SWE-bench / Terminal-Bench.
3. **A real-library track:** silent behaviour changes injected into real pinned dependencies of real repositories, plus breaking changes released after model cutoffs, to test whether synthetic scores predict real ones.
4. **More languages** (TypeScript, Java, Go, Rust) and loud failure types (renamed or removed APIs, import moves, deprecations).
5. **Scale:** more models, several samples per item at temperature > 0, and a private held-out seed pool for a leaderboard.

## How it relates to prior work

| Work | Measures | PriorLock adds |
|---|---|---|
| [GitChameleon 2.0](https://arxiv.org/abs/2507.12367) | version-conditioned code completion with executable tests | the agent is not told what changed; it has to find out |
| [VersiCode](https://arxiv.org/abs/2406.07411) | version-specific completion and migration | an agentic condition and a reward, not only a score |
| [LibEvoBench](https://arxiv.org/abs/2606.25402) | version-obliviousness on real libraries; docs help, stating the version does not | whether the agent *fetches* the docs itself |
| [CodeUpdateArena](https://arxiv.org/abs/2407.06249) | whether a model can use a synthetic API update it is given | the update is not given: it sits in the repo, and the agent must notice it |
| [When LLMs Lag Behind](https://arxiv.org/abs/2604.09515) | 270 real API updates as context-memory conflicts; even with docs, about two thirds of code runs | silent same-signature changes, and whether the agent fetches the docs at all |
| [SWE-Chain](https://arxiv.org/abs/2605.14415), [RoadmapBench](https://arxiv.org/abs/2605.15846) | agents performing real release-level upgrades, given the release notes as the spec | nobody tells the agent there is anything to upgrade for |
| [Tool-Memory Conflict](https://arxiv.org/abs/2601.09760) | tool outputs contradicting parametric knowledge | a verifiable, attack-resistant reward for following the environment |
| [Knowledge conflicts](https://arxiv.org/abs/2305.13300) (Xie et al.) | when LLMs follow context that contradicts memory | a coding-agent instance, graded on the calls the code made |
| [Embers of Autoregression](https://arxiv.org/abs/2309.13638) | models default to high-probability answers on low-probability variants | the mechanism the familiar rung is built around |
| [Terminal-Bench](https://arxiv.org/abs/2601.11868) | agents on hard terminal tasks (Harbor) | the probes ride along on its tasks without re-authoring |

The core comparison (closed vs open vs agentic) is the familiar oracle-retrieval versus self-retrieval ablation applied to documentation; what is new here is the grader, the anti-gaming machinery and packaging it as an environment. Notes on each paper are in [`priorlock/papers/`](priorlock/papers/).

## Limitations

- **Pilot scale.** Three free models (no frontier models), temperature 0, 13 archetypes. The results show the instrument separating conditions; they are not a ranking of models.
- **Synthetic, convention-level priors.** The prior being tested is the conventional semantics of a function (keep-first deduplication, truncating top-k, and so on), not memory of one specific real package. That makes tasks contamination-proof and also limits what they say about real libraries (see the roadmap).
- **Defensive habits can score.** On `default_flip` probes, an agent that always writes every argument out explicitly with the conventional value gets full credit without reading anything. `value_remap` probes are the cleanest test of reading; the bench reports results per family.
- **`result_shape` probes are partly answerable from the instruction**, which asks for every record the library returns.
- **The agentic harness is minimal.** `LIST` / `READ` only, no code execution, at most 10 turns. Agents that can run code can discover a changed default by calling the function, which is a different (also useful) skill.
- **No policy was trained**, and the RL environment is single-turn and open-book.
- **The code is public.** Probe logic is in the repository; seeds rotate data and answers, but a private seed pool is needed for a leaderboard.

## Reproduce

```bash
git clone https://github.com/phoenixlibbi/PriorLock-RL-env && cd PriorLock-RL-env
pip install -e ".[dev]"
PYTHONHASHSEED=0 pytest -q
priorlock repro                              # offline determinism fingerprint
```

Details: [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md). Design docs: [`00-THE-GAP.md`](priorlock/docs/00-THE-GAP.md) (the failure mode and evidence), [`04-PROBE-SPEC.md`](priorlock/docs/04-PROBE-SPEC.md) (probe architecture), [`05-LIFECYCLE.md`](priorlock/docs/05-LIFECYCLE.md) (wrap lifecycle), [`06-EVALUATORS.md`](priorlock/docs/06-EVALUATORS.md) (evaluator reports), [`ENVIRONMENT-DIVERSITY.md`](ENVIRONMENT-DIVERSITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Layout

```
src/priorlock/
  bench.py            model benchmark: four conditions, sandboxed grading, clustered intervals
  standalone.py       self-contained task generation and grading
  variation.py        per-seed data with answers recomputed from the library
  probes/             the 13 coding archetypes and the {0, 0.40, 1.0} ladder
  cartridges/         11 domain cartridges, 76 probes
  templates.py        generators for every injected file, including the isolated grader
  inject.py           wrap / unwrap / manifest
  gates.py            the 12 offline gates
  cheats.py           12-class cheat battery + soundness receipt
  leakprobe.py        runtime isolation proof + canary scan
  env.py              verifiers RL environment (load_environment)
  calibrate.py        per-model probe informativeness
  cli.py
tablixdemo/           reference authored domain (also wrapped)
results/              bench runs and receipts
priorlock/docs/       design docs
priorlock/papers/     literature notes
```

## Author

**Muhammad Labeeb Tariq** · [labeebjutt80@gmail.com](mailto:labeebjutt80@gmail.com) · [@phoenixlibbi](https://github.com/phoenixlibbi)

## License

MIT
