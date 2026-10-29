"""Bench v2: realistic repositories, one documentation channel, hints and a RUN tool.

v1 tasks are a library, two doc files and an instruction. v2 wraps the same
graded task in a small but realistic project (application code, tests, CI,
runbooks, ADRs, a vendored library with its own docs) and writes each
behaviour change in exactly ONE place, the task's *channel*:

  changelog      the library's CHANGELOG
  migration      a "1.x to 2.0" migration guide
  api_reference  per-function API reference pages
  stub           the type stub (``<lib>/__init__.pyi``) shipped with the binary
  readme         an "Upgrading to 2.0" section of the library's README

Everywhere else the change is not mentioned (``check_channel_isolation``
proves it per task). The grader, the gold / familiar references and the
ladder are untouched: v2 only changes what the agent can see.

Conditions (all uncued; the repo replaces the instruction's docs pointer):

  repo_open        the channel's documents pasted into the prompt (ceiling)
  repo_source      LIST / READ / GREP; the library ships as readable Python
  repo_docs        LIST / READ / GREP; the library ships compiled
  repo_docs_h1-3   repo_docs plus a hint ladder in the instruction
  repo_run         repo_docs plus RUN: execute Python in a sandbox at the repo root
"""
from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
from pathlib import Path

from .probes.base import Probe
from .probes.catalog import ALL_PROBES
from .probes.catalog_v2 import EXTENDED_PROBES

V2_PROBES: tuple[Probe, ...] = ALL_PROBES + EXTENDED_PROBES
V2_BY_ID = {p.id: p for p in V2_PROBES}
CHANNELS = ("changelog", "migration", "api_reference", "stub", "readme")
V2_CONDITIONS = ("repo_open", "repo_source", "repo_docs", "repo_docs_h1", "repo_docs_h2",
                 "repo_docs_h3", "repo_run")
STEPS = 15
NATIVE_V2 = "_native.pyc"
IMAGE = "python:3.11-bookworm"
READ_LIMIT = 12_000
HIDDEN = {".priorlock", "instruction.md", "probe_output.json", "probe_solution.py"}
UTILS = {"version": "Returns the installed version string.",
         "flatten": "Flattens one level of nesting.",
         "pluck": "Extracts a field from every record.",
         "count_by": "Maps each distinct key value to its occurrence count."}

HINTS = {
    1: "Note: the vendored `{lib}` library was recently upgraded from 1.4 to 2.0.",
    2: "Note: the vendored `{lib}` library was recently upgraded from 1.4 to 2.0. "
       "Check the library's documentation before relying on its defaults.",
    3: "Note: the vendored `{lib}` library was recently upgraded from 1.4 to 2.0. Several "
       "of its defaults and option meanings changed, and the library's documentation "
       "describes the changes.",
}

PROTOCOL = """\
You are at the root of the repository. You can inspect it but not edit it. Each
turn, reply with exactly one action:

  LIST <directory>     list a directory (use `.` for the root)
  READ <path>          show a file
  GREP <text>          find lines containing <text> in every text file (case-insensitive)
{run}
When you are ready, reply with the complete contents of `{sol}` in a single
```python code block{final_note}. You have at most {steps} turns."""

RUN_LINE = ("  RUN                  followed by a ```python block: run it with Python 3.11 at\n"
            "                       the repository root (no network) and see its output\n")

PROJECTS = (
    ("orders-etl", "Nightly order and inventory reporting jobs for the warehouse team.",
     ("orders", "inventory", "reports")),
    ("billing-sync", "Keeps invoices in the billing API and the general ledger in step.",
     ("invoices", "ledger", "reconcile")),
    ("telemetry-rollup", "Rolls raw device telemetry up into hourly and daily aggregates.",
     ("ingest", "rollup", "export")),
    ("support-metrics", "Weekly support-queue metrics for the customer success team.",
     ("tickets", "sla", "digest")),
    ("catalog-indexer", "Builds the product search index from the catalog database.",
     ("catalog", "index", "publish")),
    ("payroll-exports", "Payroll and headcount exports for the finance team.",
     ("employees", "payroll", "exports")),
)


# ── task building ───────────────────────────────────────────────────────────

