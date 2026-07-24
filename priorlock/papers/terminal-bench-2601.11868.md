# Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces

- arXiv: 2601.11868 (ICLR 2026) | PDF: https://arxiv.org/pdf/2601.11868 | HTML: arxiv.org/html/2601.11868v1
- Laude Institute / Stanford / community. Repo: github.com/laude-institute/terminal-bench
- Harbor framework (our packaging target): github.com/laude-institute/harbor

## Key facts (from full text, read 2026-07-25)

- TB 2.0: 89 tasks, ~3 reviewer-hours of human auditing each; frontier models < 65% at release,
  small models ~15%. TB 2.1 later fixed issues in 28/89 tasks (external-dependency drift, too-tight
  resource budgets, instruction-test mismatches). Leaderboard July 2026: top ~88.8% (near saturation).
- Failure taxonomy (derived from MAST): Execution, Coherence, Verification. Subclasses: disobey task
  specification, step repetition, unaware of termination conditions, context loss, premature
  termination, no/irrelevant verification, reasoning-action mismatch, weak verification.
- Command-level error analysis (3,800 sampled failures): the largest class is calling executables
  that are NOT INSTALLED or not in PATH - 24.1% of all command failures; command error rates per
  model range 9.2%-26.7%.
- Human-medium tasks that models find hard (54.5% of that bucket) need creative/adversarial
  reasoning rather than pattern-following.
- Stated limitations: internet access -> possible oracle lookup + external drift; training-set
  contamination mitigated only by a canary string; no private split; verifying task correctness is
  "extremely difficult" - authors urge future env builders to invest in manual verification and
  anti-cheat design.

## What PriorLock cites / uses

- The 24.1% not-installed/PATH stat = agentic evidence that models act from priors, not environment.
- Verification failure classes = the under-verification habit our hidden split punishes.
- TB pins versions for REPRODUCIBILITY, never as the measured skill; its visible checks are
  discriminating (feedback crank) - the two structural reasons TB does not cover our gap.
- Harbor task format = our packaging substrate (builder-side layout, verifier-at-end pattern).
