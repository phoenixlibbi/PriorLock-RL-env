# PriorLock

**PriorLock: A Domain-Agnostic Reinforcement Learning Environment for Measuring
and Training Prior Override in Autonomous Agents**

An RL environment (Harbor task format) that rewards agents for grounding actions
in the INSTALLED environment instead of parametric memory ("priors"). Domain-agnostic:
wrap any Harbor task; probes inject the measurement without re-authoring.

| | |
|---|---|
| **Creator** | [Muhammad Labeeb Tariq](https://github.com/phoenixlibbi) |
| **Email** | [labeebjutt80@gmail.com](mailto:labeebjutt80@gmail.com) |
| **GitHub** | [github.com/phoenixlibbi](https://github.com/phoenixlibbi) |
| **Repository** | [PriorLock-RL-env](https://github.com/phoenixlibbi/PriorLock-RL-env) |

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
    |  |- 04-PROBE-SPEC.md          <- probe architecture (domain-agnostic wrap path)
    |  |- 05-LIFECYCLE.md           <- build → validate → wrap → gate → doctor
    |  |- 06-EVALUATORS.md          <- deterministic success-criteria reports
    |- papers/                      <- reference receipts for every cited paper (+ PDF links)

## Author

**Muhammad Labeeb Tariq** · [labeebjutt80@gmail.com](mailto:labeebjutt80@gmail.com) · [@phoenixlibbi](https://github.com/phoenixlibbi)

## Ground rules

- Difficulty comes from non-discriminating visible feedback, never from spec ambiguity.
- Every soundness claim needs a receipt: a trace, a number with an interval, or a command that
  regenerates it.
- Stage-0 offline gates pass before any paid rollout.
- Pure ASCII in shipped files. One-command repro.