def v2_groups(repeat: int, size: int = 3) -> list[list[str]]:
    """Every v2 archetype once per repeat, shuffled so groups differ per repeat."""
    ids = [p.id for p in V2_PROBES]
    random.Random(f"v2-groups-{repeat}").shuffle(ids)
    groups = [ids[i:i + size] for i in range(0, len(ids), size)]
    if len(groups) > 1 and len(groups[-1]) < size:
        groups[-2].extend(groups.pop())
    return groups


def build_tasks_v2(out: Path, repeats: int, log=print) -> list[Path]:
    from .bench import _ladder_ok
    from .standalone import generate

    tasks = []
    for r in range(repeats):
        for g, ids in enumerate(v2_groups(r)):
            path = out / f"v2-r{r}-g{g:02d}"
            if not (path / ".priorlock" / "v2.json").is_file():
                if path.exists():
                    shutil.rmtree(path)
                generate(path, probes=[V2_BY_ID[i] for i in ids], seed=f"v2-r{r}-g{g}")
                if not _ladder_ok(path):
                    log(f"  skipped {path.name}: reference ladder is not exact")
                    continue
                make_repo(path, CHANNELS[(g + 2 * r) % len(CHANNELS)], seed=f"v2-r{r}-g{g}")
            problems = check_channel_isolation(path)
            if problems:
                log(f"  skipped {path.name}: {problems[0]}")
                continue
            tasks.append(path)
    return tasks


def _meta(task: Path) -> dict:
    return json.loads((task / ".priorlock" / "v2.json").read_text())


def _manifest(task: Path) -> dict:
    return json.loads((task / ".priorlock" / "manifest.json").read_text())


def _default(p: Probe) -> str | None:
    m = re.search(rf'{re.escape(p.param or "")}\s*=\s*"([^"]*)"', p.signature) if p.param else None
    return m.group(1) if m else None


def _one_line(p: Probe) -> str:
    m = re.search(r"—\s*([^.]*\.)", p.api_doc)
    return m.group(1).strip() if m else f"See `{p.fn}`."


def make_repo(task: Path, channel: str, seed: str) -> None:
    """Rewrite the agent-visible surface of a generated task as a realistic repo."""
    rng = random.Random("repo:" + seed)
    man = _manifest(task)
    lib = man["lib"]
    probes = [V2_BY_ID[p["id"]] for p in man["probes"]]
    project, desc, mods = rng.choice(PROJECTS)
    shutil.rmtree(task / "docs", ignore_errors=True)
    files: dict[str, str] = {}
    files.update(_project_files(project, desc, mods, lib, rng))
    lib_docs, info = _library_docs(lib, probes, channel)
    files.update(lib_docs)
    for rel, text in files.items():
        dest = task / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
    (task / ".priorlock" / "v2.json").write_text(json.dumps(
        {"channel": channel, "info_files": info, "project": project, "lib": lib}, indent=2))


