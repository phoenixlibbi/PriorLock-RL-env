"""Standalone task generation and grading — ``priorlock run``.

Generates a self-contained PriorLock task directory that any model can solve
without Harbor, Docker, or any external infrastructure.  The output is a plain
directory with an instruction file, synthetic library, input data, and smoke
tests.  A hidden ``.priorlock/`` directory contains the grader and reference
solutions.

Workflow::

    # 1. Generate a task
    priorlock run --output ./my-task --domain devtools --count 3

    # 2. Hand instruction.md to a model; it writes probe_solution.py

    # 3. Grade the solution
    priorlock run --grade ./my-task

    # Quick-check with reference solutions:
    priorlock run --grade ./my-task --reference gold       # expect 1.0
    priorlock run --grade ./my-task --reference familiar   # expect 0.40
"""
from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import templates as T
from .cartridges import (
    SOURCE_CHANGELOG, SOURCE_API_DOC, SOURCE_CODE, SOURCES,
    get as get_cartridge,
)
from .inject import pick_library_name, SOLUTION_NAME, INPUT_REL, OUTPUT_REL
from .probes.base import Probe


# ═════════════════════════════════════════════════════════════════════════════
#  Result type
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class StandaloneResult:
    path: Path
    lib: str
    probes: list[Probe]
    information_sources: tuple[str, ...]
    created: list[str] = field(default_factory=list)


# ═════════════════════════════════════════════════════════════════════════════
#  Task generation
# ═════════════════════════════════════════════════════════════════════════════

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate(
    output_dir: str | Path,
    *,
    count: int = 3,
    domains: list[str] | None = None,
    probe_ids: list[str] | None = None,
    level: int = 1,
    seed: str = "",
    difficulty_range: tuple[float, float] | None = None,
    min_discrimination: float = 0.0,
) -> StandaloneResult:
    """Generate a self-contained PriorLock task.

    The output directory is ready to hand to any model.  After the model
    writes ``probe_solution.py``, call :func:`grade` to score it.

    Args:
        output_dir: where to write the task.
        count: number of probes to inject.
        domains: restrict probes to these cartridge domains.
        probe_ids: pin specific probe IDs (overrides auto-selection).
        level: maximum probe difficulty level.
        seed: deterministic seed for probe selection.
        difficulty_range: ``(lo, hi)`` a-priori difficulty bounds.
        min_discrimination: IRT discrimination floor.
    """
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    task_id = seed or f"standalone-{secrets.token_hex(4)}"

    # ── probe selection ─────────────────────────────────────────────────────
    if probe_ids:
        from .probes import BY_ID, all_probes_by_id
        merged = {**BY_ID, **all_probes_by_id(domains)}
        unknown = [p for p in probe_ids if p not in merged]
        if unknown:
            raise KeyError(f"unknown probe id(s): {', '.join(unknown)}")
        probes = [merged[p] for p in probe_ids]
    elif domains:
        from .cartridges import select_probes_cross
        probes = select_probes_cross(
            task_id=task_id, domains=domains, count=count, level=level,
            difficulty_range=difficulty_range,
            min_discrimination=min_discrimination,
        )
    else:
        from .probes import select_probes
        probes = select_probes(
            task_id, text="", count=count,
            difficulty_range=difficulty_range,
            min_discrimination=min_discrimination,
        )

    if not probes:
        raise RuntimeError("no probes selected")

    lib = pick_library_name(task_id)

    # ── resolve information sources ─────────────────────────────────────────
    probe_domains = {p.domain for p in probes}
    info_sources: set[str] = set()
    for d in probe_domains:
        try:
            cart = get_cartridge(d)
            info_sources.update(cart.information_sources)
        except KeyError:
            info_sources = set(SOURCES)
            break
    if not info_sources:
        info_sources = set(SOURCES)

    has_changelog = SOURCE_CHANGELOG in info_sources
    has_api_doc = SOURCE_API_DOC in info_sources

    # Source-code-only → visible defaults; otherwise opaque
    hide_defaults = has_changelog or has_api_doc
    agent_lib_source = T.render_library(lib, probes, hide_defaults=hide_defaults)
    pristine_lib_source = T.render_library(lib, probes, hide_defaults=False)

    created: list[str] = []

    def _track(path: Path, content: str) -> None:
        _write(path, content)
        created.append(str(path.relative_to(output)))

    # ── agent-visible surface ───────────────────────────────────────────────
    _track(output / lib / "__init__.py", agent_lib_source)

    if has_changelog:
        _track(output / "docs" / f"{lib}-CHANGELOG.md",
               T.render_changelog(lib, probes))
    if has_api_doc:
        _track(output / "docs" / f"{lib}-api.md",
               T.render_api(lib, probes))

    _track(output / INPUT_REL, T.render_input(probes))
    _track(output / "tests" / "test_probe_visible.py",
           T.render_visible_test(lib, probes, SOLUTION_NAME, INPUT_REL))

    # Context priming
    context_files = T.render_context_files(lib, probes)
    for rel_path, content in context_files.items():
        _track(output / rel_path, content)

    # ── instruction ─────────────────────────────────────────────────────────
    info_tuple = tuple(sorted(info_sources))
    block = T.render_instruction_block(
        lib, probes, SOLUTION_NAME, INPUT_REL, OUTPUT_REL,
        information_sources=info_tuple,
    )
    _track(output / "instruction.md",
           f"# Task\n\nComplete the data-processing checks below.\n{block}")

    # ── hidden grading infrastructure (.priorlock/) ─────────────────────────
    plx = output / ".priorlock"
    lib_sha = hashlib.sha256(agent_lib_source.encode()).hexdigest()

    _write(plx / "_plx_lib" / lib / "__init__.py", pristine_lib_source)
    _write(plx / "probe_grade.py",
           T.render_grader(lib, probes, lib_sha, SOLUTION_NAME, INPUT_REL))
    _write(plx / "probe_input.json", T.render_input(probes))

    for variant in ("gold", "familiar"):
        _write(plx / "_plx_reference" / f"{variant}.py",
               T.render_reference_solution(lib, probes, variant))
    _write(plx / "_plx_reference" / "stub.py", T.STUB_SOLUTION)
    _write(plx / "_plx_reference" / "bypass.py",
           T.render_bypass_solution(probes))

    # Manifest (JSON, not TOML — simpler for standalone tasks)
    manifest = {
        "task_id": task_id,
        "lib": lib,
        "lib_sha256": lib_sha,
        "probes": [
            {"id": p.id, "family": p.family, "category": p.category,
             "domain": p.domain, "fn": p.fn, "output_key": p.output_key}
            for p in probes
        ],
        "information_sources": sorted(info_sources),
        "solution": SOLUTION_NAME,
        "input": INPUT_REL,
        "hide_defaults": hide_defaults,
    }
    _write(plx / "manifest.json", json.dumps(manifest, indent=2) + "\n")

    return StandaloneResult(
        path=output, lib=lib, probes=probes,
        information_sources=info_tuple, created=created,
    )


