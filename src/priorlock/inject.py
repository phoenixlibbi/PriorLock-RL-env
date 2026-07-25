"""The injection engine — `priorlock wrap`.

Takes an ordinary Harbor / Terminal-Bench task directory and returns a task that
measures prior-override capability *in addition to* whatever it already
measured. The task author writes nothing, learns nothing new, and can keep
editing their task normally afterwards.

What gets written
-----------------
Agent-visible (inside ``environment/``)::

    <repo>/<lib>/__init__.py               synthetic library, honest docstrings
    <repo>/docs/<lib>-CHANGELOG.md         authoritative behavioural changes
    <repo>/docs/<lib>-api.md               current signatures
    <repo>/data/probe_input.json           check inputs
    <repo>/tests/test_probe_visible.py     shape-only smoke tests
    instruction.md                         "Part 2" appended

Verifier-only (inside ``tests/``, never mounted into the agent session)::

    tests/_plx_lib/<lib>/__init__.py       pristine copy — this is what grades
    tests/probe_grade.py                   generated grader
    tests/probe_input.json                 grader's own copy of the inputs
    tests/_plx_reference/{gold,familiar,stub,bypass}.py
    tests/test.sh                          composite verifier (original preserved)

Task root::

    priorlock.toml                         manifest: probes, weights, hashes

Idempotence
-----------
Wrapping is reversible (``priorlock unwrap``) and re-runnable: a second wrap
detects the existing manifest and refuses unless ``force=True``, in which case
it unwraps first. Nothing the engine writes collides with a normal task layout.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from dataclasses import dataclass, field
from pathlib import Path

from . import templates as T
from .probes import ALL_PROBES, BY_ID, infer_categories, select_probes
from .probes.base import Probe

MANIFEST = "priorlock.toml"
SOLUTION_NAME = "probe_solution.py"
INPUT_REL = "data/probe_input.json"
OUTPUT_REL = "probe_output.json"
PRISTINE_DIR = "_plx_lib"
REFERENCE_DIR = "_plx_reference"
MARKER_BEGIN = "<!-- priorlock:begin -->"
MARKER_END = "<!-- priorlock:end -->"


# ═════════════════════════════════════════════════════════════════════════════
#  Task discovery
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class TaskLayout:
    """Where the interesting bits of a Harbor task live.

    Deliberately tolerant: Terminal-Bench tasks in the wild vary in whether the
    agent workdir is ``environment/repo``, ``environment/app``, or the
    environment root, and in whether the verifier entrypoint is ``run-tests.sh``
    or ``test.sh``.
    """
    root: Path
    task_toml: Path | None
    instruction: Path | None
    environment: Path
    repo: Path
    tests: Path
    verifier_entry: Path | None
    workdir: str

    @property
    def task_id(self) -> str:
        return self.root.name


_WORKDIR_RE = re.compile(r'^\s*workdir\s*=\s*["\']([^"\']+)["\']', re.M)
_NAME_RE = re.compile(r'^\s*name\s*=\s*["\']([^"\']+)["\']', re.M)
_DESC_RE = re.compile(r'^\s*description\s*=\s*["\']([^"\']*)["\']', re.M)
_KEYWORDS_RE = re.compile(r'^\s*(?:keywords|tags)\s*=\s*\[([^\]]*)\]', re.M)

_INSTRUCTION_NAMES = ("instruction.md", "instructions.md", "task.md", "TASK.md",
                      "PROBLEM.md", "README.md")
_VERIFIER_NAMES = ("test.sh", "run-tests.sh", "run_tests.sh", "verify.sh")


def detect_layout(task_dir: str | Path) -> TaskLayout:
    root = Path(task_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"not a directory: {root}")

    task_toml = root / "task.toml"
    task_toml = task_toml if task_toml.is_file() else None

    instruction = next(
        (root / n for n in _INSTRUCTION_NAMES if (root / n).is_file()), None
    )

    environment = root / "environment"
    if not environment.is_dir():
        environment = root

    workdir = "/app"
    if task_toml:
        m = _WORKDIR_RE.search(task_toml.read_text())
        if m:
            workdir = m.group(1)

    # the agent-visible repo: prefer the directory the workdir basename names
    repo = environment / Path(workdir).name
    if not repo.is_dir():
        for candidate in ("repo", "app", "workspace", "src"):
            if (environment / candidate).is_dir():
                repo = environment / candidate
                break
        else:
            repo = environment

    tests = root / "tests"
    verifier_entry = next(
        (tests / n for n in _VERIFIER_NAMES if (tests / n).is_file()), None
    )

    return TaskLayout(
        root=root, task_toml=task_toml, instruction=instruction,
        environment=environment, repo=repo, tests=tests,
        verifier_entry=verifier_entry, workdir=workdir,
    )


def describe_task(layout: TaskLayout) -> str:
    """Gather the text used for probe category inference."""
    chunks: list[str] = [layout.task_id]
    if layout.task_toml:
        raw = layout.task_toml.read_text()
        for rx in (_NAME_RE, _DESC_RE):
            m = rx.search(raw)
            if m:
                chunks.append(m.group(1))
        m = _KEYWORDS_RE.search(raw)
        if m:
            chunks.append(m.group(1).replace('"', " ").replace("'", " "))
    if layout.instruction and layout.instruction.is_file():
        chunks.append(layout.instruction.read_text()[:4000])
    return "\n".join(chunks)


def pick_library_name(task_id: str) -> str:
    idx = int(hashlib.sha256(("lib:" + task_id).encode()).hexdigest()[:8], 16)
    return T.LIB_NAMES[idx % len(T.LIB_NAMES)]


# ═════════════════════════════════════════════════════════════════════════════
#  Wrap
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class WrapResult:
    layout: TaskLayout
    lib: str
    probes: list[Probe]
    created: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    manifest_path: Path | None = None


def _write(path: Path, content: str, created: list[str], root: Path,
           executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    created.append(str(path.relative_to(root)))


def is_wrapped(task_dir: str | Path) -> bool:
    return (Path(task_dir) / MANIFEST).is_file()


def wrap_task(
    task_dir: str | Path,
    *,
    count: int = 3,
    probe_ids: list[str] | None = None,
    w_task: float = 0.5,
    w_gap: float = 0.5,
    force: bool = False,
    seed_suffix: str = "",
) -> WrapResult:
    layout = detect_layout(task_dir)
    root = layout.root

    if is_wrapped(root):
        if not force:
            raise RuntimeError(
                f"{root.name} is already wrapped. Re-run with force=True "
                f"(CLI: --force) to regenerate, or `priorlock unwrap` first."
            )
        unwrap_task(root)

    # ── choose probes ────────────────────────────────────────────────────────
    if probe_ids:
        unknown = [p for p in probe_ids if p not in BY_ID]
        if unknown:
            raise KeyError(f"unknown probe id(s): {', '.join(unknown)}")
        probes = [BY_ID[p] for p in probe_ids]
    else:
        probes = select_probes(
            layout.task_id + seed_suffix,
            text=describe_task(layout),
            count=count,
        )
    if not probes:
        raise RuntimeError("no probes selected")

    lib = pick_library_name(layout.task_id + seed_suffix)
    created: list[str] = []
    modified: list[str] = []

    # ── agent-visible surface ────────────────────────────────────────────────
    lib_source = T.render_library(lib, probes)
    _write(layout.repo / lib / "__init__.py", lib_source, created, root)
    _write(layout.repo / "docs" / f"{lib}-CHANGELOG.md",
           T.render_changelog(lib, probes), created, root)
    _write(layout.repo / "docs" / f"{lib}-api.md",
           T.render_api(lib, probes), created, root)
    _write(layout.repo / INPUT_REL, T.render_input(probes), created, root)
    _write(layout.repo / "tests" / "test_probe_visible.py",
           T.render_visible_test(lib, probes, SOLUTION_NAME, INPUT_REL), created, root)

    # ── instruction addendum ─────────────────────────────────────────────────
    block = (
        MARKER_BEGIN
        + T.render_instruction_block(lib, probes, SOLUTION_NAME, INPUT_REL, OUTPUT_REL)
        + "\n"
        + MARKER_END
        + "\n"
    )
    instruction = layout.instruction or (root / "instruction.md")
    existing = instruction.read_text() if instruction.is_file() else "# Task\n"
    instruction.write_text(existing.rstrip() + "\n" + block, encoding="utf-8")
    modified.append(str(instruction.relative_to(root)))

    # ── verifier-only surface ────────────────────────────────────────────────
    lib_sha = hashlib.sha256(lib_source.encode()).hexdigest()

    _write(layout.tests / PRISTINE_DIR / lib / "__init__.py", lib_source, created, root)
    _write(layout.tests / "probe_grade.py",
           T.render_grader(lib, probes, lib_sha, SOLUTION_NAME, INPUT_REL),
           created, root)
    _write(layout.tests / "probe_input.json", T.render_input(probes), created, root)

    for variant in ("gold", "familiar"):
        _write(layout.tests / REFERENCE_DIR / f"{variant}.py",
               T.render_reference_solution(lib, probes, variant), created, root)
    _write(layout.tests / REFERENCE_DIR / "stub.py", T.STUB_SOLUTION, created, root)
    _write(layout.tests / REFERENCE_DIR / "bypass.py",
           T.render_bypass_solution(probes), created, root)

    # ── composite verifier entrypoint ────────────────────────────────────────
    original_name = ""
    original_sha = ""
    if layout.verifier_entry and layout.verifier_entry.is_file():
        original_name = "task_verify.sh"
        original_sha = hashlib.sha256(layout.verifier_entry.read_bytes()).hexdigest()
        target = layout.tests / original_name
        shutil.copy2(layout.verifier_entry, target)
        target.chmod(target.stat().st_mode | stat.S_IEXEC)
        created.append(str(target.relative_to(root)))
        entry = layout.verifier_entry
    else:
        entry = layout.tests / "test.sh"
    _write(entry, T.render_composite_test_sh(original_name, layout.workdir, w_task, w_gap),
           created if entry not in (layout.verifier_entry,) else modified, root,
           executable=True)
    if layout.verifier_entry and str(entry.relative_to(root)) not in modified:
        modified.append(str(entry.relative_to(root)))

    # ── manifest ─────────────────────────────────────────────────────────────
    manifest = render_manifest(layout, lib, probes, lib_sha, w_task, w_gap,
                               original_name, original_sha)
    (root / MANIFEST).write_text(manifest, encoding="utf-8")
    created.append(MANIFEST)

    return WrapResult(layout=layout, lib=lib, probes=probes, created=created,
                      modified=modified, manifest_path=root / MANIFEST)


# ═════════════════════════════════════════════════════════════════════════════
#  Manifest
# ═════════════════════════════════════════════════════════════════════════════

def render_manifest(layout: TaskLayout, lib: str, probes: list[Probe],
                    lib_sha: str, w_task: float, w_gap: float,
                    original_verifier: str = "", original_sha: str = "") -> str:
    from . import __version__
    lines = [
        "# Generated by `priorlock wrap`. Edit weights freely; regenerate with",
        "# `priorlock wrap <task> --force` after changing the probe set.",
        "",
        "[priorlock]",
        f'version = "{__version__}"',
        f'task_id = "{layout.task_id}"',
        f'library = "{lib}"',
        f'library_sha256 = "{lib_sha}"',
        f'solution = "{SOLUTION_NAME}"',
        f'input = "{INPUT_REL}"',
        f'workdir = "{layout.workdir}"',
        f'original_verifier = "{original_verifier}"',
        f'original_verifier_sha256 = "{original_sha}"',
        "familiar_baseline = 0.40",
        "",
        "[weights]",
        f"task = {float(w_task)}",
        f"gap = {float(w_gap)}",
        "",
        "[categories]",
    ]
    for cat, score in infer_categories(describe_task(layout)):
        lines.append(f"{cat} = {score}")
    lines.append("")
    for p in probes:
        lines += [
            f'[[probe]]',
            f'id = "{p.id}"',
            f'family = "{p.family}"',
            f'category = "{p.category}"',
            f'fn = "{p.fn}"',
            f'output_key = "{p.output_key}"',
            f'weight = {p.weight}',
            f'summary = {json.dumps(p.summary)}',
            f'familiar_behaviour = {json.dumps(p.familiar_behaviour)}',
            f'installed_behaviour = {json.dumps(p.installed_behaviour)}',
            "",
        ]
    return "\n".join(lines)


def read_manifest(task_dir: str | Path) -> dict:
    """Minimal TOML reader — avoids a hard tomli dependency on Python < 3.11."""
    path = Path(task_dir) / MANIFEST
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found — task is not wrapped")
    try:
        import tomllib  # type: ignore[import-not-found]
        with path.open("rb") as f:
            return tomllib.load(f)
    except ModuleNotFoundError:
        pass

    data: dict = {}
    section: dict = data
    probes: list[dict] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[[") and line.endswith("]]"):
            section = {}
            probes.append(section)
            continue
        if line.startswith("[") and line.endswith("]"):
            section = data.setdefault(line[1:-1], {})
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        try:
            section[key] = json.loads(value)
        except json.JSONDecodeError:
            section[key] = value.strip('"\'')
    if probes:
        data["probe"] = probes
    return data


# ═════════════════════════════════════════════════════════════════════════════
#  Unwrap
# ═════════════════════════════════════════════════════════════════════════════

def unwrap_task(task_dir: str | Path) -> list[str]:
    """Remove everything `wrap_task` added. Leaves the original task intact."""
    layout = detect_layout(task_dir)
    root = layout.root
    if not is_wrapped(root):
        return []
    meta = read_manifest(root).get("priorlock", {})
    lib = meta.get("library", "")
    removed: list[str] = []

    def rm(path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            removed.append(str(path.relative_to(root)))
        elif path.is_file():
            path.unlink()
            removed.append(str(path.relative_to(root)))

    if lib:
        rm(layout.repo / lib)
        rm(layout.repo / "docs" / f"{lib}-CHANGELOG.md")
        rm(layout.repo / "docs" / f"{lib}-api.md")
    rm(layout.repo / INPUT_REL)
    rm(layout.repo / "tests" / "test_probe_visible.py")
    rm(layout.repo / SOLUTION_NAME)
    rm(layout.tests / PRISTINE_DIR)
    rm(layout.tests / REFERENCE_DIR)
    rm(layout.tests / "probe_grade.py")
    rm(layout.tests / "probe_input.json")
    rm(layout.tests / "_plx_observed_output.json")

    # restore the original verifier entrypoint
    saved = layout.tests / "task_verify.sh"
    if saved.is_file():
        entry = layout.verifier_entry or (layout.tests / "test.sh")
        shutil.move(str(saved), str(entry))
        entry.chmod(entry.stat().st_mode | stat.S_IEXEC)
        removed.append(str(saved.relative_to(root)))
    elif layout.verifier_entry and layout.verifier_entry.is_file():
        text = layout.verifier_entry.read_text()
        if "PriorLock composite verifier" in text:
            rm(layout.verifier_entry)

    # strip the instruction addendum
    if layout.instruction and layout.instruction.is_file():
        text = layout.instruction.read_text()
        if MARKER_BEGIN in text:
            head, _, rest = text.partition(MARKER_BEGIN)
            _, _, tail = rest.partition(MARKER_END)
            layout.instruction.write_text(head.rstrip() + "\n" + tail.lstrip("\n"),
                                          encoding="utf-8")
            removed.append(str(layout.instruction.relative_to(root)) + " (block)")

    rm(root / MANIFEST)
    return removed