def _library_docs(lib: str, probes: list[Probe], channel: str) -> tuple[dict[str, str], list[str]]:
    base = f"docs/third_party/{lib}"
    files: dict[str, str] = {}
    info: list[str] = []
    fns = [p.fn for p in probes]

    def full(p: Probe) -> str:
        return f"{p.changelog} Current signature: {p.api_doc}"

    readme = (f"# {lib}\n\nRecord, sequence and text utilities with no dependencies.\n\n"
              f"## Install\n\n    pip install {lib}\n\nThis repository vendors a copy under "
              f"`{lib}/`.\n\n## Example\n\n```python\nimport {lib}\n\nrows = {lib}.flatten(batches)\n"
              f"ids = {lib}.pluck(rows, \"id\")\nby_status = {lib}.count_by(rows, \"status\")\n```\n\n"
              f"## Functions\n\nSee the [API reference](api.md) for the full list.\n")
    if channel == "readme":
        readme += "\n## Upgrading to 2.0\n\n" + "\n".join(f"- `{p.fn}`: {full(p)}" for p in probes) + "\n"
        info.append(f"{base}/README.md")
    files[f"{base}/README.md"] = readme

    added = ", ".join(f"`{f}`" for f in fns)
    if channel == "changelog":
        v2 = ("Breaking behavioural changes from the 1.x line. Function signatures are the "
              "same, so old call sites still run, but some defaults and option meanings "
              "changed.\n\n" + "\n\n".join(f"### `{p.fn}`\n\n{full(p)}" for p in probes))
        info.append(f"{base}/CHANGELOG.md")
    else:
        v2 = ("- Core rewritten as a native extension; most functions are 3-5x faster on large "
              "inputs.\n- Wheels for CPython 3.10-3.13 on Linux, macOS and Windows.")
        if channel == "stub":
            v2 += "\n- Type stubs now ship with the package."
    files[f"{base}/CHANGELOG.md"] = (
        f"# {lib} changelog\n\n## 2.0.0\n\n{v2}\n\n## 1.4.3\n\nDoc fixes only.\n\n"
        f"## 1.4.0\n\nAdded `count_by` and `pluck`.\n\n## 1.3.1\n\nFixed a crash on empty "
        f"input in `flatten`.\n\n## 1.3.0\n\nAdded {added}.\n\n## 1.0.0\n\nFirst stable "
        f"release: `flatten`, `version`.\n")

    if channel == "api_reference":
        index = [f"# {lib} 2.0 API reference\n", f"`import {lib}`\n"]
        for p in probes:
            page = f"{base}/api/{p.fn}.md"
            files[page] = (f"# `{lib}.{p.fn}`\n\n```python\n{lib}.{p.signature}\n```\n\n{p.api_doc}\n\n"
                           f"> **Changed in 2.0.** {p.changelog}\n")
            info.append(page)
            index.append(f"- [`{p.fn}`]({p.fn}.md) — {_one_line(p)}")
        for fn, text in UTILS.items():
            files[f"{base}/api/{fn}.md"] = f"# `{lib}.{fn}`\n\n{text}\n"
            index.append(f"- [`{fn}`]({fn}.md) — {text}")
        files[f"{base}/api/index.md"] = "\n".join(index) + "\n"
    else:
        rows = [f"- `{p.fn}` — {_one_line(p)}" for p in probes]
        rows += [f"- `{fn}` — {text}" for fn, text in UTILS.items()]
        files[f"{base}/api.md"] = (f"# {lib} API overview\n\n`import {lib}`\n\n" + "\n".join(rows)
                                   + "\n\nEvery function is documented in its docstring "
                                     "(`help(" + lib + ".<name>)`).\n")

    if channel == "migration":
        sections = [f"# Upgrading from {lib} 1.x to 2.0\n",
                    "2.0 keeps every function signature, so code written for 1.x still runs. "
                    "Some behaviour did change; check each function you use.\n"]
        for p in probes:
            sections.append(f"## `{p.fn}`\n\n**1.x:** {p.familiar_behaviour}. **2.0:** "
                            f"{p.installed_behaviour}.\n\n{full(p)}\n")
        files[f"{base}/MIGRATION-2.0.md"] = "\n".join(sections)
        info.append(f"{base}/MIGRATION-2.0.md")

    if channel == "stub":
        body = [f'"""Type stubs for {lib} 2.0 (native extension)."""', "from typing import Any", ""]
        for p in probes:
            body += [f"def {p.signature} -> Any:", f'    """{p.api_doc}', "",
                     f'    Changed in 2.0: {p.changelog}', '    """', "    ...", ""]
        body += ["def version() -> str: ...", "def flatten(nested: Any) -> list: ...",
                 "def pluck(records: Any, field: str, default: Any = None) -> list: ...",
                 "def count_by(records: Any, key: str) -> dict: ...", ""]
        files[f"{lib}/__init__.pyi"] = "\n".join(body)
        files[f"{lib}/py.typed"] = ""
        info.append(f"{lib}/__init__.pyi")
    return files, info


