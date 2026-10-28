# Bench v2 report

Generated 2026-10-29 04:12 from 84 runs: gemini-3.1-flash-lite (17 runs), gemini-3.5-flash-lite (45 runs), openai/gpt-oss-120b (22 runs).
Regenerate with `priorlock bench --report results/bench_v2/*.jsonl`.

### Every model and condition

| Model | Condition | Tasks | Right call [95% CI] | Prior-locked | Found the change | Looked at the library | Used GREP | Used RUN | Mean turns |
|---|---|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | repo_open | 5 | **93%** [80%, 100%] | 7% (1/15) | 100% (5/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 1.0 |
| gemini-3.1-flash-lite | repo_docs | 4 | **33%** [8%, 58%] | 33% (4/12) | 25% (1/4) | 75% (3/4) | 25% (1/4) | 0% (0/4) | 6.8 |
| gemini-3.1-flash-lite | repo_docs_h2 | 4 | **33%** [8%, 58%] | 17% (2/12) | 25% (1/4) | 100% (4/4) | 75% (3/4) | 0% (0/4) | 10.5 |
| gemini-3.1-flash-lite | repo_run | 4 | **42%** [17%, 67%] | 33% (4/12) | 25% (1/4) | 100% (4/4) | 0% (0/4) | 75% (3/4) | 8.0 |
| gemini-3.5-flash-lite | repo_open | 7 | **100%** [100%, 100%] | 0% (0/21) | 100% (7/7) | 0% (0/7) | 0% (0/7) | 0% (0/7) | 1.0 |
| gemini-3.5-flash-lite | repo_source | 6 | **78%** [56%, 94%] | 6% (1/18) | 0% (0/6) | 100% (6/6) | 0% (0/6) | 0% (0/6) | 4.3 |
| gemini-3.5-flash-lite | repo_docs | 7 | **29%** [10%, 48%] | 48% (10/21) | 29% (2/7) | 86% (6/7) | 14% (1/7) | 0% (0/7) | 5.1 |
| gemini-3.5-flash-lite | repo_docs_h1 | 6 | **28%** [11%, 50%] | 44% (8/18) | 17% (1/6) | 100% (6/6) | 17% (1/6) | 0% (0/6) | 5.0 |
| gemini-3.5-flash-lite | repo_docs_h2 | 7 | **38%** [19%, 62%] | 52% (11/21) | 43% (3/7) | 100% (7/7) | 43% (3/7) | 0% (0/7) | 9.3 |
| gemini-3.5-flash-lite | repo_docs_h3 | 6 | **61%** [39%, 83%] | 17% (3/18) | 50% (3/6) | 100% (6/6) | 50% (3/6) | 0% (0/6) | 9.3 |
| gemini-3.5-flash-lite | repo_run | 6 | **72%** [50%, 89%] | 28% (5/18) | 17% (1/6) | 83% (5/6) | 0% (0/6) | 100% (6/6) | 8.7 |
| openai/gpt-oss-120b | repo_open | 9 | **100%** [100%, 100%] | 0% (0/27) | 100% (9/9) | 0% (0/9) | 0% (0/9) | 0% (0/9) | 1.0 |
| openai/gpt-oss-120b | repo_docs | 8 | **8%** [0%, 21%] | 58% (14/24) | 0% (0/8) | 0% (0/8) | 0% (0/8) | 0% (0/8) | 1.0 |
| openai/gpt-oss-120b | repo_docs_h2 | 5 | **7%** [0%, 20%] | 40% (6/15) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 1.0 |

### Right calls by condition (the hint ladder)

| Model | repo_open | repo_source | repo_docs | repo_docs_h1 | repo_docs_h2 | repo_docs_h3 | repo_run |
|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | 93% | – | 33% | – | 33% | – | 42% |
| gemini-3.5-flash-lite | 100% | 78% | 29% | 28% | 38% | 61% | 72% |
| openai/gpt-oss-120b | 100% | – | 8% | – | 7% | – | – |

### Where the change was written (all models pooled)

| Channel | Open book: right call | Compiled, no hint: right call | Compiled, no hint: found the change |
|---|---|---|---|
| changelog | 100% (15/15) | 20% (3/15) | 0% (0/5) |
| migration | 93% (14/15) | 0% (0/15) | 0% (0/5) |
| api_reference | 100% (12/12) | 8% (1/12) | 25% (1/4) |
| stub | 100% (12/12) | 67% (6/9) | 67% (2/3) |
| readme | 100% (9/9) | 33% (2/6) | 0% (0/2) |

### By probe family (compiled library, all hints and RUN pooled)

| Family | Right call | Prior-locked |
|---|---|---|
| default_flip | 32% (31/96) | 47% (45/96) |
| value_remap | 16% (8/49) | 45% (22/49) |
| result_shape | 77% (20/26) | 0% (0/26) |

### Did finding the change help? (compiled library, all hints and RUN pooled)

| Model | Right call when it found the change | Right call when it did not |
|---|---|---|
| gemini-3.1-flash-lite | 100% (9/9) | 15% (4/27) |
| gemini-3.5-flash-lite | 87% (26/30) | 26% (17/66) |
| openai/gpt-oss-120b | – | 8% (3/39) |
