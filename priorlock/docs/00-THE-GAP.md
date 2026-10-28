# 00 - The Gap: Stale Priors Beat Installed Reality

> **PriorLock:** A Domain-Agnostic Reinforcement Learning Environment for
> Measuring and Training Prior Override in Autonomous Agents.
>
> Created by **Muhammad Labeeb Tariq** · labeebjutt80@gmail.com ·
> [github.com/phoenixlibbi](https://github.com/phoenixlibbi)

## 1. Plain-language version

Models learn coding from a frozen snapshot of the internet. When they write code, they write from
MEMORY - the way a library "usually" works. In real projects the installed version is often
different: older, newer, forked, or internally patched. The truthful description of how THIS
environment behaves sits right there in the container (CHANGELOG.md, API reference, the library's
own source). Models skip it, because in 99.9% of their training life memory was correct and nothing
ever punished them for not checking.

The killer detail: when the memorized code runs, NOTHING FAILS. No crash, no red test. Every signal
the agent can see says "you are right." So even a diligent agent gets no trigger to go read. The
result is the worst kind of bug: compiles, passes visible tests, looks finished, wrong in
production.

Two different papers in the kitchen - do not confuse them:

- instruction.md = the ORDER TICKET. "Bake a chocolate cake for table 5." Agents always read this.
- The library docs/changelog/source inside the container = the NOTE ON THE FRIDGE. "This oven runs
  hot; the sugar jar contains salt." Agents almost never read this unless something crashes.

PriorLock makes reading the note the entire game.

## 2. Evidence (the receipts)

| Source | Finding | Relevance |
|---|---|---|
| GitChameleon 2.0 (arXiv:2507.12367) | 328 version-conditioned Python problems with executable tests; enterprise models score 48-51% EVEN WITH THE VERSION STATED IN THE PROMPT; RAG helps but does not close it | Proof the gap survives being told the note exists |
| VersiCode (arXiv:2406.07411) | Version-specific completion/migration; >50-point drops vs standard benchmarks for GPT-4o-class models | Independent confirmation, different dataset/metric (CDC@1) |
| Terminal-Bench (arXiv:2601.11868, ICLR 2026) | Largest command-failure class = calling executables not installed / not in PATH (24.1% of 3,800 sampled failures); failure taxonomy: premature termination, no/weak verification | Agentic corroboration: models act on priors, not on the environment; they under-verify |
| Embers of Autoregression (arXiv:2309.13638, PNAS) | Models degrade sharply on low-probability variants of familiar tasks (cipher decoding: 51% -> 13% when output is low-probability) | The mechanism: next-token pressure makes the familiar answer the default |
| LibEvoBench (arXiv:2606.25402) | Temporal knowledge stratification in code models (June 2026) | The gap is current, not historical |

## 3. Who cares and why

Users: every production codebase has pinned dependencies, internal forks, legacy versions, and
patched vendored libs. "The agent silently used the v2 API against our v1 pin" is a recurring,
expensive failure users of Claude Code / Codex / Cursor hit today. Silent-wrong is costlier than
crash-wrong because it ships.

Researchers / labs: this is the knowledge-cutoff problem in agentic form. Labs actively want models
that override parametric memory when in-context evidence contradicts it (in-context override,
environment grounding). RL is the tool of choice for instilling behaviors that generalize OOD
(SFT memorizes; RL generalizes - see counterfactual-training results). But you can only train what
you can score, and published work on this gap (GitChameleon, VersiCode, LibEvoBench,
CodeUpdateArena) offers benchmarks rather than a reward for an agent loop.

## 4. How existing benchmarks relate

- Terminal-Bench 2.0/2.1 pins versions in Docker ONLY for reproducibility - same exam room for every
  student. No task makes noticing the version the measured skill, and its visible checks are
  discriminating, so agents iterate until green (the feedback crank). TB 2.1's fixes (28/89 tasks)
  repaired env drift, tight budgets, and instruction-test mismatches - exam-paper repairs, not a new
  subject. Top score is now ~88.8% (July 2026): near saturation.
- SWE-bench: same story - pinned for reproducibility, visible tests discriminating.
- GitChameleon / VersiCode / LibEvoBench: quizzes, not environments. Single-function completion, no
  terminal, no repo, no reward machinery, cannot be trained against. Built from REAL libraries'
  documented breaking changes, so they sit in training corpora and dissolve as models memorize more.
- TMax / Terminal-Lego (Prime Intellect, 365k+ envs): scale collections of ordinary terminal tasks;
  none makes prior-override the reward target.
- tau-bench / tau2: user-interaction tool use; different axis.
- CodeUpdateArena (arXiv:2407.06249): synthetic API updates, testing whether a model can use an
  update it was given (knowledge editing). Closest prior work on synthetic changes; PriorLock's
  difference is the agentic question of whether the agent looks, and a reward for a training loop.
- Knowledge-conflict studies, e.g. "Adaptive Chameleon or Stubborn Sloth" (arXiv:2305.13300):
  when do LLMs follow context that contradicts memory. PriorLock is a coding-agent instance of
  that question.

## 5. Why it is uncommon

1. The people who proved the weakness built evals, not gyms - no reward, no agent loop.
2. Real-library material contaminates by construction; a sound version needs a never-published
   synthetic library, which is more work than scraping changelogs.
3. Building it soundly is sneaky-hard: deviations must be SILENT (a crash is feedback and hands the
   agent the answer), visible tests must all pass for the wrong solution (or the agent grinds
   feedback until green), and only hidden tests may discriminate. That is exactly the
   non-discriminating-feedback design good RL environments need.

## 6. The named failure mode we provoke

"The model confidently applies the familiar API shape, which is wrong here." Predicted trace:
complete, clean, plausible solution submitted with high confidence; visible suite green; hidden
suite fails the trap checks. Confident-wrong, not step-exhaustion. (This is the predicted trace;
the pilot in the README is the evidence collected so far.)