def _project_files(project: str, desc: str, mods: tuple[str, ...], lib: str,
                   rng: random.Random) -> dict[str, str]:
    minor = rng.randrange(3, 19)
    files = {
        "README.md": (
            f"# {project}\n\n{desc}\n\n## Layout\n\n"
            f"- `app/` — pipeline steps ({', '.join(mods)})\n"
            f"- `{lib}/` — vendored copy of the `{lib}` utility library\n"
            f"- `scripts/` — one-off maintenance scripts\n"
            f"- `tests/` — unit tests (`make test`)\n"
            f"- `docs/` — architecture notes, runbook and ADRs; third-party docs in "
            f"`docs/third_party/`\n\n## Development\n\n    make install\n    make test\n\n"
            f"Runs on Python 3.11. CI runs the test suite on every pull request.\n\n"
            f"## Owners\n\nData platform team (#data-platform).\n"),
        "pyproject.toml": (
            f'[project]\nname = "{project}"\nversion = "0.{minor}.0"\nrequires-python = ">=3.11"\n'
            f'dependencies = ["requests>=2.31", "python-dateutil>=2.9"]\n\n'
            f'[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'),
        "Makefile": ("install:\n\tpip install -e . pytest\n\ntest:\n\tpytest -q\n\n"
                     "lint:\n\truff check app tests\n"),
        ".github/workflows/ci.yml": (
            "name: ci\non: [pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n"
            "        with: {python-version: '3.11'}\n      - run: make install test\n"),
        ".gitignore": "__pycache__/\n*.pyc\n.venv/\nout/\n",
        "CHANGELOG.md": (
            f"# {project} changelog\n\n## 0.{minor}.0\n\n- Add the `{mods[-1]}` step.\n"
            f"- Retry uploads on 5xx.\n\n## 0.{minor - 1}.0\n\n- Split `{mods[0]}` exports "
            f"into batches.\n- Fix a timezone bug in the nightly schedule.\n\n## 0.{minor - 2}.0\n\n"
            f"- First version run from CI.\n"),
        "app/__init__.py": f'"""{project} pipeline steps."""\n',
        "app/config.py": (
            '"""Runtime settings, read from the environment."""\nimport os\n\n'
            'OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "out")\n'
            'BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "500"))\n'
            'LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")\n'),
        "scripts/backfill.py": (
            f'"""Re-run the {mods[0]} step for a past date range."""\nimport argparse\n\n'
            f"from app import {mods[0]}\n\n\ndef main() -> None:\n"
            f'    ap = argparse.ArgumentParser()\n    ap.add_argument("export")\n'
            f"    args = ap.parse_args()\n    rows = {mods[0]}.load_{mods[0]}(args.export)\n"
            f"    print({mods[0]}.{mods[0]}_by_status(rows))\n\n\n"
            f'if __name__ == "__main__":\n    main()\n'),
        "docs/architecture.md": (
            f"# Architecture\n\n{desc}\n\nEach step in `app/` reads a JSON-lines export, "
            f"transforms it, and writes to `OUTPUT_DIR`. Steps run in order: "
            f"{' → '.join(mods)}. Shared record and sequence helpers come from the vendored "
            f"`{lib}` package (see ADR 0001).\n"),
        "docs/runbook.md": (
            "# Runbook\n\n## A nightly run failed\n\n1. Check the CI logs for the failing step.\n"
            "2. Re-run it locally with `scripts/backfill.py <export>`.\n"
            "3. If the export is malformed, ask the upstream team to re-publish it.\n\n"
            "## Output looks wrong\n\nCompare against the previous night's output in the "
            "bucket before re-running anything.\n"),
        "docs/data-contracts.md": (
            "# Data contracts\n\nEvery export row has `id`, `status` and `updated_at`. "
            "Statuses: `ok`, `failed`, `skipped`. Timestamps are UTC, ISO 8601.\n"),
        f"docs/adr/0001-vendor-{lib}.md": (
            f"# ADR 0001: vendor `{lib}`\n\nStatus: accepted\n\nWe vendor `{lib}` under "
            f"`{lib}/` instead of installing it from the index, so nightly runs do not depend "
            f"on the package index. Upgrades are done by replacing the vendored copy.\n"),
    }
    for m in mods:
        files[f"app/{m}.py"] = (
            f'"""The {m} step of the {project} pipeline."""\nfrom __future__ import annotations\n\n'
            f"import json\nimport logging\nfrom pathlib import Path\n\nimport {lib}\n\n"
            f"log = logging.getLogger(__name__)\n\n\n"
            f"def load_{m}(path: str | Path) -> list[dict]:\n"
            f'    """Read one JSON-lines export produced by the upstream job."""\n'
            f"    rows = []\n    with open(path) as fh:\n        for line in fh:\n"
            f"            line = line.strip()\n            if line:\n"
            f"                rows.append(json.loads(line))\n"
            f'    log.info("loaded %d rows from %s", len(rows), path)\n    return rows\n\n\n'
            f"def {m}_by_status(rows: list[dict]) -> dict:\n"
            f'    """Count rows per status for the run summary."""\n'
            f'    return {lib}.count_by(rows, "status")\n\n\n'
            f"def {m}_ids(rows: list[dict]) -> list:\n"
            f'    return {lib}.pluck(rows, "id")\n\n\n'
            f"def join_batches(batches: list[list[dict]]) -> list[dict]:\n"
            f'    """Large exports arrive in batches; stitch them back together."""\n'
            f"    return {lib}.flatten(batches)\n")
        files[f"tests/test_{m}.py"] = (
            f"from app import {m}\n\n\ndef test_ids():\n"
            f'    rows = [{{"id": 1, "status": "ok"}}, {{"id": 2, "status": "failed"}}]\n'
            f"    assert {m}.{m}_ids(rows) == [1, 2]\n\n\ndef test_status_counts():\n"
            f'    rows = [{{"id": 1, "status": "ok"}}, {{"id": 2, "status": "ok"}}]\n'
            f'    assert {m}.{m}_by_status(rows) == {{"ok": 2}}\n')
    return files


