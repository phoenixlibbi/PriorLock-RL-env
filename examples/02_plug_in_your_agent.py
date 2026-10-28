"""Recipe 2: measure your own agent, or any function that writes code.

`my_agent` receives the task's instruction and its repository path and returns
the source of `probe_solution.py`. Replace it with your agent: a model call, a
tool loop, a whole framework. The task's own hidden grader scores the result.

    python examples/02_plug_in_your_agent.py
"""
import tempfile
from pathlib import Path

from priorlock.bench import build_tasks
from priorlock.standalone import grade


def my_agent(instruction: str, repo: Path) -> str:
    # Placeholder: behaves like an agent coding from memory, so it should
    # land on the 0.40 rung. Swap in your own agent here.
    return (repo / ".priorlock" / "_plx_reference" / "familiar.py").read_text()


tasks = build_tasks(Path(tempfile.mkdtemp()), repeats=1)   # all 13 archetypes, 4 tasks
for task in tasks:
    code = my_agent((task / "instruction.md").read_text(), task)
    solution = task.parent / f"{task.name}-solution.py"
    solution.write_text(code)
    report = grade(task, solution=solution)
    verdicts = {p["id"]: p["verdict"] for p in report["probes"]}
    print(f"{task.name}  gap={report['gap_score']:.2f}  {verdicts}")
