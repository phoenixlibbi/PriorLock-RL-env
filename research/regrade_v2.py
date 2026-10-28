"""Regrade every stored bench v2 run from its saved code.

    python research/regrade_v2.py results/bench_v2/*.jsonl

Checks that grading is reproducible (the score must match the stored one) and
applies the crash relabelling to runs recorded before it existed: probes left
uncalled because the solution crashed are labelled `crashed`, not `bypassed`.
Scores never change. Prints a summary; rewrites each file in place.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from priorlock import bench as B  # noqa: E402

TASKS = ROOT / "results" / "bench_v2" / "tasks_v2"


def main(files: list[str]) -> None:
    total = same = relabelled = 0
    for f in files:
        rows = [json.loads(line) for line in open(f)]
        for r in rows:
            if not r.get("code"):
                continue
            rep = B.grade_code(TASKS / r["task"], r["code"], "docker", "python:3.11-bookworm")
            total += 1
            same += abs(rep.get("gap_score", 0.0) - r["gap_score"]) < 1e-9
            flags = rep.get("flags", [])
            new = B.relabel_crash(r["verdicts"], flags)
            relabelled += sum(new[k] != r["verdicts"][k] for k in new)
            r["verdicts"], r["flags"] = new, flags
        Path(f).write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"regraded {total} runs: {same} reproduced the stored score exactly; "
          f"{relabelled} probe verdicts relabelled bypassed/absent -> crashed")


if __name__ == "__main__":
    main(sys.argv[1:])