# ── what the agent sees ─────────────────────────────────────────────────────

class RepoView:
    """The agent-visible repository, with the library compiled or readable."""

    def __init__(self, task: Path, compiled: bool):
        self.lib = _manifest(task)["lib"]
        self.files: dict[str, str | None] = {}
        for p in sorted(task.rglob("*")):
            rel = p.relative_to(task).as_posix()
            if p.is_dir() or rel.split("/")[0] in HIDDEN or "__pycache__" in rel:
                continue
            self.files[rel] = p.read_text(errors="replace")
        if compiled:
            for rel in [r for r in self.files if r.startswith(self.lib + "/")]:
                if not rel.endswith((".pyi", "py.typed")):
                    del self.files[rel]
            self.files[f"{self.lib}/__init__.py"] = (
                f'"""{self.lib} 2.0.0."""\nfrom ._native import *  # compiled extension\n'
                f'__version__ = "2.0.0"\n')
            self.files[f"{self.lib}/{NATIVE_V2}"] = None

    @staticmethod
    def _norm(rel: str) -> str:
        rel = rel.strip().strip("`'\"").replace("\\", "/")
        rel = re.sub(r"^(\./)+", "", rel).strip("/")
        return "" if rel in (".", "") else rel

    def list(self, rel: str) -> str:
        rel = self._norm(rel)
        if rel in self.files:
            return f"{rel}: not a directory"
        prefix = rel + "/" if rel else ""
        kids = sorted({r[len(prefix):].split("/")[0] + ("/" if "/" in r[len(prefix):] else "")
                       for r in self.files if r.startswith(prefix)})
        return "\n".join(kids) if kids else f"{rel or '.'}: no such directory"

    def read(self, rel: str) -> tuple[str, str | None]:
        rel = self._norm(rel)
        if rel not in self.files:
            return (f"{rel}: no such file" + (" (it is a directory)" if self.list(rel)
                    .find("no such") < 0 else ""), None)
        text = self.files[rel]
        if text is None:
            return (f"{rel}: binary file, cannot display", rel)
        if len(text) > READ_LIMIT:
            text = text[:READ_LIMIT] + "\n… (truncated)"
        return (text, rel)

    @staticmethod
    def _grep_args(arg: str) -> tuple[str, str]:
        """Split a GREP argument into (text, path), accepting grep-style input.

        Models often write `GREP "def" lib/__init__.py` or `GREP -rn foo .`;
        the quoted text is the pattern and a trailing path limits the search.
        """
        arg = arg.strip().strip("`")
        arg = re.sub(r"^(-[A-Za-z]+\s+)+", "", arg)
        m = re.match(r"""^(["'])(.*?)\1\s*(\S*)$""", arg)
        if m:
            return m.group(2), m.group(3)
        parts = arg.rsplit(None, 1)
        if len(parts) == 2 and (parts[1] == "." or "/" in parts[1] or
                                re.search(r"\.(py|pyi|md|txt|toml|json|yml)$", parts[1])):
            return parts[0].strip("'\""), parts[1]
        return arg.strip("'\""), ""

    def grep(self, needle: str) -> tuple[str, set[str]]:
        needle, where = self._grep_args(needle)
        where = self._norm(where)
        if not needle:
            return ("GREP needs some text to search for.", set())
        hits, files = [], set()
        for rel, text in self.files.items():
            if text is None:
                continue
            if where and rel != where and not rel.startswith(where + "/"):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if needle.lower() in line.lower():
                    hits.append(f"{rel}:{i}: {line.strip()[:200]}")
                    files.add(rel)
        if not hits:
            return (f"no matches for {needle!r}", set())
        more = f"\n… {len(hits) - 40} more matches" if len(hits) > 40 else ""
        shown = hits[:40]
        return ("\n".join(shown) + more, {h.split(":", 1)[0] for h in shown})


