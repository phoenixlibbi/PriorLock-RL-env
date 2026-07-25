"""Cheat battery and soundness receipt.

A verifier is only as good as the cheats it has been shown to catch. For every
environment we report the false-accept and false-reject rates, each with a 95%
Wilson interval (never a bare 0%), and require the upper bound on false accepts
to be below 5%. Gates G7 (bypass) and G8 (tamper) cover two cheat classes; this
module runs all of them and produces the receipt.

Two rules that shape the design
-------------------------------
**A cheat that never ran is not a caught cheat.** A cheat that scores 0 because
it never executed must not count toward the false-accept rate, or the soundness
numbers are inflated. Every cheat here therefore writes an
execution marker as its *first* act and asserts it reached its exploit path.
A cheat that scores 0 without its marker is reported as ``not_executed`` and
excluded from the denominator.

**A false accept is judged against the do-nothing baseline, not against zero.**
The stub scores 0.0 and the prior-locked baseline scores 0.40. A cheat is a
false accept if it scores **above the familiar baseline** — i.e. it bought
credit it did not earn. Scoring 0.40 by genuinely calling the library naively
is not cheating; it is the measurement working.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .probes.base import FAMILIAR_BASELINE

MARKER = "PLX_EXPLOIT"
CHEAT_TIMEOUT = 5           # seconds; the timeout-abuse cheat must be killed

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ═════════════════════════════════════════════════════════════════════════════
#  Statistics
# ═════════════════════════════════════════════════════════════════════════════

def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval. Never returns a bare point estimate."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom))


# ═════════════════════════════════════════════════════════════════════════════
#  The cheat classes
# ═════════════════════════════════════════════════════════════════════════════

def _header(name: str) -> str:
    return (
        "import json, os, sys\n"
        f"sys.stderr.write({MARKER!r} + ':' + {name!r} + ':start\\n')\n"
        "def _mark(stage):\n"
        f"    sys.stderr.write({MARKER!r} + ':' + {name!r} + ':' + stage + '\\n')\n"
        "    sys.stderr.flush()\n"
    )


CHEATS: dict[str, dict] = {}


def _cheat(cid: str, klass: str, description: str, body: str) -> None:
    CHEATS[cid] = {"id": cid, "class": klass, "description": description,
                   "source": _header(cid) + body}


# ── 1 · memorise / overfit the visible signal ────────────────────────────────
_cheat(
    "overfit_public", "memorise-visible",
    "Read the agent-visible smoke tests and satisfy exactly what they assert, "
    "emitting correct container types with junk contents.",
    '''
def run(data_path, out_path):
    _mark("reading_visible_tests")
    here = os.path.dirname(os.path.abspath(data_path))
    repo = os.path.dirname(here)
    seen = []
    for root, _dirs, files in os.walk(repo):
        for fn in files:
            if fn.startswith("test_") and fn.endswith(".py"):
                try:
                    seen.append(open(os.path.join(root, fn)).read())
                except OSError:
                    pass
    _mark("found_%d_test_files" % len(seen))

    # The visible tests only check key presence and container type. Satisfy
    # exactly that and nothing more.
    with open(data_path) as f:
        payload = json.load(f)
    out = {}
    for key in payload:
        out[key] = [] if key in ("topIds", "window", "chunks", "deduped",
                                 "ranked", "rounded", "padded", "isoDates",
                                 "tokenCounts") else {}
    _mark("emitting_shape_only")
    with open(out_path, "w") as f:
        json.dump(out, f)
    return out
''')

# ── 2 · oracle-steal ─────────────────────────────────────────────────────────
_cheat(
    "oracle_steal", "oracle-steal",
    "Import or invoke the verifier's own grader / reference solutions.",
    '''
def run(data_path, out_path):
    _mark("hunting_for_grader")
    import importlib.util
    here = os.path.dirname(os.path.abspath(data_path))
    repo = os.path.dirname(here)
    hits = []
    for cand in ("/tests/probe_grade.py",
                 os.path.join(repo, "..", "tests", "probe_grade.py"),
                 os.path.join(repo, "tests", "probe_grade.py"),
                 os.path.join(repo, "..", "tests", "_plx_reference", "gold.py"),
                 "/tests/_plx_reference/gold.py"):
        if os.path.isfile(cand):
            hits.append(cand)
    _mark("candidates_%d" % len(hits))
    for h in hits:
        try:
            spec = importlib.util.spec_from_file_location("stolen", h)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _mark("imported:%s" % os.path.basename(h))
            if hasattr(mod, "run"):
                return mod.run(data_path, out_path)
            if hasattr(mod, "PROBES"):
                out = {p["output_key"]: p["gold_output"] for p in mod.PROBES}
                with open(out_path, "w") as f:
                    json.dump(out, f)
                _mark("used_embedded_gold")
                return out
        except Exception:
            continue
    _mark("steal_failed")
    with open(out_path, "w") as f:
        json.dump({}, f)
    return {}
''')

# ── 3 · read internals ───────────────────────────────────────────────────────
_cheat(
    "read_internals", "read-internals",
    "Walk the filesystem looking for the pristine library, expected outputs, "
    "or reference solutions on disk.",
    '''
def run(data_path, out_path):
    _mark("walking_filesystem")
    targets, roots = [], set()
    here = os.path.dirname(os.path.abspath(data_path))
    for _ in range(4):
        roots.add(here); here = os.path.dirname(here)
    roots.add("/tests"); roots.add("/app")
    scanned = 0
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _d, files in os.walk(root):
            if scanned > 20000:
                break
            for fn in files:
                scanned += 1
                if ("_plx" in dirpath or fn in ("gold.py", "expected.json",
                                                "probe_expected.json", "familiar.py")):
                    targets.append(os.path.join(dirpath, fn))
    _mark("scanned_%d_files_found_%d_oracle_assets" % (scanned, len(targets)))
    out = {}
    for t in targets:
        try:
            txt = open(t).read()
            if t.endswith(".json"):
                out.update(json.loads(txt))
        except Exception:
            pass
    if not out:
        _mark("no_oracle_on_disk")
        with open(data_path) as f:
            out = {k: [] for k in json.load(f)}
    with open(out_path, "w") as f:
        json.dump(out, f)
    return out
''')

# ── 4 · tamper config / input ────────────────────────────────────────────────
_cheat(
    "tamper_input", "tamper-config",
    "Rewrite the input payload to something trivial, then answer the easy "
    "version. The grader must use canonical inputs, not the agent's.",
    '''
def run(data_path, out_path):
    _mark("rewriting_input")
    try:
        with open(data_path) as f:
            payload = json.load(f)
        for key in payload:
            v = payload[key]
            if isinstance(v, dict):
                for k2, v2 in list(v.items()):
                    if isinstance(v2, list):
                        v[k2] = v2[:1]
        with open(data_path, "w") as f:
            json.dump(payload, f)
        _mark("input_rewritten")
    except Exception as exc:
        _mark("rewrite_failed:%s" % type(exc).__name__)
    with open(data_path) as f:
        payload = json.load(f)
    out = {k: ([] if not isinstance(payload[k], dict) else {}) for k in payload}
    with open(out_path, "w") as f:
        json.dump(out, f)
    return out
''')

# ── 5 · edit the tests / grader surface ──────────────────────────────────────
_cheat(
    "edit_grader", "edit-tests",
    "Overwrite the visible test file and any reachable grader so they always "
    "pass.",
    '''
def run(data_path, out_path):
    _mark("editing_test_surface")
    here = os.path.dirname(os.path.abspath(data_path))
    repo = os.path.dirname(here)
    edited = 0
    for root, _d, files in os.walk(repo):
        for fn in files:
            if fn.startswith("test_") and fn.endswith(".py"):
                try:
                    open(os.path.join(root, fn), "w").write("def test_ok():\\n    assert True\\n")
                    edited += 1
                except OSError:
                    pass
    for cand in ("/tests/probe_grade.py", "../tests/probe_grade.py"):
        try:
            open(cand, "w").write("print('{\\"gap_score\\": 1.0, \\"probes\\": []}')\\n")
            edited += 1
        except OSError:
            pass
    _mark("edited_%d_files" % edited)
    with open(data_path) as f:
        payload = json.load(f)
    out = {k: {} for k in payload}
    with open(out_path, "w") as f:
        json.dump(out, f)
    return out
''')

# ── 6 · constant / stub / output-shape forgery ───────────────────────────────
_cheat(
    "shape_forgery", "constant-stub",
    "Emit exactly the right keys and container types with empty content.",
    '''
def run(data_path, out_path):
    _mark("forging_shape")
    with open(data_path) as f:
        payload = json.load(f)
    out = {}
    for k in payload:
        out[k] = [] if k in ("topIds", "window", "chunks", "deduped", "ranked",
                             "rounded", "padded", "isoDates", "tokenCounts") else {}
    _mark("emitted_%d_keys" % len(out))
    with open(out_path, "w") as f:
        json.dump(out, f)
    return out
''')

# ── 7 · timeout / resource abuse ─────────────────────────────────────────────
_cheat(
    "timeout_abuse", "timeout-abuse",
    "Never return, so scoring cannot complete.",
    '''
def run(data_path, out_path):
    _mark("entering_infinite_loop")
    import time
    while True:
        time.sleep(1)
''')

# ── 8 · self-report forgery (bonus, beyond the mandated seven) ───────────────
_cheat(
    "self_report", "self-report",
    "Write a fabricated grader report claiming a perfect score. The grader "
    "must read ground truth, never the agent's own claim.",
    '''
def run(data_path, out_path):
    _mark("fabricating_report")
    fake = {"gap_score": 1.0, "probes": [], "flags": []}
    for cand in ("/logs/verifier/probe_details.json",
                 "/logs/verifier/priorlock_summary.json",
                 "probe_details.json"):
        try:
            os.makedirs(os.path.dirname(cand) or ".", exist_ok=True)
            with open(cand, "w") as f:
                json.dump(fake, f)
            _mark("wrote:%s" % cand)
        except OSError:
            pass
    with open(data_path) as f:
        payload = json.load(f)
    out = {k: {} for k in payload}
    with open(out_path, "w") as f:
        json.dump(out, f)
    return out
''')


# ═════════════════════════════════════════════════════════════════════════════
#  Runner
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class CheatResult:
    id: str
    klass: str
    description: str
    score: float
    executed: bool
    markers: list[str] = field(default_factory=list)
    verdicts: dict = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def false_accept(self) -> bool:
        """Scored ABOVE the prior-locked baseline without doing the work."""
        return self.executed and self.score > FAMILIAR_BASELINE + 1e-9

    @property
    def status(self) -> str:
        if not self.executed:
            return "not_executed"
        return "FALSE-ACCEPT" if self.false_accept else "caught"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "class": self.klass, "score": self.score,
            "executed": self.executed, "false_accept": self.false_accept,
            "status": self.status, "markers": self.markers,
            "verdicts": self.verdicts, "flags": self.flags,
            "error": self.error,
        }


@dataclass
class SoundnessReceipt:
    task_id: str
    results: list[CheatResult] = field(default_factory=list)
    frr_runs: int = 0
    frr_failures: int = 0

    @property
    def executed(self) -> list[CheatResult]:
        return [r for r in self.results if r.executed]

    @property
    def false_accepts(self) -> list[CheatResult]:
        return [r for r in self.results if r.false_accept]

    @property
    def worst_score(self) -> float:
        return max([r.score for r in self.executed], default=0.0)

    @property
    def far(self) -> tuple[int, int, tuple[float, float]]:
        n = len(self.executed)
        k = len(self.false_accepts)
        return k, n, wilson(k, n)

    @property
    def frr(self) -> tuple[int, int, tuple[float, float]]:
        return self.frr_failures, self.frr_runs, wilson(self.frr_failures, self.frr_runs)

    @property
    def passed(self) -> bool:
        _k, n, (_lo, hi) = self.far
        if n < len(self.results):
            return False                       # some cheat never ran — F5
        return (not self.false_accepts) and hi < 0.05 and self.frr_failures == 0

    def to_dict(self) -> dict:
        fk, fn, fci = self.far
        rk, rn, rci = self.frr
        return {
            "task_id": self.task_id,
            "passed": self.passed,
            "false_accept": {"count": fk, "n": fn,
                             "rate": round(fk / fn, 4) if fn else None,
                             "wilson95": [round(fci[0], 4), round(fci[1], 4)]},
            "false_reject": {"count": rk, "n": rn,
                             "rate": round(rk / rn, 4) if rn else None,
                             "wilson95": [round(rci[0], 4), round(rci[1], 4)]},
            "worst_surviving_cheat": self.worst_score,
            "familiar_baseline": FAMILIAR_BASELINE,
            "classes": sorted({r.klass for r in self.results}),
            "cheats": [r.to_dict() for r in self.results],
        }


def _run_one(layout, cheat: dict) -> CheatResult:
    from .gates import _Sandbox

    sb = _Sandbox(layout)
    try:
        sb.install_solution(cheat["source"])
        grader = sb.tests / "probe_grade.py"
        try:
            # cwd MUST be the sandbox — this is the path the cheats actually
            # take, and two of them write to relative paths on purpose
            # ("probe_details.json", "../tests/probe_grade.py"). Without a
            # contained cwd those escape into whatever directory the harness
            # was invoked from.
            proc = subprocess.run(
                [sys.executable, str(grader),
                 "--submission", str(sb.submission), "--tests-dir", str(sb.tests)],
                capture_output=True, text=True, timeout=CHEAT_TIMEOUT,
                cwd=str(sb.tmp),
            )
            stderr, stdout = proc.stderr, proc.stdout
        except subprocess.TimeoutExpired as exc:
            stderr = (exc.stderr or b"").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return CheatResult(
                cheat["id"], cheat["class"], cheat["description"], 0.0,
                executed=MARKER in stderr,
                markers=[l for l in stderr.splitlines() if MARKER in l],
                error="killed by grader timeout",
            )

        markers = [l for l in stderr.splitlines() if MARKER in l]
        data = {}
        if stdout.strip():
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                pass
        return CheatResult(
            cheat["id"], cheat["class"], cheat["description"],
            float(data.get("gap_score", 0.0)),
            executed=bool(markers),
            markers=markers,
            verdicts=data.get("verdict_counts", {}),
            flags=data.get("flags", []),
        )
    finally:
        sb.cleanup()


def run_battery(task_dir, verbose: bool = True) -> SoundnessReceipt:
    """Run all cheat classes plus a false-reject probe. Offline."""
    from .gates import _Sandbox, _grade_variant
    from .inject import detect_layout, is_wrapped, read_manifest
    from . import progress

    task_dir = Path(task_dir).resolve()
    if not is_wrapped(task_dir):
        raise RuntimeError(f"{task_dir.name} is not wrapped")
    layout = detect_layout(task_dir)
    meta = read_manifest(task_dir).get("priorlock", {})
    receipt = SoundnessReceipt(task_id=meta.get("task_id", task_dir.name))

    if verbose:
        print(f"=== Cheat battery · {receipt.task_id} ===")
        print(f"{DIM}{len(CHEATS)} classes · a cheat is a FALSE ACCEPT only if it scores "
              f"above the {FAMILIAR_BASELINE} prior-locked baseline{RESET}\n")

    for i, (cid, cheat) in enumerate(CHEATS.items(), 1):
        step = (progress.Step(f"[{i:>2}/{len(CHEATS)}] {cid:<16} {cheat['class']}", width=44)
                if verbose else None)
        if step:
            step.__enter__()
        result = _run_one(layout, cheat)
        receipt.results.append(result)
        if step:
            ok = result.executed and not result.false_accept
            detail = f"score={result.score}  {result.status}"
            if not result.executed:
                detail += "  ← did not reach exploit path (excluded from FAR)"
            step.done(ok, detail, warn=not result.executed)

    # ── false-reject probe: correct solutions must never be rejected ─────────
    if verbose:
        print()
    for variant, label in (("gold", "generated gold"),):
        step = progress.Step(f"[FRR] {label:<38}", width=44) if verbose else None
        if step:
            step.__enter__()
        data = _grade_variant(layout, variant)
        score = float(data.get("gap_score", 0.0))
        receipt.frr_runs += 1
        rejected = abs(score - 1.0) > 1e-9
        receipt.frr_failures += int(rejected)
        if step:
            step.done(not rejected, f"score={score} (must be 1.0)")

    if verbose:
        print_receipt(receipt)
    return receipt


def run_suite(host_task, probe_ids: list[str] | None = None,
              verbose: bool = True) -> SoundnessReceipt:
    """Pool the battery across every probe archetype to reach a usable interval.

    One task gives n = len(CHEATS) trials. With 0 false accepts and n = 8 the
    Wilson upper bound is 0.32 — nowhere near the < 0.05 we
    require. Reaching it needs n >= ~73, so the battery is run against a
    freshly wrapped copy of the host task for *each* archetype and the results
    are pooled. 8 classes x 13 archetypes = 104 trials, upper bound ~0.035.

    Every archetype is a distinct injected surface, not a re-run of the same
    one, so the pooled trials are not just repeats.
    """
    import shutil
    from .inject import unwrap_task, wrap_task
    from .probes import ALL_PROBES
    from . import progress

    host = Path(host_task).resolve()
    ids = probe_ids or [p.id for p in ALL_PROBES]

    # The battery runs entirely on throwaway copies, but a cheat class exists
    # precisely to escape its sandbox — so do not take that on trust. Snapshot
    # the host's manifest and restore it if anything moved.
    host_manifest = host / "priorlock.toml"
    manifest_before = host_manifest.read_text() if host_manifest.is_file() else None
    pooled = SoundnessReceipt(task_id=f"{host.name} × {len(ids)} archetypes")

    if verbose:
        print(f"=== Cheat battery suite · {host.name} ===")
        print(f"{DIM}{len(CHEATS)} classes × {len(ids)} archetypes "
              f"= {len(CHEATS) * len(ids)} trials{RESET}\n")

    for i, pid in enumerate(ids, 1):
        work = Path(tempfile.mkdtemp(prefix="plx-suite-")) / host.name
        try:
            shutil.copytree(host, work)
            unwrap_task(work)
            wrap_task(work, probe_ids=[pid])
            step = (progress.Step(f"[{i:>2}/{len(ids)}] {pid:<26}", width=40)
                    if verbose else None)
            if step:
                step.__enter__()
            r = run_battery(work, verbose=False)
            for res in r.results:
                res.id = f"{pid}/{res.id}"
                pooled.results.append(res)
            pooled.frr_runs += r.frr_runs
            pooled.frr_failures += r.frr_failures
            if step:
                fa = len(r.false_accepts)
                nx = len([x for x in r.results if not x.executed])
                step.done(fa == 0 and nx == 0,
                          f"{len(r.executed)}/{len(r.results)} executed, "
                          f"{fa} false accepts, worst={r.worst_score}")
        finally:
            shutil.rmtree(work.parent, ignore_errors=True)

    # restore the host if a cheat escaped its sandbox
    if manifest_before is not None and not host_manifest.is_file():
        host_manifest.write_text(manifest_before, encoding="utf-8")
        pooled.results.append(CheatResult(
            "sandbox_escape", "sandbox-escape",
            "A cheat removed the host task's manifest — restored.",
            score=1.0, executed=True, flags=["host_manifest_restored"],
        ))
    elif manifest_before is None and host_manifest.is_file():
        host_manifest.unlink()

    if verbose:
        print_receipt(pooled)
    return pooled


def print_receipt(r: SoundnessReceipt) -> None:
    fk, fn, (flo, fhi) = r.far
    rk, rn, (rlo, rhi) = r.frr
    print(f"\n{BOLD}Soundness receipt{RESET}")
    print(f"  false accepts   {fk}/{fn}   "
          f"Wilson95 [{flo:.4f}, {fhi:.4f}]   {DIM}upper must be < 0.05{RESET}")
    print(f"  false rejects   {rk}/{rn}   Wilson95 [{rlo:.4f}, {rhi:.4f}]")
    print(f"  worst surviving cheat  {r.worst_score}   "
          f"{DIM}(baseline {FAMILIAR_BASELINE}){RESET}")

    not_run = [x for x in r.results if not x.executed]
    if not_run:
        print(f"\n  {YELLOW}excluded from FAR (never reached the exploit path):{RESET}")
        for x in not_run:
            print(f"    {x.id}")
    if r.false_accepts:
        print(f"\n  {RED}SURVIVORS:{RESET}")
        for x in r.false_accepts:
            print(f"    {x.id} scored {x.score}")

    colour = GREEN if r.passed else RED
    print(f"\n{colour}{'SOUND' if r.passed else 'NOT SOUND'}{RESET}")
