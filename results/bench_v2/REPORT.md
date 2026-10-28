# Bench v2 report

Generated 2026-10-29 03:49 from 54 runs: gemini-3.5-flash-lite (45 runs), openai/gpt-oss-120b (9 runs).
Regenerate with `priorlock bench --report results/bench_v2/*.jsonl`.

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
| openai/gpt-oss-120b | repo_open | 4 | **100%** [100%, 100%] | 0% (0/12) | 100% (4/4) | 0% (0/4) | 0% (0/4) | 0% (0/4) | 1.0 |
| openai/gpt-oss-120b | repo_docs | 1 | **33%** [0%, 100%] | 67% (2/3) | 0% (0/1) | 0% (0/1) | 0% (0/1) | 0% (0/1) | 1.0 |
| openai/gpt-oss-120b | repo_docs_h2 | 3 | **11%** [0%, 33%] | 44% (4/9) | 0% (0/3) | 0% (0/3) | 0% (0/3) | 0% (0/3) | 1.0 |
| openai/gpt-oss-120b | repo_run | 1 | **0%** [0%, 0%] | 0% (0/3) | 0% (0/1) | 0% (0/1) | 0% (0/1) | 0% (0/1) | 16.0 |

### Right calls by condition (the hint ladder)

| Model | repo_open | repo_source | repo_docs | repo_docs_h1 | repo_docs_h2 | repo_docs_h3 | repo_run |
|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | 100% | 78% | 29% | 28% | 38% | 61% | 72% |
| openai/gpt-oss-120b | 100% | – | 33% | – | 11% | – | 0% |

### Where the change was written (all models pooled)

| Channel | Open book: right call | Compiled, no hint: right call | Compiled, no hint: found the change |
|---|---|---|---|
| changelog | 100% (9/9) | 22% (2/9) | 0% (0/3) |
| migration | 100% (9/9) | 0% (0/6) | 0% (0/2) |
| api_reference | 100% (6/6) | 33% (1/3) | 100% (1/1) |
| stub | 100% (6/6) | 100% (3/3) | 100% (1/1) |
| readme | 100% (3/3) | 33% (1/3) | 0% (0/1) |

### By probe family (compiled library, all hints and RUN pooled)

| Family | Right call | Prior-locked |
|---|---|---|
| default_flip | 37% (22/59) | 49% (29/59) |
| value_remap | 24% (8/33) | 42% (14/33) |
| result_shape | 79% (15/19) | 0% (0/19) |

### Did finding the change help? (compiled library, all hints and RUN pooled)

| Model | Right call when it found the change | Right call when it did not |
|---|---|---|
| gemini-3.5-flash-lite | 87% (26/30) | 26% (17/66) |
| openai/gpt-oss-120b | – | 13% (2/15) |