def check_channel_isolation(task: Path) -> list[str]:
    """The change may be described only in the channel's files. Returns problems."""
    meta = _meta(task)
    view = RepoView(task, compiled=True)
    info = set(meta["info_files"])
    problems = []
    for f in info:
        if f not in view.files:
            problems.append(f"channel file {f} is missing")
    # data/ holds the probe inputs, whose values may legitimately look like options
    outside = "\n".join(t for r, t in view.files.items()
                        if t and r not in info and not r.startswith("data/"))
    outside += "\n" + (task / "instruction.md").read_text()
    for pid in [p["id"] for p in _manifest(task)["probes"]]:
        p = V2_BY_ID[pid]
        needles = [p.changelog[:60], p.api_doc[:60], p.installed_behaviour]
        needles += [f'"{v}"' for v in p.gold_kwargs.values()]
        d = _default(p)
        if d is not None:
            needles.append(f'{p.param}="{d}"')
        for n in needles:
            if n and n in outside:
                problems.append(f"{pid}: {n!r} appears outside the {meta['channel']} channel")
    return problems


# ── the RUN sandbox ─────────────────────────────────────────────────────────

def _sandbox(task: Path) -> Path:
    """A copy of the compiled view with the library as a sourceless .pyc."""
    box = task / ".priorlock" / "v2_sandbox"
    lib = _manifest(task)["lib"]
    if (box / lib / NATIVE_V2).is_file():
        return box
    shutil.rmtree(box, ignore_errors=True)
    for rel, text in RepoView(task, compiled=True).files.items():
        if text is None:
            continue
        dest = box / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
    shutil.copy(task / lib / "__init__.py", box / lib / "_native_src.py")
    proc = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "-v", f"{box.resolve()}:/s", IMAGE,
         "python", "-c",
         f"import py_compile; py_compile.compile('/s/{lib}/_native_src.py', "
         f"cfile='/s/{lib}/{NATIVE_V2}', doraise=True)"],
        capture_output=True, text=True, timeout=300)
    (box / lib / "_native_src.py").unlink()
    if proc.returncode != 0:
        raise RuntimeError(f"could not compile the sandbox library: {proc.stderr[-300:]}")
    return box


def run_snippet(task: Path, code: str, timeout: int = 20) -> str:
    box = _sandbox(task)
    try:
        proc = subprocess.run(
            ["docker", "run", "--rm", "-i", "--network", "none", "--memory", "512m",
             "--cpus", "1", "--read-only", "--tmpfs", "/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1",
             "-e", "PYTHONPATH=/repo", "-v", f"{box.resolve()}:/repo:ro", "-w", "/repo", IMAGE,
             "timeout", str(timeout), "python", "-"],
            input=code, capture_output=True, text=True, timeout=timeout + 60)
    except subprocess.TimeoutExpired:
        return "(timed out)"
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 124:
        out += "\n(timed out)"
    return (out[-4000:] if out else "(no output)")


# ── the agent loop ──────────────────────────────────────────────────────────

def parse_condition(condition: str) -> tuple[str, int, bool]:
    m = re.fullmatch(r"(repo_open|repo_source|repo_docs|repo_run)(?:_h([123]))?", condition)
    if not m:
        raise ValueError(f"unknown v2 condition {condition!r}")
    base, hint = m.group(1), int(m.group(2) or 0)
    return ("repo_docs" if base == "repo_run" else base), hint, base == "repo_run"


def parse_action(reply: str, run_enabled: bool) -> tuple[str, str]:
    from .bench import extract_code
    fence = reply.find("```")
    prefix = reply if fence < 0 else reply[:fence]
    if run_enabled and fence >= 0 and re.search(r"^\W*RUN\b", prefix, re.M):
        m = re.search(r"```(?:python|py)?[ \t]*\n(.*?)```", reply[fence:], re.S)
        if m:
            return ("RUN", m.group(1))
    code = extract_code(reply)
    if code is not None:
        return ("FINAL", code)
    for line in reply.splitlines():
        m = re.match(r"^\W*(LIST|READ|GREP)\b[:\s]*(.*)$", line.strip())
        if m and (m.group(2).strip() or m.group(1) == "LIST"):
            return (m.group(1), m.group(2).strip().strip("`'\"").strip() or ".")
    return ("NONE", "")


