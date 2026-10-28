"""bench v2: realistic repos, one documentation channel, hints and the RUN tool.

Scripted models stand in for real endpoints; the RUN test needs Docker.
"""
import shutil
from pathlib import Path

import pytest

from priorlock import bench as B
from priorlock import repo_v2 as R
from priorlock.probes.catalog_v2 import EXTENDED_PROBES
from priorlock.standalone import generate, grade

IDS = ["fill_method_remap", "csv_header", "dedupe_keep_policy"]


class Scripted(B.Model):
    def __init__(self, replies):
        super().__init__(name="scripted", base_url="http://unused")
        self.replies = list(replies)
        self.seen = []

    def chat(self, messages):
        self.seen.append(messages[-1]["content"])
        return self.replies.pop(0)


def _ref(task: Path, name: str) -> str:
    return (task / ".priorlock" / "_plx_reference" / f"{name}.py").read_text()


@pytest.fixture(scope="module")
def tasks(tmp_path_factory):
    root = tmp_path_factory.mktemp("v2")
    out = {}
    for ch in R.CHANNELS:
        path = root / ch
        generate(path, probes=[R.V2_BY_ID[i] for i in IDS], seed="test-v2")
        assert B._ladder_ok(path)
        R.make_repo(path, ch, seed="test-v2")
        out[ch] = path
    return out


def test_extended_probes_discriminate():
    assert len(EXTENDED_PROBES) == 23
    assert len(R.V2_PROBES) == 36 == len(R.V2_BY_ID)
    for p in EXTENDED_PROBES:
        assert p.gold_output != p.familiar_output, p.id


def test_groups_cover_every_archetype_once_per_repeat():
    for r in range(2):
        flat = [pid for g in R.v2_groups(r) for pid in g]
        assert sorted(flat) == sorted(R.V2_BY_ID)


def test_ladder_check_leaves_no_answer_in_the_task(tasks):
    for path in tasks.values():
        assert not (path / "probe_solution.py").exists()
        assert not (path / "probe_output.json").exists()


@pytest.mark.parametrize("channel", R.CHANNELS)
def test_change_is_written_only_in_its_channel(tasks, channel):
    assert R.check_channel_isolation(tasks[channel]) == []
    assert R._meta(tasks[channel])["info_files"]


def test_compiled_view_hides_the_library_source(tasks):
    task = tasks["changelog"]
    lib = R._manifest(task)["lib"]
    compiled = R.RepoView(task, compiled=True)
    assert compiled.read(f"{lib}/{R.NATIVE_V2}")[0].endswith("binary file, cannot display")
    assert "_compat" not in compiled.read(f"{lib}/__init__.py")[0]
    assert "_compat" in R.RepoView(task, compiled=False).read(f"{lib}/__init__.py")[0]
    assert not any(r.endswith("probe_solution.py") for r in compiled.files)
    assert "instruction.md" not in compiled.files


def test_grep_finds_the_change_only_in_the_channel(tasks):
    task = tasks["migration"]
    out, hits = R.RepoView(task, compiled=True).grep('"carry"')
    assert hits == {f"docs/third_party/{R._manifest(task)['lib']}/MIGRATION-2.0.md"}, out


def test_parse_action():
    assert R.parse_action("I'll look first.\nREAD docs/x.md", False) == ("READ", "docs/x.md")
    assert R.parse_action("`LIST .`", False) == ("LIST", ".")
    assert R.parse_action("GREP: default", False) == ("GREP", "default")
    assert R.parse_action("RUN\n```python\nprint(1)\n```", True) == ("RUN", "print(1)\n")
    assert R.parse_action("RUN\n```python\nprint(1)\n```", False) == ("FINAL", "print(1)\n")
    assert R.parse_action("```python\nx = 1\n```", True) == ("FINAL", "x = 1\n")
    assert R.parse_action("hmm", False) == ("NONE", "")
    assert R.parse_condition("repo_docs_h2") == ("repo_docs", 2, False)
    assert R.parse_condition("repo_run") == ("repo_docs", 0, True)


def test_reading_agent_scores_full_and_memory_agent_scores_baseline(tasks, tmp_path):
    task = tasks["api_reference"]
    info = R._meta(task)["info_files"][0]
    gold = Scripted([f"LIST .", f"READ {info}", f"```python\n{_ref(task, 'gold')}```"])
    out = R.solve_v2(gold, task, "repo_docs")
    assert out["info_seen"] and out["turns"] == 3
    (tmp_path / "gold.py").write_text(out["code"])
    assert grade(task, solution=tmp_path / "gold.py")["gap_score"] == 1.0

    memory = Scripted([f"```python\n{_ref(task, 'familiar')}```"])
    out = R.solve_v2(memory, task, "repo_docs")
    assert not out["info_seen"] and out["turns"] == 1
    (tmp_path / "fam.py").write_text(out["code"])
    assert abs(grade(task, solution=tmp_path / "fam.py")["gap_score"] - 0.4) < 1e-9
    assert not (task / "probe_solution.py").exists()


def test_hints_and_open_book(tasks):
    task = tasks["readme"]
    lib = R._manifest(task)["lib"]
    m = Scripted(["```python\npass\n```"])
    R.solve_v2(m, task, "repo_docs_h3")
    assert "upgraded from 1.4 to 2.0" in m.seen[0] and "documentation" in m.seen[0]
    assert "(v2)" not in m.seen[0] and "docs/" not in m.seen[0].split("The input file")[0]
    m = Scripted(["```python\npass\n```"])
    out = R.solve_v2(m, task, "repo_open")
    assert out["info_seen"] and "Upgrading to 2.0" in m.seen[0] and lib in m.seen[0]


def test_out_of_turns_asks_for_the_answer(tasks):
    m = Scripted(["LIST ."] * 3 + ["```python\npass\n```"])
    out = R.solve_v2(m, tasks["stub"], "repo_source", steps=3)
    assert out["code"] == "pass\n" and out["turns"] == 4


@pytest.mark.skipif(not B.docker_available(), reason="needs Docker")
def test_run_tool_executes_the_compiled_library_without_its_source(tasks):
    task = tasks["changelog"]
    lib = R._manifest(task)["lib"]
    out = R.run_snippet(task, f"import {lib}, inspect\nprint({lib}.csv_header if hasattr({lib}, "
                              f"'csv_header') else {lib}.read_csv('a,b\\n1,2'))\n"
                              f"try:\n    inspect.getsource({lib}.read_csv)\n    print('SOURCE')\n"
                              f"except (OSError, TypeError):\n    print('NO_SOURCE')\n")
    assert "[['a', 'b'], ['1', '2']]" in out and "NO_SOURCE" in out, out
    box = task / ".priorlock" / "v2_sandbox" / lib
    assert sorted(p.name for p in box.iterdir()) == ["__init__.py", R.NATIVE_V2]
    shutil.rmtree(task / ".priorlock" / "v2_sandbox")
