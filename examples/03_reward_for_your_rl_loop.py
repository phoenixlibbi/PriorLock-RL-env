"""Recipe 3: use the grader as the reward in your own RL loop.

`reward(task, code)` returns the PriorLock score for one rollout: 1.0 for the
documented call with the right output, 0.40 for the memorized one, 0.0 for
skipping the library, spraying values, or anything else. Each seed is a fresh
task with its own data, so a policy cannot memorize answers across tasks.

    python examples/03_reward_for_your_rl_loop.py
"""
import tempfile
from pathlib import Path

from priorlock.standalone import generate, grade


def make_task(seed: str) -> Path:
    task = Path(tempfile.mkdtemp()) / "task"
    generate(task, probe_ids=["merge_precedence_remap", "null_key_policy",
                              "tie_inclusive_topk"], seed=seed)
    return task


def reward(task: Path, code: str) -> float:
    solution = task.parent / "rollout.py"
    solution.write_text(code)
    return grade(task, solution=solution)["gap_score"]


task = make_task("episode-0")
refs = task / ".priorlock" / "_plx_reference"
for name in ("gold", "familiar", "bypass"):
    print(f"{name:<9} reward = {reward(task, (refs / f'{name}.py').read_text()):.2f}")
# gold 1.00 · familiar 0.40 · bypass 0.00
