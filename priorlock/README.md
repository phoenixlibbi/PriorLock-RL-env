# PriorLock

An RL environment (Harbor task format) that rewards coding agents for grounding their code in the
INSTALLED environment instead of their parametric memory ("priors"). Built as the trial-build
submission.

## The idea in one paragraph (the kitchen story)

An AI model is a chef who memorized every famous cookbook. We invite it into OUR kitchen, where a
note on the fridge (the installed library's CHANGELOG and docs) says: "this oven runs in
milliseconds, not seconds; retries are OFF by default here." A chef who cooks from memory produces a
dish that LOOKS perfect - it runs, no crash, every test it can see passes - but it is silently wrong.
Only the hidden scoring tests (which check this kitchen's true behavior) tell the difference. The
reward therefore pays for exactly one skill: READ THE NOTE BEFORE YOU COOK. Research shows frontier
models fail this ~half the time even when told the version explicitly (GitChameleon 2.0: 48-51%).

## Folder map

    priorlock/
    |- README.md                    <- you are here
    |- docs/
    |  |- 00-THE-GAP.md             <- the capability gap, evidence, why nobody covered it
    |  |- 01-ARCHITECTURE.md        <- full technical design (library, tasks, verifier, generator)
    |  |- 02-BUILD-SPEC.md          <- step-by-step implementation playbook (feed this to an AI agent)
    |- papers/                      <- reference receipts for every cited paper (+ PDF links)

## Status

Planning complete. Next step: execute docs/02-BUILD-SPEC.md phase by phase.

## Ground rules

- Difficulty comes from non-discriminating visible feedback, never from spec ambiguity.
- Every soundness claim needs a receipt: a trace, a number with an interval, or a command that
  regenerates it.
- Stage-0 offline gates pass before any paid rollout.
- Pure ASCII in shipped files. One-command repro. No prior-client material anywhere.
