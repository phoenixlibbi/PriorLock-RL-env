# Bench v2 report

Generated 2026-10-29 06:32 from 125 runs: gemini-3.1-flash-lite (48 runs), gemini-3.5-flash-lite (45 runs), gemma-4-31b-it (10 runs), openai/gpt-oss-120b (22 runs).
Regenerate with `priorlock bench --report results/bench_v2/*.jsonl`.

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
| gemma-4-31b-it | repo_open | 3 | **100%** [100%, 100%] | 0% (0/9) | 100% (3/3) | 0% (0/3) | 0% (0/3) | 0% (0/3) | 1.0 |
| gemma-4-31b-it | repo_docs | 3 | **11%** [0%, 33%] | 44% (4/9) | 0% (0/3) | 100% (3/3) | 67% (2/3) | 0% (0/3) | 6.3 |
| gemma-4-31b-it | repo_docs_h2 | 2 | **100%** [100%, 100%] | 0% (0/6) | 100% (2/2) | 100% (2/2) | 0% (0/2) | 0% (0/2) | 9.5 |
| gemma-4-31b-it | repo_run | 2 | **67%** [33%, 100%] | 33% (2/6) | 0% (0/2) | 100% (2/2) | 0% (0/2) | 100% (2/2) | 8.0 |
| openai/gpt-oss-120b | repo_open | 9 | **100%** [100%, 100%] | 0% (0/27) | 100% (9/9) | 0% (0/9) | 0% (0/9) | 0% (0/9) | 1.0 |
| openai/gpt-oss-120b | repo_docs | 8 | **8%** [0%, 21%] | 58% (14/24) | 0% (0/8) | 0% (0/8) | 0% (0/8) | 0% (0/8) | 1.0 |
| openai/gpt-oss-120b | repo_docs_h2 | 5 | **7%** [0%, 20%] | 40% (6/15) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 1.0 |

### Right calls by condition (the hint ladder)

| Model | repo_open | repo_source | repo_docs | repo_docs_h1 | repo_docs_h2 | repo_docs_h3 | repo_run |
|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | 89% | – | 22% | – | 22% | – | 36% |
| gemini-3.5-flash-lite | 100% | 78% | 29% | 28% | 38% | 61% | 72% |
| gemma-4-31b-it | 100% | – | 11% | – | 100% | – | 67% |
| openai/gpt-oss-120b | 100% | – | 8% | – | 7% | – | – |

### Where the change was written (all models pooled)

| Channel | Open book: right call | Compiled, no hint: right call | Compiled, no hint: found the change |
|---|---|---|---|
| changelog | 100% (24/24) | 17% (4/24) | 0% (0/8) |
| migration | 96% (23/24) | 0% (0/24) | 0% (0/8) |
| api_reference | 100% (18/18) | 6% (1/18) | 17% (1/6) |
| stub | 100% (15/15) | 75% (9/12) | 75% (3/4) |
| readme | 75% (9/12) | 25% (3/12) | 25% (1/4) |

### By probe family (compiled library, all hints and RUN pooled)

| Family | Right call | Prior-locked |
|---|---|---|
| default_flip | 28% (42/152) | 45% (69/152) |
| value_remap | 21% (16/77) | 44% (34/77) |
| result_shape | 80% (28/35) | 0% (0/35) |

### Did finding the change help? (compiled library, all hints and RUN pooled)

| Model | Right call when it found the change | Right call when it did not |
|---|---|---|
| gemini-3.1-flash-lite | 79% (19/24) | 12% (10/84) |
| gemini-3.5-flash-lite | 87% (26/30) | 26% (17/66) |
| gemma-4-31b-it | 100% (6/6) | 33% (5/15) |
| openai/gpt-oss-120b | – | 8% (3/39) |
