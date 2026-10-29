# PriorLock

> **Do coding agents read the documentation, or code from memory?** An open RL environment, benchmark and hardened verifier for one failure: when an installed library's behaviour has changed without changing its signature, code written from memory runs, passes every visible test, and is wrong.

[![tests](https://github.com/phoenixlibbi/PriorLock-RL-env/actions/workflows/test.yml/badge.svg)](https://github.com/phoenixlibbi/PriorLock-RL-env/actions/workflows/test.yml)
[![Stage-0 gates](https://github.com/phoenixlibbi/PriorLock-RL-env/actions/workflows/stage0.yml/badge.svg)](https://github.com/phoenixlibbi/PriorLock-RL-env/actions/workflows/stage0.yml)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

**Status:** research in progress. Every experiment so far ran on free-tier or local models. The tables below are generated from the logged runs and refresh as runs finish; every model reply, file read and verdict is in [`results/`](results/).

## Abstract

Coding agents work in repositories whose dependencies are pinned to versions the model may never have seen. When a library keeps a function's signature but changes what it does, code written from memory raises no error and passes the visible tests; the only signal is the library's own documentation. **We ask whether agents go and read it.**

PriorLock builds tasks around synthetic, contamination-free libraries whose behaviour changed silently, and grades the library calls the agent's code actually made, with an isolated, red-teamed verifier, on a three-rung ladder: never called the library (0), called it the memorized way (0.40), called it the documented way (1.0). In **bench v2**, 36 behaviour changes sit inside realistic repositories where the change is written in exactly one place (a CHANGELOG, a migration guide, API reference pages, a type stub or a README).

Across the free models tested so far, models apply the change almost perfectly when the documentation is in the prompt (89–100% right calls), but **when they must find it themselves, right calls fall to 8–29%**. The failure is in looking, not in understanding: when a model found the note it made the right call 79–87% of the time, and when it did not, 12–26%. Telling a model that the library was upgraded does not help; telling it to check the documentation, or letting it run code, helps the model that looks, and does nothing for models that answer without looking. Looking is a habit, which makes it a training target; PriorLock packages the tasks, the verifier and the reward as an open building block for that.

<!-- V2_FINDINGS_START -->
## Key findings so far

Free models only, temperature 0. Bench v2 is still running (see the timestamp on the tables): Gemini 3.1 Flash-Lite has completed the first task set (all 36 changes) on 4 conditions; Gemini 3.5 Flash-Lite and gpt-oss-120b are partway through and resume when their free daily quotas reset. Cells hold about 5–12 tasks, so read these as directions with wide intervals, not estimates.

1. **The tasks are solvable; the information is the bottleneck.** With the docs in the prompt: Gemini 3.5 Flash-Lite 100%, gpt-oss-120b 100%, Gemini 3.1 Flash-Lite 89% right calls.
2. **When the agent must find the docs, it mostly does not.** Library compiled, no hint: Gemini 3.5 Flash-Lite 29%, Gemini 3.1 Flash-Lite 22%, gpt-oss-120b 8%. The same drop appeared in the v1 pilot on four models from three vendors (12–27%).
3. **Finding the note is what matters.** When the agent found the note describing the change it made the right call 79–87% of the time (Gemini 3.1: 79% vs 12% when it did not; Gemini 3.5: 87% vs 26%).
4. **Two different failures.** The Gemini models look, but mostly at the library's code: with readable source Gemini 3.5 Flash-Lite reached 78%. gpt-oss-120b does not look at all: it answered on its first turn in every compiled-library task, even when told to check the documentation.
5. **Telling the version does not help; telling what to do helps only a model that looks.** For Gemini 3.5 Flash-Lite: "upgraded to 2.0" 28%, "check the documentation" 38%, "defaults changed; the docs describe it" 61%, consistent with [LibEvoBench](https://arxiv.org/abs/2606.25402)'s finding that stating the target version gives no benefit. "Check the documentation" did not move Gemini 3.1 Flash-Lite (22% → 22%) or gpt-oss-120b (8% → 7%).
6. **Running the code is the strongest lever so far.** With a RUN tool and no hint, Gemini 3.5 Flash-Lite tested the library directly and reached 72%; Gemini 3.1 Flash-Lite 39%.
7. **Agents look next to the code, not in the docs folder.** Without a hint, a change written in the type stub inside the library folder was found in 3 of 4 tasks (75% right calls); one written in the CHANGELOG or a migration guide was found in 0 of 14 (0–14% right calls).
<!-- V2_FINDINGS_END -->

## Contents

1. [Problem](#1-problem) · 2. [Method](#2-method) · 3. [Experimental setup](#3-experimental-setup) · 4. [Results](#4-results) · 5. [Discussion](#5-discussion) · 6. [Limitations](#6-limitations-and-threats-to-validity) · 7. [Corrections log](#7-corrections-log) · 8. [Use it](#8-use-it-an-open-building-block) · 9. [Next experiments](#9-next-experiments-for-labs-and-collaborators) ([Study 2 plan](#91-study-2-next-silent-dependency-changes-inside-real-repositories)) · 10. [Related work](#10-related-work) · 11. [Reproduce](#11-reproduce)

---

## 1. Problem

Models learn libraries from a frozen snapshot of the internet. Libraries keep moving, and some changes keep the signature while changing the behaviour: a default flips, an option name starts to mean something else, a result gains extra rows. Real releases do this; scikit-learn 1.4, for example, changed the default of `KMeans(n_init=…)`. Code written from memory against such a library:

- **runs**: no exception, no deprecation warning;
- **passes the visible tests**, which rarely pin the exact semantics;
- **is wrong**, and nothing tells the agent to look.

The note that would have saved it is usually sitting in the repository: a CHANGELOG entry, a migration guide, a docstring, a type stub. This matters twice for anyone training coding agents with RL. Agents deployed on pinned, internal or post-cutoff dependencies hit it daily. And a reward computed from tests that cannot see the difference trains the memorized behaviour in, instead of out.

Prior work measured the knowledge side: whether a model can use an update it is given, or knows a stated version ([§10](#10-related-work)). PriorLock asks the agentic side:

| | Research question | How it is measured |
|---|---|---|
| **RQ1** | Can agents apply a documented behaviour change when they are handed the documentation? | open-book condition (ceiling) |
| **RQ2** | Do agents find that documentation themselves when nobody hands it over? | agentic conditions, library compiled, no hint |
| **RQ3** | What changes that: a hint, the ability to run code, where the change is written? | hint ladder, RUN tool, five documentation channels |
| **RQ4** | Can the behaviour be measured robustly enough to serve as an RL reward? | call-observing verifier, cheat battery, integrity gates |

## 2. Method

### 2.1 Behaviour changes (probes)

Each probe is one library function whose behaviour changed in the installed major version **without changing its signature**. There are three families:

| Family | What changed | Example (names and data vary per task) |
|---|---|---|
| `default_flip` | a default value was inverted | `to_seconds(values, unit="ms")` now assumes milliseconds; 1.x assumed seconds |
| `value_remap` | an accepted value now means something else | `fill_gaps(method="forward")` now fills from the *next* reading; 1.x carried the previous one |
| `result_shape` | the result's shape changed | `top_k()` returns every record tied at the cut-off, so it may return more than `k` |

The catalog has **36 coding behaviour changes**: the original 13, plus 23 added for bench v2 around everyday conventions (time units, percentile interpolation, page numbering, CSV headers and quoting, slug separators, week starts, day counts, log-level thresholds, version ordering, config parsing, camelCase styles, and more). Their gold and memorized outputs are computed by running the code, never written by hand. The library itself is synthetic, so the change cannot have been seen in pre-training; what is tested is the *conventional* behaviour a model expects (keep the first duplicate, sort ascending, interpolate percentiles linearly).

### 2.2 Reward ladder

The verifier imports a pristine copy of the library in an isolated child process, wraps each probed function and records the arguments the solution *explicitly supplied* (`inspect.Signature.bind`, defaults excluded). Per probe:

| Score | Verdict | Requires |
|---|---|---|
| **1.00** | `override` | every call uses the documented behaviour **and** the output is right |
| **0.40** | `prior_locked` | the memorized call, producing the memorized output |
| **0.40** | `correct_output_other_call` | the right output reached some other way |
| **0.00** | `inconsistent_calls` | the probed argument took different values across calls (spraying options) |
| **0.00** | `bypassed` | the library function was never called |
| 0.00 | `incorrect`, `correct_call_bad_output` | anything else |

The 0.40 rung is structural: it is what the memorized solution earns, it is checked on every task, and no route earns more without the documented call. Grading the *call* rather than the output is what makes the reward un-guessable: there is no accidental way to pass `keep="first"`.

### 2.3 Verifier hardening

The verifier was red-teamed before release by ten independent AI reviewers (five roles, and five that each read one lab's public research). They found four exploits, three of which scored a perfect 1.0 without doing the task; all are fixed and kept as permanent tests.

| Attack | What stops it |
|---|---|
| Read the grader or reference answers on disk | answer files are removed while the solution runs; root grading also drops to `nobody` |
| Reach into the grading process, print a fake report | the solution runs in a separate process; the grader ignores its output and writes its own report, stamped with a nonce passed over stdin |
| Spray every argument value, knowing the right outputs | all calls must agree on the probed argument |
| Edit the library or the tests; constant outputs; timeouts | the verifier owns a pristine copy; wrong values score 0; the child is killed |

**Residual risk.** The solution and the call recorder share the child process, so a solution can forge its own call record; that only helps if it already knows the documented argument, which is the knowledge being measured.

### 2.4 Bench v2: realistic repositories, one documentation channel

v1 tasks are a library, two doc files and an instruction. In v2 each task is a **small, realistic project**: application modules that use the library's unchanged helpers, unit tests, a CI workflow, a Makefile, a project CHANGELOG, a runbook, a data-contracts page, an ADR explaining why the library is vendored, and the vendored library with its own README, CHANGELOG and API overview. Finding the right note takes real searching.

Each task writes its behaviour changes in **exactly one place**, its *channel*:

| Channel | Where the change is written | Everywhere else |
|---|---|---|
| `changelog` | the library's `CHANGELOG.md`, 2.0.0 section | — |
| `migration` | `MIGRATION-2.0.md`, a 1.x → 2.0 upgrade guide | the CHANGELOG's 2.0.0 entry mentions only performance |
| `api_reference` | one page per function, with a "Changed in 2.0" note | as above |
| `stub` | the type stub `<lib>/__init__.pyi` shipped next to the compiled library | as above |
| `readme` | an "Upgrading to 2.0" section of the library's README | as above |

`check_channel_isolation` verifies, for every task, that the change's description, its option values and its new default appear in no other agent-visible file. 24 tasks (two task sets, each covering all 36 changes in groups of three) rotate the five channels.

### 2.5 Conditions

| Condition | What the agent gets | Question |
|---|---|---|
| `repo_open` | the channel's documents pasted into the prompt | RQ1: can it apply the change? (ceiling) |
| `repo_source` | `LIST`, `READ`, `GREP`; library shipped as readable Python | does it find the behaviour in the code? |
| `repo_docs` | as above, library shipped compiled (a one-line `__init__.py` and a binary) | RQ2: does it find the docs? |
| `repo_docs_h1` | + "the vendored library was upgraded from 1.4 to 2.0" | does knowing the version help? |
| `repo_docs_h2` | + "check the library's documentation before relying on its defaults" | does a nudge to look help? |
| `repo_docs_h3` | + "several defaults and option meanings changed; the docs describe them" | does an explicit warning help? |
| `repo_run` | `repo_docs` + `RUN`: execute Python at the repo root in a network-less sandbox | does testing replace reading? |

No condition tells the agent which function changed. In every condition the instruction is uncued (no version tag, no pointer to the docs, no bold on the required behaviour), and the agent sees the task's input file.

### 2.6 Agent harness

A deliberately minimal, model-agnostic agent: one action per turn (`LIST`, `READ`, `GREP`, and `RUN` where enabled), at most 15 turns, then a final request for the answer. Temperature 0, the same system prompt for every model, any OpenAI-compatible endpoint. Every reply is stored with the run. When a model emits an action as a native tool call (gpt-oss on Groq does), the harness reads it back (`recover_action`) instead of losing it, and counts each recovery. In the RUN sandbox the library is a sourceless `.pyc`, so `help()` and calling the functions work but its source cannot be read.

### 2.7 Metrics

- **Right call**: the probed function was called with the installed version's behaviour on every call (`override` or `correct_call_bad_output`).
- **Prior-locked**: the memorized call producing the memorized output.
- **Found the change**: the agent read a channel file, or a `GREP` result showed it a line from one.
- **Looked at the library**: the agent opened a file in the library's own folder.

95% intervals come from a bootstrap that resamples whole behaviour changes (archetypes), not probes, because repeats of one change are correlated.

## 3. Experimental setup

| Model | Access (free) | v1 pilot | Bench v2 |
|---|---|---|---|
| Gemini 3.5 Flash-Lite | Google AI Studio free tier (500 requests/day) | 5 conditions | all 7 conditions |
| Gemini 3.1 Flash-Lite | Google AI Studio free tier | 3 conditions | 4 core conditions |
| Gemma 4 31B | Google AI Studio free tier | partial | 4 core conditions (queued) |
| gpt-oss-120b | Groq free tier (8,000 tokens/min) | 3 conditions | 4 core conditions |
| Qwen3.8 27B | Groq free tier | partial | 4 core conditions (queued) |
| Nemotron 3 Ultra | OpenRouter `:free` (50 requests/day) | — | small slice (queued) |
| Qwen2.5-Coder 7B | local, Ollama | 4 conditions | 4 core conditions (queued) |

The core conditions are `repo_open`, `repo_docs`, `repo_docs_h2` and `repo_run`. One model runs at a time; a model stops when its provider reports the daily quota is used up, and unfinished cells resume the next day (a failed call is never recorded as a result). Models that could not be run (Gemini 3.5 Flash: quota; Gemini 2.5 Flash: retired) are not reported.

**Validation before any model ran.** On all 24 v2 tasks, the Docker grader gives the reference solutions exactly gold 1.00 · memorized 0.40 · bypass 0.00 · empty 0.00 (96 of 96). The test suite (62 tests, CI on Python 3.10–3.13) covers scripted agents with known behaviour (a reading agent scores 1.0 and is recorded as having found the change; a memory agent scores 0.40 and is not), channel isolation for every channel, the RUN sandbox (it runs the library but cannot show its source) and the action parser.

## 4. Results

### 4.1 Bench v2

<!-- V2_TABLES_START -->
_Last updated 2026-10-29 05:03 · 117 runs · gemini-3.1-flash-lite (48 runs), gemini-3.5-flash-lite (45 runs), gemma-4-31b-it (2 runs), openai/gpt-oss-120b (22 runs)._

### Right calls by condition (the hint ladder)

| Model | repo_open | repo_source | repo_docs | repo_docs_h1 | repo_docs_h2 | repo_docs_h3 | repo_run |
|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | 89% | – | 22% | – | 22% | – | 36% |
| gemini-3.5-flash-lite | 100% | 78% | 29% | 28% | 38% | 61% | 72% |
| gemma-4-31b-it | 100% | – | 33% | – | – | – | – |
| openai/gpt-oss-120b | 100% | – | 8% | – | 7% | – | – |

### Where the change was written (all models pooled)

| Channel | Open book: right call | Compiled, no hint: right call | Compiled, no hint: found the change |
|---|---|---|---|
| changelog | 100% (24/24) | 17% (4/24) | 0% (0/8) |
| migration | 95% (20/21) | 0% (0/21) | 0% (0/7) |
| api_reference | 100% (15/15) | 7% (1/15) | 20% (1/5) |
| stub | 100% (15/15) | 75% (9/12) | 75% (3/4) |
| readme | 75% (9/12) | 25% (3/12) | 25% (1/4) |

### By probe family (compiled library, all hints and RUN pooled)

| Family | Right call | Prior-locked |
|---|---|---|
| default_flip | 28% (40/144) | 45% (65/144) |
| value_remap | 17% (12/72) | 47% (34/72) |
| result_shape | 80% (24/30) | 0% (0/30) |

### Did finding the change help? (compiled library, all hints and RUN pooled)

| Model | Right call when it found the change | Right call when it did not |
|---|---|---|
| gemini-3.1-flash-lite | 79% (19/24) | 12% (10/84) |
| gemini-3.5-flash-lite | 87% (26/30) | 26% (17/66) |
| gemma-4-31b-it | – | 33% (1/3) |
| openai/gpt-oss-120b | – | 8% (3/39) |

<details><summary>Every model and condition (found / looked / GREP / RUN / turns)</summary>

### Every model and condition

| Model | Condition | Tasks | Right call [95% CI] | Prior-locked | Found the change | Looked at the library | Used GREP | Used RUN | Mean turns |
|---|---|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | repo_open | 12 | **89%** [78%, 97%] | 3% (1/36) | 100% (12/12) | 0% (0/12) | 0% (0/12) | 0% (0/12) | 1.0 |
| gemini-3.1-flash-lite | repo_docs | 12 | **22%** [8%, 36%] | 36% (13/36) | 25% (3/12) | 92% (11/12) | 42% (5/12) | 0% (0/12) | 7.4 |
| gemini-3.1-flash-lite | repo_docs_h2 | 12 | **22%** [8%, 36%] | 25% (9/36) | 25% (3/12) | 100% (12/12) | 67% (8/12) | 0% (0/12) | 10.2 |
| gemini-3.1-flash-lite | repo_run | 12 | **36%** [22%, 53%] | 50% (18/36) | 17% (2/12) | 100% (12/12) | 0% (0/12) | 83% (10/12) | 8.0 |
| gemini-3.5-flash-lite | repo_open | 7 | **100%** [100%, 100%] | 0% (0/21) | 100% (7/7) | 0% (0/7) | 0% (0/7) | 0% (0/7) | 1.0 |
| gemini-3.5-flash-lite | repo_source | 6 | **78%** [56%, 94%] | 6% (1/18) | 0% (0/6) | 100% (6/6) | 0% (0/6) | 0% (0/6) | 4.3 |
| gemini-3.5-flash-lite | repo_docs | 7 | **29%** [10%, 48%] | 48% (10/21) | 29% (2/7) | 86% (6/7) | 14% (1/7) | 0% (0/7) | 5.1 |
| gemini-3.5-flash-lite | repo_docs_h1 | 6 | **28%** [11%, 50%] | 44% (8/18) | 17% (1/6) | 100% (6/6) | 17% (1/6) | 0% (0/6) | 5.0 |
| gemini-3.5-flash-lite | repo_docs_h2 | 7 | **38%** [19%, 62%] | 52% (11/21) | 43% (3/7) | 100% (7/7) | 43% (3/7) | 0% (0/7) | 9.3 |
| gemini-3.5-flash-lite | repo_docs_h3 | 6 | **61%** [39%, 83%] | 17% (3/18) | 50% (3/6) | 100% (6/6) | 50% (3/6) | 0% (0/6) | 9.3 |
| gemini-3.5-flash-lite | repo_run | 6 | **72%** [50%, 89%] | 28% (5/18) | 17% (1/6) | 83% (5/6) | 0% (0/6) | 100% (6/6) | 8.7 |
| gemma-4-31b-it | repo_open | 1 | **100%** [100%, 100%] | 0% (0/3) | 100% (1/1) | 0% (0/1) | 0% (0/1) | 0% (0/1) | 1.0 |
| gemma-4-31b-it | repo_docs | 1 | **33%** [0%, 100%] | 67% (2/3) | 0% (0/1) | 100% (1/1) | 100% (1/1) | 0% (0/1) | 8.0 |
| openai/gpt-oss-120b | repo_open | 9 | **100%** [100%, 100%] | 0% (0/27) | 100% (9/9) | 0% (0/9) | 0% (0/9) | 0% (0/9) | 1.0 |
| openai/gpt-oss-120b | repo_docs | 8 | **8%** [0%, 21%] | 58% (14/24) | 0% (0/8) | 0% (0/8) | 0% (0/8) | 0% (0/8) | 1.0 |
| openai/gpt-oss-120b | repo_docs_h2 | 5 | **7%** [0%, 20%] | 40% (6/15) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 1.0 |

</details>
<!-- V2_TABLES_END -->

Full tables: [`results/bench_v2/REPORT.md`](results/bench_v2/REPORT.md) · raw runs with every reply: [`results/bench_v2/*.jsonl`](results/bench_v2/) · logs: [`results/bench_v2/logs/`](results/bench_v2/logs/).

### 4.2 Pilot (v1): agents that seem to read the docs are reading the code

The pilot used 13 behaviour changes in small task folders, with the change described in the CHANGELOG, the API reference and the library's docstrings. With readable source the Gemini models got everything right, but they had read the code, never the CHANGELOG. Shipping the library compiled, so the docs were the only source, separated the two:

| Model | Library code readable | Library compiled, docs readable | Opened the docs |
|---|---|---|---|
| Gemini 3.5 Flash-Lite | **100%** right call | **23%** [0%, 46%], 58% coded from memory | 0 of 8 tasks |
| Gemini 3.1 Flash-Lite | **100%** | **27%** [8%, 50%], 50% coded from memory | 1 of 8 tasks |
| gpt-oss-120b (Groq) | **12%** [3%, 24%], opened no file | **25%** [6%, 47%], opened no file | 0 of 10 tasks |
| Qwen2.5-Coder 7B (local) | 15% [0%, 38%] | 15% [0%, 38%] | 0 of 4 tasks |

With the docs in the prompt the same models scored 96–100% (Qwen2.5-Coder 7B: 62%). On the two families that genuinely require the docs (`default_flip`, `value_remap`), the Gemini models made 1 right call out of 40 once the source was compiled. gpt-oss-120b answered on its first turn in 18 of 20 agentic tasks; in the other 2 its actions may have been lost to the native tool-call issue later found in v2 ([§7](#7-corrections-log)). Its two agentic rows are effectively the same condition for a model that does not look, so the gap between them is run-to-run noise.

<details>
<summary>Full v1 table: every condition, verdict mix and per-family breakdown</summary>

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

Closed-book (signatures with defaults hidden, no docs, no source) shows the prior: Gemini 3.5 Flash-Lite used the memorized behaviour 46% of the time, and on all 8 `value_remap` probes. Raw runs: [`results/bench/`](results/bench/).
</details>

### 4.3 Validity of the instrument

| Check | Result | Command |
|---|---|---|
| Reference ladder on every v2 task, in the Docker grader | gold 1.00 · memorized 0.40 · bypass 0.00 · empty 0.00 on **24 of 24** tasks | `pytest tests/test_repo_v2.py` |
| Channel isolation | the change appears only in its channel on **24 of 24** tasks | `check_channel_isolation` |
| Cheat battery: 12 attack classes × 13 archetypes | **every class caught on every archetype**; best cheat score 0.40, never above the do-nothing baseline | `priorlock cheats <task> --suite` · [receipt](results/receipts/soundness-receipt.json) |
| Runtime isolation (Harbor, 49 attempts) | 0 oracle assets reachable from the agent | `priorlock leakprobe <task>` · [trace](results/receipts/leakprobe-trace.json) |
| Wrapped Harbor task | **12 of 12** offline gates pass; host verifier byte-identical | `priorlock wrap <task> && priorlock stage0 <task>` |

The cheat receipt pools 156 runs for a Wilson upper bound of 2.4% on false accepts; runs of one class are correlated, so read it as "no class got through anywhere", not as 156 independent trials.

## 5. Discussion

**Not knowing versus not looking.** Every model that was handed the documentation applied it. The gap opens only when the agent has to decide to look, and it is large: 60–90 points. The cause shows up in the logs as two distinct behaviours. Some models look, but at the library's code, and fall back on memory when the code is unreadable. Others write their answer before opening anything.

**A habit, so a training target.** A one-sentence hint ("check the documentation") or a tool (RUN) moved the model that already explores by up to 30–40 points; knowing the version did not. That is the signature of a missing habit rather than missing knowledge, which is exactly what RL changes. It also says what such an environment must reward: the *call the code made*, because tests that cannot tell the two behaviours apart reward memory. PriorLock's verifier is built for that, and is tested against the obvious ways to game it.

**Where the docs live.** Agents searched where the code is: the library folder and, with GREP, wherever a search term hit. Release notes and migration guides in a docs folder were the least likely to be found. For library authors this argues for stating behaviour changes where tools look (docstrings, type stubs); for agent builders, for a "check what changed in the dependency" step.

**Testing beats reading.** Given the ability to run code, the best model tested the library's actual behaviour instead of reading about it, and did best. A sandboxed RUN step is cheap and probably the most practical mitigation today.

## 6. Limitations and threats to validity

- **Small, free models only.** Flash-Lite-class and open-weight models at temperature 0; no frontier model, no full agent scaffold yet. The effect may shrink for stronger agents; [§9](#9-next-experiments-for-labs-and-collaborators) is the plan to test that.
- **Sample size.** Bench v2 cells hold a handful of tasks; free-tier quotas bound how many. Intervals are wide and reported.
- **Synthetic libraries.** They make the change impossible to have memorized, but they test conventional priors, not memory of one real package. A real-library track is planned.
- **Minimal harness.** One action per turn, 15 turns. Real agents batch actions, search more and run tests; the RUN condition covers part of that.
- **Defensive habits can score.** On `default_flip` probes an agent that always writes every argument explicitly with the conventional value is right without reading; `value_remap` is the cleanest test of reading, so results are reported per family. `result_shape` probes are partly answerable from the instruction.
- **Provider quirks.** gpt-oss on Groq sometimes emits actions as native tool calls; the harness reads them back and counts them, and runs where a reply was lost were removed ([§7](#7-corrections-log)).
- **Domain cartridges.** Besides the coding catalog, 11 domain cartridges (76 probes) exist for wrapping Harbor tasks; only `coding` and `fundamentals` currently produce exact reference ladders, and only those are used in the benchmark. The integrity gates reject any task whose ladder is not exact.
- **The RL environment is single-turn** and open-book (`verifiers`); no policy has been trained yet.

## 7. Corrections log

Problems found during the study, and what was done. None changed a reported number except where stated.

| Found | Effect | Fix |
|---|---|---|
| Grading a reference solution left it in the task folder | two v1 `fundamentals` tasks had the 0.40 reference visible to the agent; every logged action was checked, and no model opened it | `grade()` removes what it placed; a test checks no answer is left behind |
| After a rate-limit (429) retry, the request body was replaced by the error text | the retried calls failed; failed calls are never recorded, so no result was affected | fixed, with regression tests |
| gpt-oss on Groq emits some actions as native tool calls, which reached the harness as empty replies | its v2 RUN runs lost actions; 9 such runs were removed before analysis and are rerun | `recover_action` reads the call back; each run records how many it recovered |
| The v1 write-up said gpt-oss "never opened a file" | too strong: 2 of its 20 agentic tasks are uncertain for the reason above | wording corrected |

## 8. Use it: an open building block

```bash
pip install "git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"
priorlock info
```

Python 3.10–3.13, standard library only. Docker is optional (it sandboxes model-written code and runs `RUN`); Harbor is only needed for `wrap` and `leakprobe`.

**Quickstart, no model, one minute.**

```bash
priorlock run -o my-task --seed demo                # synthetic library + docs + data + smoke test
priorlock run --grade my-task --reference gold      # 1.0
priorlock run --grade my-task --reference familiar  # 0.40  (the memorized answer)
priorlock run --grade my-task --reference stub      # 0.0
```

**Benchmark a model.**

```bash
priorlock bench --suite v2 --provider gemini --model gemini-3.5-flash-lite --rpm 12 \
    --condition repo_open --condition repo_docs --condition repo_docs_h2 --condition repo_run
priorlock bench --suite v2 --base-url http://localhost:8000/v1 --model my-model    # any OpenAI-compatible endpoint
priorlock bench --provider ollama --model qwen2.5-coder:7b                          # v1 pilot suite, local
priorlock bench --report results/bench_v2/*.jsonl                                   # tables
```

Runs are resumable (one JSON line per task and condition, with the code, every reply, the files read and per-probe verdicts); `--only REGEX` picks tasks; a model stops cleanly when its daily quota is used up.

**Reuse the parts.**

| Piece | Reuse it for | Where |
|---|---|---|
| Call-observing verifier | any RL environment where *how* an API was used matters, not only the output | `templates.py` (`GRADER`, `CHILD_SOURCE`) |
| Structural reward ladder | a dense reward whose middle rung is "plausible but wrong", which cheating cannot beat | `probes/base.py` |
| Realistic repo builder with channel isolation | testing whether agents find information placed in one known location | `repo_v2.py` |
| Condition harness | separating "cannot" from "does not" for any grounding skill (open / agentic / hints / RUN) | `bench.py`, `repo_v2.py` |
| Cheat battery | red-teaming any verifier, with execution markers and pooled receipts | `cheats.py` |
| Probe injection | adding this measurement to an existing Harbor / Terminal-Bench task without touching its verifier | `inject.py`, `gates.py` |
| Per-seed variation | tasks whose leaked answers do not transfer: perturb inputs, recompute answers by running references | `variation.py` |

**Starter recipes** in [`examples/`](examples/), each under 80 lines and checked in CI: [define your own behaviour change](examples/01_your_own_behaviour_change.py) and get a gated task · [plug in your agent](examples/02_plug_in_your_agent.py) · [use the verifier as the reward in your RL loop](examples/03_reward_for_your_rl_loop.py).

**RL environment.** `vf.load_environment("priorlock")` (`pip install "priorlock[rl]"`) returns a `verifiers` environment: each instance draws its own changes and data, evaluation holds out whole archetypes, and the system prompt never says that anything changed. It is single-turn with the docs in the prompt, so it trains *acting on* documentation, not *deciding to look*; the multi-turn version is the first item in §9.

**Wrap a Harbor task.** `priorlock wrap <task>` adds probes to an existing Terminal-Bench / Harbor task, keeps its verifier byte-identical and reports two scores (`task_score`, `gap_score`) and a composite; `priorlock stage0` runs the 12 integrity gates and `priorlock unwrap` removes exactly what was added. Lifecycle details: [`priorlock/docs/05-LIFECYCLE.md`](priorlock/docs/05-LIFECYCLE.md).

## 9. Next experiments, for labs and collaborators

Everything above ran on free tiers. The pipeline is complete; these are the experiments it is ready for, and what each needs.

| Experiment | Answers | Needs | Status |
|---|---|---|---|
| Frontier models on bench v2 (Claude, GPT, Gemini Pro), all 7 conditions | does the gap close with stronger models? | about 3,000–5,000 API calls | applied for research credits |
| A standard agent scaffold (Terminus-2 via Harbor, mini-swe-agent) on a v2 subset | is the gap an artifact of the minimal harness? | the same models, about 5–20× more calls per task | v2 tasks export to Harbor via `wrap` |
| Multi-turn `verifiers` / OpenEnv environment with LIST / READ / GREP / RUN | a trainable version of "decide to look" | engineering only | next |
| Small GRPO run on an open model, held-out archetypes and channels | can RL teach looking, and does it transfer? | a few GPU-days | open, [#5](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/5) |
| Study 2: counterfactual dependency changes inside real repositories (SWE-bench Pro public set), see §9.1 | does it happen in real software? | engineering, per-task review; free models for the pilot | planned, [#4](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/4) |
| Read budgets in large repositories | does looking drop when it costs something? | engineering only | open, [#1](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/1) |

Also open: docs or source ([#2](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/2)) and habit or knowledge ([#3](https://github.com/phoenixlibbi/PriorLock-RL-env/issues/3)). If you can run any of these, or want the results on your models, open an issue or get in touch.

### 9.1 Study 2 (next): silent dependency changes inside real repositories

**Status: planned, not started.** This is the handover plan for whoever builds Study 2; the raw survey data is in [`research/swebench-pro-survey.json`](research/swebench-pro-survey.json).

#### 9.1.1 Why a second study

Study 1 shows the effect under control: models apply a documented behaviour change when they are handed the docs (93–100% right calls) but mostly do not find the docs themselves (8–33%). It cannot show that this happens in real software, because its libraries and repositories are generated. Study 2 keeps the question and the verifier, and replaces the generated parts with real ones:

| | Study 1 (now) | Study 2 (this plan) |
|---|---|---|
| Repository | generated mini-project | a complete real repository at a real commit |
| Environment | `python:3.11` + task files | the repository's own Docker image (dependencies pinned and installed) |
| Library | synthetic (`funckit`, …) | a real dependency the project uses (PyYAML, Jinja2, python-dateutil, …) |
| Behaviour change | synthetic | **counterfactual**: one real function's behaviour silently changed in the installed copy and documented in that library's own style |
| Task | "data-processing checks" naming the function | a short, natural change to the real project that needs that function |
| Grading | the library call + output | the library call (same verifier) + the repository's own tests |

#### 9.1.2 Design decision: counterfactual changes, not "releases after the cutoff"

Training cutoffs are unknown, differ between models and keep moving, so an experiment built on "releases the model has not seen" cannot be reproduced. Instead, each task changes a real function in a way that **never existed**: no model can have trained on it, the same patched environment gives the same test for every model in any year, and there is no limit on how many changes can be made. The model's pull toward the old behaviour is real, because it knows the real library well.

A **closed-book check per model** is still required (not for cutoffs): run the task with no repository access and confirm the model uses the *original* behaviour. A change the model happens to guess right is dropped for that model.

#### 9.1.3 Why SWE-bench Pro's public set fits

[SWE-bench Pro](https://arxiv.org/abs/2509.16941) tasks are very hard (under 25% solved), but Study 2 does **not** use its tasks, only its repositories and environments:

- complete, actively maintained codebases with real docs, tests and CI;
- a ready, pinned Docker image per instance (`ghcr.io/scaleapi/swe-bench_pro-v2:<tag>`), which removes the most expensive step of building environments;
- many base commits per repository, so tasks can be spread across versions;
- our own tasks stay small and isolated, so a failure means "did not notice the change", not "could not solve a huge PR".

#### 9.1.4 Survey of the public set (2026-10-29)

Source: Hugging Face `ScaleAI/SWE-bench_Pro` (config `default`, 642 tasks), the GitHub API and the registry manifests (metadata only; nothing was downloaded). Raw data: [`swebench-pro-survey.json`](research/swebench-pro-survey.json).

| Repository | Tasks | Language | Licence | Stars | Repo size | Image (compressed) |
|---|---|---|---|---|---|---|
| ansible/ansible | 82 | Python | GPL-3.0 | 71k | 261 MB | 0.75 GB |
| internetarchive/openlibrary | 82 | Python | AGPL-3.0 | 6.8k | 126 MB | 1.07 GB |
| qutebrowser/qutebrowser | 73 | Python | GPL-3.0 | 11.7k | 64 MB | 0.75 GB |
| flipt-io/flipt | 78 | Go | not asserted | 4.9k | 107 MB | 1.93 GB |
| gravitational/teleport | 68 | Go | AGPL-3.0 | 21k | 1.5 GB | 3.50 GB |
| future-architect/vuls | 58 | Go | GPL-3.0 | 12.3k | 32 MB | 1.20 GB |
| navidrome/navidrome | 52 | Go | GPL-3.0 | 24.4k | 71 MB | 0.92 GB |
| protonmail/webclients | 55 | JavaScript | GPL-3.0 | 5.7k | 4.2 GB | 6.52 GB |
| element-hq/element-web | 52 | JavaScript | AGPL-3.0 | 13.6k | 613 MB | 1.84 GB |
| NodeBB/NodeBB | 38 | JavaScript | GPL-3.0 | 15.2k | 111 MB | 0.98 GB |
| tutao/tutanota | 4 | TypeScript | GPL-3.0 | 8.1k | 288 MB | 1.21 GB |

**Python repositories and the dependencies they pin** (candidates for counterfactual changes):

| Repository | Third-party dependencies (from `requirements*.txt` at a base commit) |
|---|---|
| ansible/ansible | PyYAML, cryptography, jinja2, packaging, resolvelib |
| internetarchive/openlibrary | Babel, beautifulsoup4, python-dateutil, httpx, lxml, Pillow, pydantic, PyYAML, feedparser, isbnlib, pymarc, … |
| qutebrowser/qutebrowser | Jinja2, MarkupSafe, PyYAML, Pygments, attrs, colorama, cssutils |

**Recommended pilot repositories:** `internetarchive/openlibrary` (the widest spread of everyday dependencies: dates, HTML, HTTP, YAML) and `ansible/ansible` (PyYAML and Jinja2 at the centre of the project, the largest community). Both have small images and many base commits. `qutebrowser` is a good third (needs Qt, so its tests may be heavier).

#### 9.1.5 How a task is built

1. **Pick a repository and base commit**, and pull that instance's Docker image.
2. **Pick a dependency function the project really calls** (search the codebase), with a parameter or behaviour a model has a strong prior about. Examples to evaluate: `yaml.dump(sort_keys=…)`, `dateutil.parser.parse(dayfirst=…)`, `jinja2.Environment(autoescape=…)`, `BeautifulSoup.get_text(strip=…)`, `packaging.specifiers.SpecifierSet(prereleases=…)`.
3. **Make the counterfactual change in the installed copy** inside the image (`site-packages`): same signature, plausible new behaviour (flip a default, change what one option value means, or change an edge case). Bump the installed version (for example PyYAML 6.0.1 → 7.0.0) consistently in `__version__` and the `dist-info` metadata.
4. **Document it where that ecosystem documents changes**, in exactly one channel per task: the function's docstring in the installed source, the package's changelog / release notes in `dist-info`, the project's own changelog or upgrade notes ("bumped PyYAML to 7.0"), or a comment next to the pin in `requirements.txt`. Keep a channel-isolation check, as in Study 1.
5. **Write a short, natural task in the project** that needs that function (a small feature, helper or fix, a few lines to a few dozen), with the instruction in the project's issue style and no hint that anything changed.
6. **Grade two ways:** the call-observing verifier wraps the real dependency function and records the arguments the agent's code passed (documented call 1.0 / memorized call 0.40 / not called 0), and the repository's own tests check nothing else broke. Write hidden tests that distinguish the old and new behaviour.
7. **Validate before any model runs:** a gold patch scores 1.0, a memorized-behaviour patch scores 0.40, a no-op scores 0, the repository's tests pass on gold, and the closed-book check shows the prior.

#### 9.1.6 Things to check first

- **Licences.** The public set is copyleft (GPL-3.0 / AGPL-3.0; flipt does not assert one). Use the repositories for research, but **do not redistribute the repositories or images**: publish each task as a patch plus a setup script that pulls the original image. Any file we publish that is derived from a repository's code goes in a separate folder under that repository's licence. The counterfactual patches touch the *dependencies* (PyYAML MIT, Jinja2 BSD-3, python-dateutil Apache-2.0/BSD), which keeps those simple.
- **Language.** The call-observing verifier is Python-only today. Start with the three Python repositories; Go and JavaScript need a language-specific way to observe calls.
- **Disk and architecture.** Images are 0.75–6.5 GB compressed and x86-only. The three Python images total about 2.6 GB.
- **Effort.** About 1–2 hours per task done properly. Pilot: 2 repositories × 5 tasks. Paper: 20–30 tasks.
- **Agent.** Real repositories are large. The minimal agent may need more turns, or a standard scaffold (Terminus-2 through Harbor, mini-swe-agent) with shell access; log every command so "did it read the docs" can still be answered.
- **Where Python docs really live.** Installed Python packages ship readable source and docstrings, not release notes. So the realistic channels differ from Study 1: the installed source and docstring, `dist-info` metadata, the project's own changelog or pin comment. Decide the channel set before building tasks.
- **Budget.** A real-repository episode uses several times more calls than a Study 1 episode. Pilot on free tiers with one or two models; frontier models need credits.

#### 9.1.7 Conditions and metrics

Reuse Study 1's conditions where they apply: closed-book (the prior), docs in the prompt (ceiling), agent with repository access and no hint, the "check the documentation" hint, and code execution (natural here, since the image can run the project). Report right calls, prior-locked calls, whether the agent opened the channel, and the repository's test pass rate, with intervals that resample behaviour changes.

#### 9.1.8 Pilot checklist

- [ ] Pull the images for one openlibrary and one ansible base commit; confirm the repository tests run.
- [ ] For each, list five dependency functions the project calls; run the closed-book prior check on two free models; keep the five strongest priors.
- [ ] Build one task end to end (patch, docs channel, task text, hidden test, call grader); validate the reference ladder.
- [ ] Build the remaining nine; run the free models; compare with Study 1.

## 10. Related work

| Work | Measures | PriorLock adds |
|---|---|---|
| [GitChameleon 2.0](https://arxiv.org/abs/2507.12367) | version-conditioned code completion with executable tests | the agent is not told what changed; it has to find out |
| [VersiCode](https://arxiv.org/abs/2406.07411) | version-specific completion and migration | agentic conditions and a reward, not only a score |
| [LibEvoBench](https://arxiv.org/abs/2606.25402) | version-obliviousness on real libraries; docs help, stating the version does not | whether the agent *fetches* the docs itself, and where it looks |
| [CodeUpdateArena](https://arxiv.org/abs/2407.06249) | whether a model can use a synthetic API update it is given | the update is not given: it sits in the repo |
| [When LLMs Lag Behind](https://arxiv.org/abs/2604.09515) | 270 real API updates as context-memory conflicts | silent same-signature changes, and the fetching step |
| [SWE-Chain](https://arxiv.org/abs/2605.14415), [RoadmapBench](https://arxiv.org/abs/2605.15846) | agents performing release-level upgrades from given release notes | nobody tells the agent there is anything to upgrade for |
| [Tool-Memory Conflict](https://arxiv.org/abs/2601.09760) | tool outputs contradicting parametric knowledge | a verifiable, attack-resistant reward for following the environment |
| [Knowledge conflicts](https://arxiv.org/abs/2305.13300) (Xie et al.) | when LLMs follow context that contradicts memory | a coding-agent instance, graded on the calls the code made |
| [Embers of Autoregression](https://arxiv.org/abs/2309.13638) | models default to high-probability answers on low-probability variants | the mechanism the memorized rung is built around |
| [Terminal-Bench](https://arxiv.org/abs/2601.11868) | agents on hard terminal tasks (Harbor) | probes ride along on its tasks without re-authoring |

The core comparison (open-book versus self-retrieval) is a familiar ablation applied to documentation; what is new is the call-observing verifier, the channel-isolated realistic repositories, the anti-gaming machinery and the packaging as an environment. Notes on each paper: [`priorlock/papers/`](priorlock/papers/).

## 11. Reproduce

```bash
git clone https://github.com/phoenixlibbi/PriorLock-RL-env && cd PriorLock-RL-env
pip install -e ".[dev]"
PYTHONHASHSEED=0 pytest -q                       # 62 tests; Docker tests run when Docker is available
priorlock bench --report results/bench_v2/*.jsonl # regenerate the v2 tables from the logged runs
priorlock repro                                   # offline determinism fingerprint
```

Tasks regenerate byte-identically from their seeds. More: [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) · design notes: [`priorlock/docs/`](priorlock/docs/) · contributing a behaviour change: [`CONTRIBUTING.md`](CONTRIBUTING.md).

<details>
<summary>Repository layout</summary>

```
src/priorlock/
  bench.py            model benchmark: conditions, agent loop, sandboxed grading, clustered intervals
  repo_v2.py          bench v2: realistic repos, documentation channels, hints, RUN sandbox, report
  probes/             the reward ladder, 13 original and 23 extended coding behaviour changes
  standalone.py       self-contained task generation and grading
  variation.py        per-seed data with answers recomputed from the library
  templates.py        generators for every task file, including the isolated grader
  cheats.py           12-class cheat battery and soundness receipt
  inject.py, gates.py wrap / unwrap Harbor tasks; the 12 integrity gates
  leakprobe.py        runtime isolation proof
  env.py              verifiers RL environment
  cartridges/         domain cartridges for wrapping
results/
  bench_v2/           v2 runs (JSONL with every reply), logs, REPORT.md
  bench/              v1 pilot runs
  receipts/           cheat-battery and isolation receipts
examples/             starter recipes (checked in CI)
priorlock/docs/       design notes · priorlock/papers/  literature notes
```
</details>

## Citation

```bibtex
@software{tariq2026priorlock,
  author = {Tariq, Muhammad Labeeb},
  title  = {PriorLock: Do Coding Agents Read the Documentation, or Code from Memory?},
  year   = {2026},
  url    = {https://github.com/phoenixlibbi/PriorLock-RL-env}
}
```

## Author

**Muhammad Labeeb Tariq** · [labeebjutt80@gmail.com](mailto:labeebjutt80@gmail.com) · [@phoenixlibbi](https://github.com/phoenixlibbi)

## License

MIT