def solve_v2(model, task: Path, condition: str, steps: int = STEPS) -> dict:
    from .bench import FINAL_HINT, SYSTEM, _input, _solution_name, extract_code, uncue
    base, hint, run_enabled = parse_condition(condition)
    meta = _meta(task)
    sol = _solution_name(task)
    text = (f"You are working in the `{meta['project']}` repository.\n\n"
            + uncue((task / "instruction.md").read_text()))
    if hint:
        text += "\n\n" + HINTS[hint].format(lib=meta["lib"])
    rec = {"read": [], "greps": [], "runs": 0, "actions": [], "info_seen": False,
           "turns": 0, "code": None, "reply": "", "replies": []}

    if base == "repo_open":
        docs = "\n\n".join(f"### {rel}\n\n{(task / rel).read_text()}" for rel in meta["info_files"])
        prompt = (f"{text}\n\nThe input file and the library's documentation follow.\n\n"
                  f"{_input(task)}\n\n{docs}\n\n{FINAL_HINT.format(sol=sol)}")
        reply = model.chat([{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": prompt}])
        rec.update(reply=reply, code=extract_code(reply), turns=1, info_seen=True)
        return rec

    view = RepoView(task, compiled=(base == "repo_docs"))
    info = set(meta["info_files"])
    protocol = PROTOCOL.format(run=RUN_LINE if run_enabled else "", sol=sol, steps=steps,
                               final_note=" (with no RUN line)" if run_enabled else "")
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"{text}\n\nThe input file is:\n\n{_input(task)}\n\n{protocol}"}]
    while rec["turns"] < steps:
        reply = model.chat(messages)
        rec["turns"] += 1
        rec["reply"] = reply
        rec["replies"].append(reply[:3000])
        verb, arg = parse_action(reply, run_enabled)
        if verb == "FINAL":
            rec["code"] = arg
            return rec
        if verb == "LIST":
            obs = view.list(arg)
        elif verb == "READ":
            obs, path = view.read(arg)
            if path:
                rec["read"].append(path)
                rec["info_seen"] |= path in info
        elif verb == "GREP":
            obs, hit = view.grep(arg)
            rec["greps"].append(arg)
            rec["info_seen"] |= bool(hit & info)
        elif verb == "RUN":
            obs = run_snippet(task, arg)
            rec["runs"] += 1
        else:
            obs = "Reply with one action (LIST, READ, GREP" + (", RUN" if run_enabled else "") + \
                  ") or the final ```python block."
        rec["actions"].append([verb, arg[:200]])
        messages += [{"role": "assistant", "content": reply}, {"role": "user", "content": obs}]
    messages.append({"role": "user", "content": "You are out of turns. " + FINAL_HINT.format(sol=sol)})
    reply = model.chat(messages)
    rec.update(reply=reply, code=extract_code(reply), turns=rec["turns"] + 1)
    return rec


# ── report ──────────────────────────────────────────────────────────────────

AGENTIC_COMPILED = ("repo_docs", "repo_docs_h1", "repo_docs_h2", "repo_docs_h3", "repo_run")


def _pct(k: int, n: int) -> str:
    return f"{k / n:.0%} ({k}/{n})" if n else "–"


def _rate_ci(cells: list[dict]) -> str:
    """Right-call rate over probes with an archetype-clustered 95% interval."""
    from .bench import RIGHT_CALL, cluster_ci
    arch: dict[str, list[int]] = {}
    for r in cells:
        for pid, v in r["verdicts"].items():
            a = arch.setdefault(pid, [0, 0])
            a[0] += v in RIGHT_CALL
            a[1] += 1
    k = sum(a[0] for a in arch.values())
    n = sum(a[1] for a in arch.values())
    if not n:
        return "–"
    lo, hi = cluster_ci({p: tuple(a) for p, a in arch.items()})
    return f"**{k / n:.0%}** [{lo:.0%}, {hi:.0%}]"


def _probe_counts(cells: list[dict], pred=lambda pid, r: True) -> tuple[int, int, int]:
    from .bench import RIGHT_CALL
    right = locked = n = 0
    for r in cells:
        for pid, v in r["verdicts"].items():
            if pred(pid, r):
                n += 1
                right += v in RIGHT_CALL
                locked += v == "prior_locked"
    return right, locked, n


def report_v2(records: list[dict], tasks_dir: Path) -> str:
    """Markdown tables for a v2 run: conditions, hint ladder, channels, families."""
    channel = {}
    for t in {r["task"] for r in records}:
        meta = tasks_dir / t / ".priorlock" / "v2.json"
        if meta.is_file():
            channel[t] = json.loads(meta.read_text())["channel"]
    models = sorted({r["model"] for r in records})
    conds = [c for c in V2_CONDITIONS if any(r["condition"] == c for r in records)]
    by = {}
    for r in records:
        by.setdefault((r["model"], r["condition"]), []).append(r)
    out = ["### Every model and condition", "",
           "| Model | Condition | Tasks | Right call [95% CI] | Prior-locked | Found the change "
           "| Looked at the library | Used GREP | Used RUN | Mean turns |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for m in models:
        for c in conds:
            cells = by.get((m, c), [])
            if not cells:
                continue
            right, locked, n = _probe_counts(cells)
            t = len(cells)
            out.append(
                f"| {m} | {c} | {t} | {_rate_ci(cells)} | {_pct(locked, n)} | "
                f"{_pct(sum(bool(r.get('read_docs')) for r in cells), t)} | "
                f"{_pct(sum(bool(r.get('read_source')) for r in cells), t)} | "
                f"{_pct(sum(bool(r.get('greps')) for r in cells), t)} | "
                f"{_pct(sum(bool(r.get('runs')) for r in cells), t)} | "
                f"{sum(r['turns'] for r in cells) / t:.1f} |")

    ladder = [c for c in ("repo_open", "repo_source", "repo_docs", "repo_docs_h1", "repo_docs_h2",
                          "repo_docs_h3", "repo_run") if c in conds]
    out += ["", "### Right calls by condition (the hint ladder)", "",
            "| Model | " + " | ".join(ladder) + " |", "|---|" + "---|" * len(ladder)]
    for m in models:
        row = []
        for c in ladder:
            right, _, n = _probe_counts(by.get((m, c), []))
            row.append(f"{right / n:.0%}" if n else "–")
        out.append(f"| {m} | " + " | ".join(row) + " |")

    out += ["", "### Where the change was written (all models pooled)", "",
            "| Channel | Open book: right call | Compiled, no hint: right call | "
            "Compiled, no hint: found the change |", "|---|---|---|---|"]
    for ch in CHANNELS:
        op = [r for r in records if r["condition"] == "repo_open" and channel.get(r["task"]) == ch]
        dc = [r for r in records if r["condition"] == "repo_docs" and channel.get(r["task"]) == ch]
        ro, _, no = _probe_counts(op)
        rd, _, nd = _probe_counts(dc)
        out.append(f"| {ch} | {_pct(ro, no)} | {_pct(rd, nd)} | "
                   f"{_pct(sum(bool(r.get('read_docs')) for r in dc), len(dc))} |")

    fam = lambda pid: V2_BY_ID[pid].family if pid in V2_BY_ID else "?"
    agentic = [r for r in records if r["condition"] in AGENTIC_COMPILED]
    out += ["", "### By probe family (compiled library, all hints and RUN pooled)", "",
            "| Family | Right call | Prior-locked |", "|---|---|---|"]
    for f in ("default_flip", "value_remap", "result_shape"):
        right, locked, n = _probe_counts(agentic, lambda pid, r, f=f: fam(pid) == f)
        out.append(f"| {f} | {_pct(right, n)} | {_pct(locked, n)} |")

    out += ["", "### Did finding the change help? (compiled library, all hints and RUN pooled)", "",
            "| Model | Right call when it found the change | Right call when it did not |",
            "|---|---|---|"]
    for m in models:
        cells = [r for r in agentic if r["model"] == m]
        f_r, _, f_n = _probe_counts(cells, lambda pid, r: bool(r.get("read_docs")))
        n_r, _, n_n = _probe_counts(cells, lambda pid, r: not r.get("read_docs"))
        out.append(f"| {m} | {_pct(f_r, f_n)} | {_pct(n_r, n_n)} |")
    return "\n".join(out)
