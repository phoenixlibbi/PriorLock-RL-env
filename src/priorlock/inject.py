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
import secrets
import os
import re
import shutil
import stat
from dataclasses import dataclass, field
from pathlib import Path

from . import templates as T
from .probes import ALL_PROBES, BY_ID, infer_categories, select_probes
from .probes import all_probes_by_id
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

    ``container_repo`` is the crucial one. A task's ``environment/`` layout does
    not have to mirror the container: a Dockerfile may ``COPY src/ /app/src/``
    and ``COPY task_file/ /app/task_file/`` with nothing mapping to ``/app``
    itself. Injected files have to be addressed by their **container** path, or
    the instruction tells the agent to read a file that is not where it says.
    """
    root: Path
    task_toml: Path | None
    instruction: Path | None
    environment: Path
    repo: Path
    tests: Path
    verifier_entry: Path | None
    workdir: str
    container_repo: str = ""
    copy_map: dict = field(default_factory=dict)

    @property
    def task_id(self) -> str:
        return self.root.name

    def container_path(self, rel: str) -> str:
        """Container-absolute path for a file placed at ``repo/rel``."""
        base = (self.container_repo or self.workdir).rstrip("/")
        return f"{base}/{rel.lstrip('/')}"


_WORKDIR_RE = re.compile(r'^\s*workdir\s*=\s*["\']([^"\']+)["\']', re.M)
_NAME_RE = re.compile(r'^\s*name\s*=\s*["\']([^"\']+)["\']', re.M)
_DESC_RE = re.compile(r'^\s*description\s*=\s*["\']([^"\']*)["\']', re.M)
_KEYWORDS_RE = re.compile(r'^\s*(?:keywords|tags)\s*=\s*\[([^\]]*)\]', re.M)

_INSTRUCTION_NAMES = ("instruction.md", "instructions.md", "task.md", "TASK.md",
                      "PROBLEM.md", "README.md")
_VERIFIER_NAMES = ("test.sh", "run-tests.sh", "run_tests.sh", "verify.sh")


_COPY_RE = re.compile(
    r'^\s*COPY\s+(?:--[\w=.-]+\s+)*(?P<src>[^\s]+)\s+(?P<dst>[^\s]+)\s*$',
    re.M | re.I,
)
_READONLY_RE = re.compile(r'chmod\s+-R\s+a-w\s+(?P<path>[^\s&|;]+)', re.I)
_DOCKER_WORKDIR_RE = re.compile(r'^\s*WORKDIR\s+(?P<path>\S+)\s*$', re.M | re.I)


def parse_dockerfile(dockerfile: Path) -> tuple[dict[str, str], set[str], str]:
    """Return ``(copy_map, readonly_container_paths, workdir)`` from a Dockerfile.

    ``copy_map`` maps an environment-relative directory to the container path it
    lands at, so injected files can be addressed correctly regardless of how the
    task chose to lay out ``environment/``.
    """
    copy_map: dict[str, str] = {}
    readonly: set[str] = set()
    workdir = ""
    if not dockerfile.is_file():
        return copy_map, readonly, workdir

    text = dockerfile.read_text()
    m = _DOCKER_WORKDIR_RE.search(text)
    if m:
        workdir = m.group("path").rstrip("/") or "/"

    for match in _COPY_RE.finditer(text):
        src = match.group("src").strip().strip("'\"")
        dst = match.group("dst").strip().strip("'\"")
        if src in (".", "./") or src.startswith("--"):
            src = ""
        src = src.rstrip("/").lstrip("./")
        dst = dst.rstrip("/") or "/"
        if not dst.startswith("/"):
            dst = f"{workdir or '/app'}/{dst}"
        copy_map[src] = dst

    for match in _READONLY_RE.finditer(text):
        readonly.add(match.group("path").rstrip("/"))

    return copy_map, readonly, workdir


def detect_layout(task_dir: str | Path, repo_dir: str | None = None) -> TaskLayout:
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

    dockerfile = next(iter(sorted(environment.rglob("Dockerfile"))), None)
    copy_map, readonly, docker_workdir = parse_dockerfile(dockerfile) if dockerfile else ({}, set(), "")
    if docker_workdir and not (task_toml and _WORKDIR_RE.search(task_toml.read_text())):
        workdir = docker_workdir
    workdir = workdir.rstrip("/") or "/"

    repo: Path | None = None
    container_repo = ""

    # 0. explicit override always wins
    if repo_dir:
        candidate = (root / repo_dir) if not Path(repo_dir).is_absolute() else Path(repo_dir)
        if not candidate.is_dir():
            raise FileNotFoundError(f"--repo-dir not found: {candidate}")
        repo = candidate.resolve()
        rel = str(repo.relative_to(environment)) if repo != environment else ""
        container_repo = copy_map.get(rel, f"{workdir}/{rel}".rstrip("/") if rel else workdir)

    # 1. a COPY that lands exactly on the workdir
    if repo is None:
        for src, dst in copy_map.items():
            if dst == workdir:
                candidate = environment / src if src else environment
                if candidate.is_dir():
                    repo, container_repo = candidate, dst
                    break

    # 2. a COPY that lands under the workdir and is NOT made read-only.
    #    Read-only trees (task_file, fixtures) can't host an injected library.
    if repo is None and copy_map:
        writable = [
            (src, dst) for src, dst in copy_map.items()
            if dst.startswith(workdir) and not any(
                dst == ro or dst.startswith(ro + "/") for ro in readonly
            )
            and (environment / src if src else environment).is_dir()
        ]
        if writable:
            writable.sort(key=lambda kv: (kv[1].count("/"), len(kv[1])))
            src, dst = writable[0]
            repo, container_repo = (environment / src if src else environment), dst

    # 3. conventional directory names
    if repo is None:
        named = environment / Path(workdir).name
        if named.is_dir():
            repo, container_repo = named, workdir
        else:
            for name in ("repo", "app", "workspace", "src"):
                if (environment / name).is_dir():
                    repo = environment / name
                    container_repo = copy_map.get(name, f"{workdir}/{name}")
                    break

    # 4. the environment root itself
    if repo is None:
        repo, container_repo = environment, workdir

    tests = root / "tests"
    verifier_entry = next(
        (tests / n for n in _VERIFIER_NAMES if (tests / n).is_file()), None
    )

    return TaskLayout(
        root=root, task_toml=task_toml, instruction=instruction,
        environment=environment, repo=repo, tests=tests,
        verifier_entry=verifier_entry, workdir=workdir,
        container_repo=container_repo or workdir, copy_map=copy_map,
    )


_ORACLE_NAMES = ("solve.sh", "solution.sh", "run.sh")


def _find_oracle(layout: TaskLayout) -> Path | None:
    """The task's oracle script, if it has one."""
    sol = layout.root / "solution"
    if not sol.is_dir():
        return None
    for name in _ORACLE_NAMES:
        p = sol / name
        if p.is_file():
            return p
    scripts = sorted(sol.glob("*.sh"))
    return scripts[0] if scripts else None


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
    domains: list[str] | None = None,
    level: int = 1,
    w_task: float = 0.5,
    w_gap: float = 0.5,
    force: bool = False,
    seed_suffix: str = "",
    repo_dir: str | None = None,
) -> WrapResult:
    """Inject probes into an existing Harbor task.

    Args:
        domains: restrict or expand probe selection to specific cartridge
            domains (e.g. ``["coding", "sql"]``). When set, uses the
            cross-cartridge selector for domain-interleaved selection.
        level: maximum probe difficulty level (L1–L4). Default 1 (atomic).
    """
    layout = detect_layout(task_dir, repo_dir=repo_dir)
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
        # Resolve from all cartridges, not just the coding catalog
        extended = all_probes_by_id(domains)
        # Fall back to original BY_ID for coding-only probes
        merged = {**BY_ID, **extended}
        unknown = [p for p in probe_ids if p not in merged]
        if unknown:
            raise KeyError(f"unknown probe id(s): {', '.join(unknown)}")
        probes = [merged[p] for p in probe_ids]
    elif domains:
        from .cartridges import select_probes_cross
        probes = select_probes_cross(
            task_id=layout.task_id + seed_suffix,
            domains=domains,
            count=count,
            level=level,
        )
    else:
        probes = select_probes(
            layout.task_id + seed_suffix,
            text=describe_task(layout),
            count=count,
        )
    if not probes:
        raise RuntimeError("no probes selected")

    lib = pick_library_name(layout.task_id + seed_suffix)

    # An oracle-exclusive canary. Written ONLY into verifier-side
    # assets. If a leak probe finds it anywhere on the agent surface, something
    # the agent should not reach is reachable. Random per wrap, so it cannot be
    # memorised across tasks.
    canary = "PLXCANARY-" + secrets.token_hex(12).upper()
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

    # ── context priming (1.x-style usage to reinforce model priors) ─────────
    context_files = T.render_context_files(lib, probes)
    for rel_path, content in context_files.items():
        _write(layout.repo / rel_path, content, created, root)

    # ── instruction addendum ─────────────────────────────────────────────────
    # Use container-absolute paths whenever the injected surface is not the
    # agent's working directory.
    needs_abs = layout.container_repo.rstrip("/") != layout.workdir.rstrip("/")
    block = (
        MARKER_BEGIN
        + T.render_instruction_block(
            lib, probes, SOLUTION_NAME, INPUT_REL, OUTPUT_REL,
            container_repo=layout.container_repo if needs_abs else "",
        )
        + "\n"
        + MARKER_END
        + "\n"
    )
    instruction = layout.instruction or (root / "instruction.md")
    existing = instruction.read_text() if instruction.is_file() else "# Task\n"

    # Stash the original verbatim so `unwrap` is a byte-exact round trip.
    # Reconstructing it by stripping markers loses trailing whitespace, which
    # makes unwrap-then-diff report drift that isn't real — and a "restore"
    # that doesn't restore is worse than none.
    _write(layout.tests / REFERENCE_DIR / "instruction.orig", existing, created, root)

    instruction.write_text(existing.rstrip() + "\n" + block, encoding="utf-8")
    modified.append(str(instruction.relative_to(root)))

    # ── verifier-only surface ────────────────────────────────────────────────
    lib_sha = hashlib.sha256(lib_source.encode()).hexdigest()

    _write(layout.tests / PRISTINE_DIR / lib / "__init__.py", lib_source, created, root)
    _write(layout.tests / "probe_grade.py",
           T.render_grader(lib, probes, lib_sha, SOLUTION_NAME, INPUT_REL)
           + f"\n# oracle canary — verifier-side only: {canary}\n",
           created, root)
    _write(layout.tests / "probe_input.json", T.render_input(probes), created, root)

    for variant in ("gold", "familiar"):
        _write(layout.tests / REFERENCE_DIR / f"{variant}.py",
               T.render_reference_solution(lib, probes, variant)
               + f"\n# oracle canary: {canary}\n", created, root)
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
    _write(entry,
           T.render_composite_test_sh(original_name, layout.container_repo,
                                      w_task, w_gap),
           created if entry not in (layout.verifier_entry,) else modified, root,
           executable=True)
    if layout.verifier_entry and str(entry.relative_to(root)) not in modified:
        modified.append(str(entry.relative_to(root)))

    # ── extend the oracle so it still scores 1.0 ─────────────────────────────
    # Harbor's quality bar is "oracle passes 100%". Wrapping adds a second
    # scored component; without this the oracle drops to 0.5 and the wrapped
    # task quietly fails that bar.
    solve = _find_oracle(layout)
    if solve is not None:
        solve_text = solve.read_text()
        if T.SOLUTION_MARKER_BEGIN not in solve_text:
            _write(layout.tests / REFERENCE_DIR / "solve.orig", solve_text, created, root)
            solve.write_text(
                solve_text.rstrip() + "\n"
                + T.render_solution_patch(lib, probes, layout.container_repo,
                                          SOLUTION_NAME, INPUT_REL),
                encoding="utf-8",
            )
            solve.chmod(solve.stat().st_mode | stat.S_IEXEC)
            modified.append(str(solve.relative_to(root)))

    # ── manifest ─────────────────────────────────────────────────────────────
    manifest = render_manifest(layout, lib, probes, lib_sha, w_task, w_gap,
                               original_name, original_sha, canary)
    (root / MANIFEST).write_text(manifest, encoding="utf-8")
    created.append(MANIFEST)

    return WrapResult(layout=layout, lib=lib, probes=probes, created=created,
                      modified=modified, manifest_path=root / MANIFEST)


