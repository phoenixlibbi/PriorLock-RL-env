# Automated Evaluators

> **PriorLock:** A Domain-Agnostic Reinforcement Learning Environment for
> Measuring and Training Prior Override in Autonomous Agents.
>
> Created by **Muhammad Labeeb Tariq** · labeebjutt80@gmail.com ·
> [github.com/phoenixlibbi](https://github.com/phoenixlibbi)

## The build-standard requirement

RL environment checklists ask for **automated evaluators**: scripts or verifier
functions that assess whether an agent’s output meets success criteria, so the
reward is **deterministic and objective**.

PriorLock meets that requirement with two independent evaluators. Neither trusts
the agent’s self-report.

| Evaluator | Success criteria | Checker | Artifact |
|---|---|---|---|
| **Host** | Required outputs, schemas, metrics, protocol rules from the Harbor task | `tests/task_verify.sh` (original verifier, byte-preserved) | `task_score` |
| **Probe** | Installed library semantics (prior override) | `tests/probe_grade.py` (call-arg interception) | `gap_score` + per-probe verdicts |

Composite reward:

```
reward = (task_score × w_task + gap_score × w_gap) / (w_task + w_gap)
```

Emitted as `reward.json` and `verifier/priorlock_summary.json` after a Harbor run.

---

## Why the probe evaluator is objective

1. **Verifier-owned library.** Grading imports a pristine copy from
   `tests/_plx_lib/`. Editing the agent-visible library cannot change the score
   (Gate G8).
2. **Call arguments observed, not self-reported.** Each probe function is
   wrapped; explicitly supplied arguments are recovered with
   `inspect.Signature.bind` (defaults excluded). There is no forgeable trace file.
3. **Bypass scores zero.** Reimplementing the function without calling the
   library yields `bypassed` / 0.0, not the familiar 0.40 rung (Gate G7).
4. **Visible tests are shape-only.** `test_probe_visible.py` cannot leak gold
   values (Gate G5).

See also [`04-PROBE-SPEC.md`](04-PROBE-SPEC.md) § Anti-reward-hacking.

---

## Offline API and CLI

```bash
# Structured success-criteria report (checklist-facing)
priorlock evaluate tasks/my-task --reference gold
priorlock evaluate tasks/my-task -s path/to/probe_solution.py --json -o evaluator_report.json
priorlock evaluate tasks/my-task --reference familiar --require-override   # exits 1

# Human-oriented twin (same grader)
priorlock verify tasks/my-task --reference gold
```

Python:

```python
from priorlock.evaluators import (
    evaluate_submission,
    meets_success_criteria,
    write_report,
)

report = evaluate_submission("tasks/my-task", reference="gold")
assert report.deterministic
assert report.gap_score == 1.0
assert meets_success_criteria(report, require_all_override=True)
write_report(report, "evaluator_report.json")
```

### Report shape (excerpt)

```json
{
  "task_id": "pipeline-drift-calibration-hard",
  "library": "pycore",
  "deterministic": true,
  "gap_score": 1.0,
  "flags": [],
  "success_criteria": [
    "merge_precedence_remap: \"keep\" is an alias for keep_right — the patch value wins"
  ],
  "checks": [
    {
      "id": "merge_precedence_remap",
      "criterion": "…",
      "passed": true,
      "verdict": "override",
      "score": 1.0,
      "evidence": {
        "supplied": [{"on_conflict": "keep_left"}],
        "gold_call": true,
        "output_matches": "gold"
      }
    }
  ],
  "host_evaluator": {
    "entrypoint": "tests/task_verify.sh",
    "produces": "task_score",
    "runs_offline": false
  },
  "probe_evaluator": {
    "entrypoint": "tests/probe_grade.py",
    "produces": "gap_score",
    "runs_offline": true,
    "method": "call_argument_interception"
  }
}
```

---

## Offline vs Harbor

| What | Command | Needs Docker? |
|---|---|---|
| Probe evaluator only | `priorlock evaluate` / `verify` | No |
| Stage-0 gates (G1–G12) | `priorlock stage0` | No |
| Cheat battery | `priorlock cheats --suite` | No |
| Host `task_score` + full composite | `harbor run -p <task> -a …` | Yes |

`priorlock evaluate` documents the host evaluator contract in the report but
cannot execute Harbor’s verifier without a container. That separation is
intentional: host criteria stay owned by the task author.

---

## Install note

Use the repo CLI (`python3 -m priorlock.cli` or `pip install -e .`) so commands
match this tree. A stale global install may omit newer subcommands such as
`evaluate` and `run`.

```bash
cd PriorLock-RL-env
python3 -m pip install -e . --break-system-packages   # or your venv
priorlock evaluate --help
```