# ═════════════════════════════════════════════════════════════════════════════
#  Grading
# ═════════════════════════════════════════════════════════════════════════════

def grade(
    task_dir: str | Path,
    *,
    solution: str | Path | None = None,
    reference: str | None = None,
) -> dict:
    """Grade a solution in a standalone task directory.

    Args:
        task_dir: path to the standalone task (must contain ``.priorlock/``).
        solution: path to a custom ``probe_solution.py``.  Defaults to
            ``<task_dir>/probe_solution.py``.
        reference: if set, grade a built-in reference solution instead
            (``"gold"``, ``"familiar"``, ``"stub"``, ``"bypass"``).

    Returns:
        The grader's JSON report.
    """
    task = Path(task_dir).resolve()
    plx = task / ".priorlock"
    if not plx.is_dir():
        raise FileNotFoundError(
            f"not a standalone PriorLock task (no .priorlock/): {task}"
        )

    manifest = json.loads((plx / "manifest.json").read_text())
    sol_name = manifest["solution"]

    # Resolve which solution to grade
    if reference:
        ref_path = plx / "_plx_reference" / f"{reference}.py"
        if not ref_path.is_file():
            raise FileNotFoundError(f"reference solution not found: {ref_path}")
        # Copy reference into position for the grader
        shutil.copy2(ref_path, task / sol_name)
    elif solution:
        sol = Path(solution).resolve()
        if not sol.is_file():
            raise FileNotFoundError(f"solution not found: {sol}")
        shutil.copy2(sol, task / sol_name)
    else:
        if not (task / sol_name).is_file():
            raise FileNotFoundError(
                f"solution not found: {task / sol_name}\n"
                f"  write {sol_name} or use --reference gold|familiar"
            )

    # Run the grader as a subprocess (cleanest isolation)
    result = subprocess.run(
        [sys.executable, str(plx / "probe_grade.py"),
         "--submission", str(task),
         "--tests-dir", str(plx)],
        capture_output=True, text=True, timeout=60,
    )

    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(
            f"grader failed (exit {result.returncode}):\n{result.stderr[:1000]}"
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"grader produced invalid JSON:\n{result.stdout[:500]}\n"
            f"stderr:\n{result.stderr[:500]}"
        )


def is_standalone(task_dir: str | Path) -> bool:
    """True if *task_dir* is a standalone PriorLock task."""
    return (Path(task_dir) / ".priorlock" / "manifest.json").is_file()
