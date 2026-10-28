"""priorlock bench: task plan, agent sandbox, grading and the results table.

A scripted model stands in for a real endpoint, so these run offline.
"""
from pathlib import Path

import pytest

from priorlock import bench as B
from priorlock.probes import BY_ID


class Scripted(B.Model):
    """Replies from a list; records every prompt it was shown."""

    def __init__(self, replies):
        super().__init__(name="scripted", base_url="http://unused")
        self.replies = list(replies)
        self.seen = []

    def chat(self, messages):
        self.seen.append(messages[-1]["content"])
        return self.replies.pop(0)


def _ref(task: Path, name: str) -> str:
    code = (task / ".priorlock" / "_plx_reference" / f"{name}.py").read_text()
    return f"```python\n{code}```"


@pytest.fixture(scope="module")
def tasks(tmp_path_factory):
    return B.build_tasks(tmp_path_factory.mktemp("bench"), repeats=1)


def test_groups_cover_every_archetype_once():
    flat = [pid for g in B.probe_groups() for pid in g]
    assert sorted(flat) == sorted(BY_ID)
    assert len(flat) == len(set(flat))


def test_agent_cannot_reach_the_grader_or_leave_the_repo(tasks):
    task = tasks[0]
    for rel in (".priorlock/probe_grade.py", ".priorlock", "../" * 6 + "etc/hosts"):
        obs, path = B._act(task, f"READ {rel}")
        assert path is None and "no such file" in obs
    listing, _ = B._act(task, "LIST .")
    assert ".priorlock" not in listing


@pytest.mark.parametrize("ref,score,verdict", [
    ("gold", 1.0, "override"),
    ("familiar", 0.4, "prior_locked"),
    ("stub", 0.0, "bypassed"),
])
def test_closed_book_answers_grade_on_the_ladder(tasks, ref, score, verdict):
    task = tasks[0]
    model = Scripted([_ref(task, ref)])
    out = B.solve(model, task, "closed")
    report = B.grade_code(task, out["code"], sandbox="none", image="")
    assert report["gap_score"] == score
    assert {p["verdict"] for p in report["probes"]} == {verdict}


def test_closed_hides_docs_and_open_shows_them(tasks):
    task = tasks[0]
    changelog = next((task / "docs").glob("*CHANGELOG.md")).read_text()
    closed, opened = Scripted(["```python\npass\n```"]), Scripted(["```python\npass\n```"])
    B.solve(closed, task, "closed")
    B.solve(opened, task, "open")
    assert changelog not in closed.seen[0]
    assert changelog in opened.seen[0]
    assert "probe_input.json" in closed.seen[0]


def test_agentic_loop_records_what_was_read(tasks, tmp_path):
    task = tasks[0]
    doc = next((task / "docs").glob("*CHANGELOG.md")).name
    model = Scripted(["LIST docs", f"READ docs/{doc}", _ref(task, "gold")])
    out_file = tmp_path / "r.jsonl"
    B.run_bench(model, [task], ["agentic"], out_file, sandbox="none", image="",
                log=lambda *_: None)
    rec = B.load_records([out_file])[0]
    assert rec["read_docs"] and rec["turns"] == 3 and rec["gap_score"] == 1.0


def test_no_code_block_scores_zero_and_run_is_resumable(tasks, tmp_path):
    task = tasks[0]
    out_file = tmp_path / "r.jsonl"
    B.run_bench(Scripted(["I would rather not."]), [task], ["closed"], out_file,
                sandbox="none", image="", log=lambda *_: None)
    B.run_bench(Scripted([]), [task], ["closed"], out_file,       # nothing to redo
                sandbox="none", image="", log=lambda *_: None)
    recs = B.load_records([out_file])
    assert len(recs) == 1
    assert set(recs[0]["verdicts"].values()) == {"no_answer"}


def test_intervals_resample_archetypes_not_probes():
    def rec(verdicts):
        return {"model": "m", "condition": "closed", "gap_score": 0.4,
                "read_docs": False, "verdicts": verdicts}
    one = [rec({"a": "prior_locked", "b": "override"})]
    many = one * 20                         # same two archetypes, repeated
    s1 = B.summarise(one)["m"]["closed"]["prior_locked"]
    s20 = B.summarise(many)["m"]["closed"]["prior_locked"]
    assert s1["rate"] == s20["rate"] == 0.5
    assert s20["ci95"] == s1["ci95"]         # repeats add no independent evidence
    assert s20["ci95"][0] <= 0.5 <= s20["ci95"][1]
    assert "| m | closed | 40 |" in B.report_markdown(many)


@pytest.mark.skipif(not B.docker_available(), reason="Docker not available")
def test_docker_sandbox_grades_the_ladder(tasks):
    task = tasks[0]
    for ref, score in (("gold", 1.0), ("familiar", 0.4), ("stub", 0.0)):
        code = (task / ".priorlock" / "_plx_reference" / f"{ref}.py").read_text()
        report = B.grade_code(task, code, sandbox="docker", image="python:3.11-bookworm")
        assert report["gap_score"] == score
