"""The grader runs solutions out of process and pays only for consistent, documented calls.

Each test is an exploit found in review, kept as a regression test.
"""
import json

import pytest

from priorlock.cheats import CHEATS
from priorlock.standalone import generate, grade


@pytest.fixture(scope="module")
def task(tmp_path_factory):
    path = tmp_path_factory.mktemp("iso") / "task"
    generate(path, probe_ids=["null_key_policy", "merge_precedence_remap",
                              "tie_inclusive_topk"], seed="iso")
    return path


def _grade(task, tmp_path, source):
    sol = tmp_path / "probe_solution.py"
    sol.write_text(source)
    return grade(task, solution=sol)


def _answers_present(task):
    plx = task / ".priorlock"
    return (plx / "probe_grade.py").is_file() and (plx / "_plx_reference" / "gold.py").is_file()


@pytest.mark.parametrize("cheat", ["grader_introspect", "stdout_forgery",
                                   "reference_exec", "oracle_steal"])
def test_exploits_found_in_review_score_zero(task, tmp_path, cheat):
    report = _grade(task, tmp_path, CHEATS[cheat]["source"])
    assert report["gap_score"] == 0.0
    assert _answers_present(task)            # hidden during the run, restored after


def test_spraying_argument_values_scores_zero(task, tmp_path):
    lib = json.loads((task / ".priorlock" / "manifest.json").read_text())["lib"]
    gold = (task / ".priorlock" / "_plx_reference" / "gold.py").read_text()
    # the gold solution, plus an extra call with the memorized argument
    spray = gold.replace("def run(data_path, out_path):",
                         f"def run(data_path, out_path):\n    {lib}.bucket([], 'k')", 1)
    report = _grade(task, tmp_path, spray)
    verdicts = {p["id"]: p["verdict"] for p in report["probes"]}
    assert verdicts["null_key_policy"] == "inconsistent_calls"
    assert verdicts["merge_precedence_remap"] == "override"


def _gold_outputs(task):
    import subprocess, sys
    plx = task / ".priorlock"
    code = ("import json, sys; sys.path[:0] = [%r, %r]; import gold; "
            "print(json.dumps(gold.run(%r, %r)))"
            % (str(plx / "_plx_lib"), str(plx / "_plx_reference"),
               str(task / "data" / "probe_input.json"), str(task / "gold.out")))
    return json.loads(subprocess.run([sys.executable, "-c", code], capture_output=True,
                                     text=True, check=True).stdout)


def test_correct_output_by_another_route_earns_the_baseline(task, tmp_path):
    familiar = (task / ".priorlock" / "_plx_reference" / "familiar.py").read_text()
    gold_out = _gold_outputs(task)
    # make the familiar calls, then write the right answers by hand
    source = familiar.replace(
        '    with open(out_path, "w") as f:',
        f'    out.update({gold_out!r})\n    with open(out_path, "w") as f:', 1)
    report = _grade(task, tmp_path, source)
    by_id = {p["id"]: p for p in report["probes"]}
    for pid in ("null_key_policy", "merge_precedence_remap"):
        assert by_id[pid]["score"] == 0.4
        assert by_id[pid]["verdict"] == "correct_output_other_call"


def test_seeds_give_different_answers(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    ids = ["null_key_policy", "dedupe_keep_policy", "tie_inclusive_topk"]
    generate(a, probe_ids=ids, seed="one")
    generate(b, probe_ids=ids, seed="two")
    assert _gold_outputs(a) != _gold_outputs(b)
    # a gold solution leaked from one task does not solve the other
    leaked = (a / ".priorlock" / "_plx_reference" / "gold.py").read_text()
    sol = tmp_path / "leaked.py"
    sol.write_text(leaked)
    assert grade(b, solution=sol)["gap_score"] < 1.0