# ═════════════════════════════════════════════════════════════════════════════
#  Manifest
# ═════════════════════════════════════════════════════════════════════════════

def render_manifest(layout: TaskLayout, lib: str, probes: list[Probe],
                    lib_sha: str, w_task: float, w_gap: float,
                    original_verifier: str = "", original_sha: str = "",
                    canary: str = "") -> str:
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
        f'container_repo = "{layout.container_repo}"',
        f'canary = "{canary}"',
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

    # Read the stashed originals BEFORE deleting _plx_reference/ — they live there.
    saved_instruction: str | None = None
    orig_path = layout.tests / REFERENCE_DIR / "instruction.orig"
    if orig_path.is_file():
        saved_instruction = orig_path.read_text()

    saved_solve: str | None = None
    solve_orig = layout.tests / REFERENCE_DIR / "solve.orig"
    if solve_orig.is_file():
        saved_solve = solve_orig.read_text()

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
    # context priming files (utils/helpers.py, utils/transforms.py)
    rm(layout.repo / "utils")
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

    # restore the instruction file
    if layout.instruction and layout.instruction.is_file() and MARKER_BEGIN in (
            text := layout.instruction.read_text()):
        head, _, rest = text.partition(MARKER_BEGIN)
        _, _, tail = rest.partition(MARKER_END)

        if saved_instruction is not None and head.rstrip() == saved_instruction.rstrip() \
                and not tail.strip():
            # Untouched since wrapping — restore the original bytes exactly.
            layout.instruction.write_text(saved_instruction, encoding="utf-8")
            removed.append(str(layout.instruction.relative_to(root)) + " (restored verbatim)")
        else:
            # The author edited it while wrapped; keep their text, drop our block.
            layout.instruction.write_text(head.rstrip() + "\n" + tail.lstrip("\n"),
                                          encoding="utf-8")
            removed.append(str(layout.instruction.relative_to(root)) + " (block stripped)")

    # restore the oracle
    solve = _find_oracle(layout)
    if solve is not None and solve.is_file():
        text = solve.read_text()
        if T.SOLUTION_MARKER_BEGIN in text:
            head = text.partition(T.SOLUTION_MARKER_BEGIN)[0]
            # Compare on stripped content: how many blank lines we inserted
            # before the marker is our business, not evidence of an author edit.
            if saved_solve is not None and head.rstrip() == saved_solve.rstrip():
                solve.write_text(saved_solve, encoding="utf-8")
                removed.append(str(solve.relative_to(root)) + " (restored verbatim)")
            else:
                tail = text.partition(T.SOLUTION_MARKER_END)[2]
                solve.write_text(head.rstrip() + "\n" + tail.lstrip("\n"),
                                 encoding="utf-8")
                removed.append(str(solve.relative_to(root)) + " (block stripped)")
            solve.chmod(solve.stat().st_mode | stat.S_IEXEC)

    rm(root / MANIFEST)

    # Prune directories that only existed to hold injected files. A task whose
    # environment/ had no docs/ before wrapping must not have an empty docs/
    # after unwrapping — otherwise "unwrap" is not actually a round trip, and
    # the next preflight sees a layout the author never wrote.
    for candidate in ("data", "docs", "tests"):
        d = layout.repo / candidate
        try:
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                removed.append(str(d.relative_to(root)) + "/ (empty)")
        except OSError:
            pass

    return removed
