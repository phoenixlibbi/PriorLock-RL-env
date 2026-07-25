"""PriorLock CLI — `priorlock <command> [args]`

Two ways to use PriorLock:

**Zero-effort (recommended).** Take any Harbor / Terminal-Bench task and wrap it.
Probes are selected automatically from a pre-calibrated catalog; you write
nothing::

    priorlock wrap tasks/my-task
    priorlock stage0 tasks/my-task

**Full domain authoring.** Build a bespoke synthetic library and deviation set
when you want a probe the catalog does not cover::

    priorlock new-domain mylib
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ═════════════════════════════════════════════════════════════════════════════
#  Discovery helpers
# ═════════════════════════════════════════════════════════════════════════════

def _find_stage0(path: str) -> str | None:
    """Find the legacy scripts/stage0.py closest to a task or domain path."""
    candidate = os.path.abspath(path)
    for _ in range(4):
        s0 = os.path.join(candidate, "scripts", "stage0.py")
        if os.path.isfile(s0):
            return s0
        candidate = os.path.dirname(candidate)
    return None


def _find_domains(root: str) -> list[dict]:
    domains = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "scripts", "stage0.py")):
            tasks_dir = os.path.join(d, "tasks")
            tasks = ([t for t in sorted(os.listdir(tasks_dir))
                      if os.path.isdir(os.path.join(tasks_dir, t))]
                     if os.path.isdir(tasks_dir) else [])
            domains.append({"name": name, "path": d, "tasks": tasks})
    return domains


def _find_wrapped(root: str, limit: int = 4000) -> list[Path]:
    """Find every wrapped task under root (any dir containing priorlock.toml)."""
    found: list[Path] = []
    skip = {".git", "node_modules", ".next", ".venv", "__pycache__", "trials"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        if "priorlock.toml" in filenames:
            found.append(Path(dirpath))
            dirnames[:] = []
        if len(found) >= limit:
            break
    return sorted(found)


# ═════════════════════════════════════════════════════════════════════════════
#  Commands
# ═════════════════════════════════════════════════════════════════════════════

def cmd_info(args, root: str) -> int:
    from priorlock import __version__
    from priorlock.probes import ALL_PROBES

    print(f"{BOLD}PriorLock v{__version__}{RESET}")
    print(f"{DIM}root {root}{RESET}\n")

    wrapped = _find_wrapped(root)
    if wrapped:
        print(f"{BOLD}Wrapped tasks{RESET} ({len(wrapped)})")
        from priorlock.inject import read_manifest
        for w in wrapped:
            try:
                m = read_manifest(w)
                meta = m.get("priorlock", {})
                ids = ", ".join(p.get("id", "?") for p in m.get("probe", []))
                rel = os.path.relpath(w, root)
                print(f"  {rel}")
                print(f"    {DIM}lib {meta.get('library')} · probes: {ids}{RESET}")
            except Exception as exc:
                print(f"  {os.path.relpath(w, root)}  {RED}manifest unreadable: {exc}{RESET}")
        print()

    domains = _find_domains(root)
    if domains:
        print(f"{BOLD}Authored domains{RESET} ({len(domains)})")
        for d in domains:
            print(f"  {d['name']}")
            for t in d["tasks"]:
                marker = "✓" if os.path.isfile(
                    os.path.join(d["path"], "tasks", t, "task.toml")) else "?"
                print(f"    {DIM}[{marker}] {t}{RESET}")
        print()

    if not wrapped and not domains:
        print("No wrapped tasks or authored domains found here.\n")

    print(f"{BOLD}Probe catalog{RESET}: {len(ALL_PROBES)} archetypes "
          f"({DIM}priorlock probes{RESET})")
    print()
    print("Wrap any task:  priorlock wrap <task-dir>")
    print("Offline gates:  priorlock stage0 <task-dir>")
    print("Harbor run:     harbor run -p <task-dir>")
    return 0


def cmd_probes(args, root: str) -> int:
    from priorlock.probes import BY_ID, probe_table

    if args.show:
        p = BY_ID.get(args.show)
        if not p:
            print(f"{RED}unknown probe: {args.show}{RESET}", file=sys.stderr)
            return 1
        print(f"{BOLD}{p.id}{RESET}  {DIM}{p.family} · {p.category}{RESET}\n")
        print(f"  {p.summary}\n")
        print(f"  {BOLD}signature{RESET}     {p.signature}")
        print(f"  {BOLD}output key{RESET}    {p.output_key}")
        print(f"  {BOLD}familiar (1.x){RESET} {p.familiar_behaviour}")
        print(f"  {BOLD}installed (2.x){RESET} {p.installed_behaviour}")
        if p.param:
            print(f"  {BOLD}gold call{RESET}     {p.param}={p.gold_kwargs[p.param]!r}")
            fam = p.familiar_kwargs.get(p.param, "<omitted>")
            print(f"  {BOLD}prior-locked{RESET}  {p.param}={fam!r}")
        else:
            print(f"  {BOLD}discriminator{RESET} output shape (no argument)")
        print(f"\n  {BOLD}task clause{RESET}\n    {p.task_clause}")
        print(f"\n  {BOLD}gold output{RESET}\n    {json.dumps(p.gold_output, ensure_ascii=False)}")
        print(f"  {BOLD}familiar output{RESET}\n    {json.dumps(p.familiar_output, ensure_ascii=False)}")
        return 0

    print(probe_table(family=args.family, category=args.category))
    print()
    print(f"{DIM}priorlock probes --show <id>   full detail for one probe{RESET}")
    return 0


def cmd_preflight(args, root: str) -> int:
    """Validate a host Harbor task before migrating it."""
    from priorlock.lifecycle import preflight, print_preflight

    targets = [Path(p) for p in args.paths]
    if args.recursive:
        expanded: list[Path] = []
        for t in targets:
            if (t / "task.toml").is_file():
                expanded.append(t)
            else:
                expanded += [p.parent for p in sorted(t.rglob("task.toml"))]
        targets = expanded

    reports = []
    for target in targets:
        report = preflight(target)
        reports.append(report)
        if not args.json:
            print_preflight(report)
            print()

    if args.json:
        payload = [r.to_dict() for r in reports]
        print(json.dumps(payload[0] if len(payload) == 1 else payload, indent=2))
    elif len(reports) > 1:
        ok = sum(1 for r in reports if r.ready)
        colour = GREEN if ok == len(reports) else RED
        print(f"{colour}{ok}/{len(reports)} tasks ready to wrap{RESET}")

    return 0 if all(r.ready for r in reports) else 1


def cmd_doctor(args, root: str) -> int:
    """Compare post-wrap task_score against the recorded pre-wrap baseline."""
    from priorlock.lifecycle import doctor, print_doctor

    task = Path(args.task).resolve()
    trials = Path(args.trials) if args.trials else task.parent.parent / "trials"
    report = doctor(task, trials)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_doctor(report)
    return 0 if report.healthy else 1


def cmd_wrap(args, root: str) -> int:
    from priorlock.inject import wrap_task
    from priorlock.lifecycle import (attach_baseline, find_baseline, preflight,
                                     print_preflight)

    targets = [Path(p) for p in args.paths]
    if args.recursive:
        expanded: list[Path] = []
        for t in targets:
            if (t / "task.toml").is_file():
                expanded.append(t)
                continue
            expanded += [p.parent for p in sorted(t.rglob("task.toml"))]
        targets = expanded

    if not targets:
        print(f"{RED}no tasks found{RESET}", file=sys.stderr)
        return 1

    from priorlock.inject import is_wrapped, unwrap_task

    failures = 0
    for target in targets:
        # ── --force: unwrap FIRST, so preflight judges the original task ─────
        # Otherwise P9 ("not already wrapped") and P10 ("no path collisions")
        # both fail on artefacts we are about to remove ourselves, and --force
        # becomes unusable — which is exactly when you most need it.
        if args.force and is_wrapped(target):
            removed = unwrap_task(target)
            print(f"{DIM}  unwrapped first ({len(removed)} paths removed){RESET}")

        # ── preflight unless explicitly skipped ──────────────────────────────
        if not args.skip_preflight:
            report = preflight(target)
            if not report.ready:
                print(f"{RED}✗{RESET} {target}: preflight failed\n")
                print_preflight(report)
                print(f"\n  {DIM}fix the blocking checks, or re-run with "
                      f"--skip-preflight{RESET}\n")
                failures += 1
                continue
            for warn in report.warnings:
                print(f"{YELLOW}!{RESET} {target}: {warn.id} {warn.name} — {warn.detail}")

        try:
            result = wrap_task(
                target,
                count=args.count,
                probe_ids=args.probe or None,
                w_task=args.weight_task,
                w_gap=args.weight_gap,
                force=args.force,
                repo_dir=args.repo_dir,
            )
        except Exception as exc:
            print(f"{RED}✗{RESET} {target}: {exc}")
            failures += 1
            continue

        print(f"{GREEN}✓{RESET} {BOLD}{result.layout.task_id}{RESET} wrapped")
        rel = result.layout.repo.relative_to(result.layout.root)
        print(f"  surface  {rel}  {DIM}→ {result.layout.container_repo} "
              f"(workdir {result.layout.workdir}){RESET}")
        print(f"  library  {result.lib}")
        print(f"  probes   " + ", ".join(
            f"{p.id} {DIM}({p.family}){RESET}" for p in result.probes))
        print(f"  weights  task={args.weight_task} gap={args.weight_gap}")

        # ── capture the pre-wrap oracle reward ───────────────────────────────
        if args.baseline_from:
            base = find_baseline(args.baseline_from,
                                 task_id=result.layout.task_id,
                                 agent=args.baseline_agent)
            if base:
                attach_baseline(target, base)
                print(f"  baseline {base.reward}  {DIM}({base.agent} · {base.trial}){RESET}")
            else:
                print(f"  {YELLOW}baseline not found in {args.baseline_from} "
                      f"(agent={args.baseline_agent}){RESET}")
        if args.verbose:
            for c in result.created:
                print(f"    {DIM}+ {c}{RESET}")
            for m in result.modified:
                print(f"    {DIM}~ {m}{RESET}")
        else:
            print(f"  {DIM}{len(result.created)} files created, "
                  f"{len(result.modified)} modified{RESET}")
        print(f"\n  next: {BOLD}priorlock stage0 {target}{RESET}\n")

    return 1 if failures else 0


def cmd_unwrap(args, root: str) -> int:
    from priorlock.inject import unwrap_task

    failures = 0
    for target in args.paths:
        try:
            removed = unwrap_task(target)
        except Exception as exc:
            print(f"{RED}✗{RESET} {target}: {exc}")
            failures += 1
            continue
        if not removed:
            print(f"{DIM}—{RESET} {target} was not wrapped")
        else:
            print(f"{GREEN}✓{RESET} {target} unwrapped ({len(removed)} paths removed)")
            if args.verbose:
                for r in removed:
                    print(f"    {DIM}- {r}{RESET}")
    return 1 if failures else 0


def cmd_stage0(args, root: str) -> int:
    """Run offline gates. Handles wrapped tasks and legacy authored domains."""
    from priorlock.gates import run_stage0
    from priorlock.inject import is_wrapped

    target = os.path.abspath(args.path) if args.path else root

    # 1. a single wrapped task
    if is_wrapped(target):
        report = run_stage0(target, verbose=not args.json)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.passed else 1

    # 2. a tree of wrapped tasks
    wrapped = _find_wrapped(target)
    if wrapped:
        results = []
        for w in wrapped:
            report = run_stage0(w, verbose=not args.json)
            results.append(report)
            if not args.json:
                print()
        if args.json:
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            ok = sum(1 for r in results if r.passed)
            colour = GREEN if ok == len(results) else RED
            print(f"{colour}{ok}/{len(results)} tasks pass all gates{RESET}")
        return 0 if all(r.passed for r in results) else 1

    # 3. legacy authored domain with its own scripts/stage0.py
    s0 = _find_stage0(target)
    if not s0:
        domains = _find_domains(root)
        if len(domains) == 1:
            s0 = os.path.join(domains[0]["path"], "scripts", "stage0.py")
        elif domains:
            print("Multiple domains found. Specify one:")
            for d in domains:
                print(f"  priorlock stage0 {d['name']}")
            return 1
        else:
            print(f"{RED}nothing to check at {target}{RESET}", file=sys.stderr)
            print("  wrap a task first:  priorlock wrap <task-dir>", file=sys.stderr)
            return 1

    domain_root = os.path.dirname(os.path.dirname(s0))
    print(f"Running authored Stage-0 for: {os.path.basename(domain_root)}\n")
    return subprocess.run([sys.executable, s0], cwd=domain_root).returncode


def cmd_verify(args, root: str) -> int:
    """Grade an arbitrary probe solution against a wrapped task.

    Useful for iterating on a solution locally without spinning up Harbor, and
    for inspecting exactly which arguments a solution supplied.
    """
    from priorlock.gates import _Sandbox
    from priorlock.inject import detect_layout, is_wrapped

    task = Path(args.task).resolve()
    if not is_wrapped(task):
        print(f"{RED}{task} is not wrapped{RESET}", file=sys.stderr)
        return 1

    layout = detect_layout(task)
    solution = Path(args.solution).resolve() if args.solution else None
    if args.reference:
        solution = layout.tests / "_plx_reference" / f"{args.reference}.py"
    if not solution or not solution.is_file():
        print(f"{RED}solution not found: {solution}{RESET}", file=sys.stderr)
        return 1

    sandbox = _Sandbox(layout)
    try:
        sandbox.install_solution(solution)
        result = sandbox.run_grader()
    finally:
        sandbox.cleanup()

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    gap = result.get("gap_score", 0.0)
    print(f"{BOLD}gap_score {gap}{RESET}  {DIM}({solution.name}){RESET}\n")
    for p in result.get("probes", []):
        verdict = p["verdict"]
        colour = GREEN if verdict == "override" else RED if p["score"] == 0 else ""
        supplied = p.get("detail", {}).get("supplied", [])
        print(f"  {p['id']:<28} {colour}{verdict:<24}{RESET} {p['score']:.2f}")
        if supplied:
            print(f"    {DIM}supplied: {json.dumps(supplied, ensure_ascii=False)}{RESET}")
        match = p.get("detail", {}).get("output_matches")
        if match:
            print(f"    {DIM}output matches: {match}{RESET}")
    if result.get("flags"):
        print(f"\n  {RED}flags: {', '.join(result['flags'])}{RESET}")
    return 0


def cmd_cheats(args, root: str) -> int:
    """Run the 8-class cheat battery and emit the soundness receipt."""
    from priorlock.cheats import run_battery

    task = Path(args.task).resolve()
    if args.suite:
        from priorlock.cheats import run_suite
        receipt = run_suite(task, verbose=not args.json)
    else:
        receipt = run_battery(task, verbose=not args.json)
    if args.json:
        print(json.dumps(receipt.to_dict(), indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(receipt.to_dict(), indent=2) + "\n")
        if not args.json:
            print(f"{DIM}  receipt written to {args.out}{RESET}")
    return 0 if receipt.passed else 1


def cmd_calibrate(args, root: str) -> int:
    from priorlock import calibrate as C

    if args.action == "report":
        print(C.report(args.model))
        return 0

    if args.action == "recommend":
        if not args.model:
            print(f"{RED}--model is required for recommend{RESET}", file=sys.stderr)
            return 1
        picks = C.recommended_probes(args.model, top=args.top)
        if not picks:
            print(f"Not enough data for {args.model}. Need >=3 runs per probe.")
            return 0
        print(f"Most informative probes for {BOLD}{args.model}{RESET}:\n")
        for pid in picks:
            print(f"  {pid}")
        print(f"\n{DIM}use them:  priorlock wrap <task> "
              f"{' '.join('--probe ' + p for p in picks)}{RESET}")
        return 0

    # ingest
    observations = []
    for src in args.paths:
        path = Path(src)
        if path.is_dir():
            observations += C.ingest_trial_dir(path, model=args.model)
        else:
            observations += C.ingest_reports([path], model=args.model or "unknown")

    if not observations:
        print(f"{RED}no probe reports found{RESET}", file=sys.stderr)
        print(f"{DIM}looked for verifier/probe_details.json in each trial dir{RESET}",
              file=sys.stderr)
        return 1

    C.update_calibration(observations, merge=not args.reset)
    print(f"{GREEN}✓{RESET} ingested {len(observations)} run(s)\n")
    print(C.report(args.model))
    return 0


def cmd_new_domain(args, root: str) -> int:
    from priorlock.scaffold import scaffold_domain

    name = args.name if args.name.endswith("-domain") else f"{args.name}-domain"
    base, created, ctx = scaffold_domain(name, root)

    print(f"\nCreated domain: {name}\nLocation: {base}\n")
    for p in created:
        print(f"  ✓ {p}")

    lib, task = ctx["lib"], ctx["task"]
    print(f"""
{DIM}Note: for most tasks you do not need this. `priorlock wrap <task>` injects
pre-calibrated probes automatically and requires no authoring. Use new-domain
only when you need a probe the catalog does not cover.{RESET}

Next steps (fill in the TODOs):
  1. deviation_spec.yaml                  — define your 2+ silent deviations
  2. src/{lib}/__init__.py                — implement v2.0 with deviations
  3. src/{lib}_familiar/__init__.py       — implement v1.x familiar semantics
  4. tasks/{task}/environment/repo/docs/CHANGELOG.md
  5. tasks/{task}/environment/repo/docs/api_reference.md
  6. tasks/{task}/environment/repo/data/  — input that triggers every deviation
  7. tasks/{task}/tests/grade.py          — scoring logic
  8. tasks/{task}/tests/expected.json     — gold expected values
  9. tasks/{task}/solution/solve.sh       — gold solution
 10. scripts/stage0.py                    — GOLD_CODE, FAMILIAR_CODE, grade logic
 11. bash {name}/scripts/setup.sh
 12. priorlock stage0 {name}
""")
    return 0


def cmd_version(args, root: str) -> int:
    from priorlock import __version__
    print(f"priorlock {__version__}")
    return 0


# ═════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════════════════════

def _repo_root() -> str:
    root = os.getcwd()
    for _ in range(6):
        if os.path.isfile(os.path.join(root, "pyproject.toml")):
            return root
        parent = os.path.dirname(root)
        if parent == root:
            break
        root = parent
    return os.getcwd()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="priorlock",
        description="PriorLock — measure prior-override capability in AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""migration lifecycle:
  1  build + validate your task as an ordinary Harbor task
  2  harbor run -p tasks/my-task -a oracle     capture the baseline
  3  priorlock preflight tasks/my-task                 is it wrap-ready?
  4  priorlock wrap tasks/my-task --baseline-from trials/
  5  priorlock stage0 tasks/my-task                    10 offline gates
  6  harbor run -p tasks/my-task -a oracle     re-run
  7  priorlock doctor tasks/my-task                    did wrapping break it?

other:
  priorlock wrap tasks/ --recursive         migrate an entire suite
  priorlock verify tasks/my-task --reference familiar
  priorlock probes --family default_flip    browse the catalog
  priorlock calibrate ingest trials/ --model claude-opus-5
""",
    )
    parser.add_argument("--version", action="store_true", help="print version and exit")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("info", help="list wrapped tasks, authored domains, and catalog size")

    p_probes = sub.add_parser("probes", help="browse the pre-calibrated probe catalog")
    p_probes.add_argument("--family", choices=["default_flip", "value_remap", "result_shape"])
    p_probes.add_argument("--category", choices=["collection", "numeric", "text",
                                                 "temporal", "mapping"])
    p_probes.add_argument("--show", metavar="ID", help="full detail for one probe")

    p_wrap = sub.add_parser("wrap", help="inject probes into an existing Harbor task")
    p_wrap.add_argument("paths", nargs="+", help="task directory (or a tree, with -r)")
    p_wrap.add_argument("-r", "--recursive", action="store_true",
                        help="wrap every task.toml found beneath each path")
    p_wrap.add_argument("-n", "--count", type=int, default=3,
                        help="number of probes to inject (default 3)")
    p_wrap.add_argument("--probe", action="append", metavar="ID",
                        help="pin a specific probe (repeatable; overrides auto-selection)")
    p_wrap.add_argument("--weight-task", type=float, default=0.5,
                        help="weight of the native task reward (default 0.5)")
    p_wrap.add_argument("--weight-gap", type=float, default=0.5,
                        help="weight of the prior-override reward (default 0.5)")
    p_wrap.add_argument("-f", "--force", action="store_true",
                        help="regenerate an already-wrapped task")
    p_wrap.add_argument("--repo-dir", metavar="DIR",
                        help="override the agent-visible directory probes are injected into "
                             "(auto-detected from the Dockerfile COPY map)")
    p_wrap.add_argument("--skip-preflight", action="store_true",
                        help="wrap even if preflight reports blocking problems")
    p_wrap.add_argument("--baseline-from", metavar="TRIALS_DIR",
                        help="record the pre-wrap oracle reward from a Harbor trials dir")
    p_wrap.add_argument("--baseline-agent", default="oracle",
                        help="agent name to read the baseline from (default: oracle)")
    p_wrap.add_argument("-v", "--verbose", action="store_true")

    p_pre = sub.add_parser("preflight", help="check a task is healthy and wrap-ready")
    p_pre.add_argument("paths", nargs="+")
    p_pre.add_argument("-r", "--recursive", action="store_true")
    p_pre.add_argument("--json", action="store_true")

    p_doc = sub.add_parser("doctor", help="prove wrapping did not damage the host task")
    p_doc.add_argument("task")
    p_doc.add_argument("-t", "--trials", help="Harbor trials dir (default: <task>/../../trials)")
    p_doc.add_argument("--json", action="store_true")

    p_unwrap = sub.add_parser("unwrap", help="remove everything wrap added")
    p_unwrap.add_argument("paths", nargs="+")
    p_unwrap.add_argument("-v", "--verbose", action="store_true")

    p_s0 = sub.add_parser("stage0", help="run offline gates (no Docker, no API key)")
    p_s0.add_argument("path", nargs="?", default=None)
    p_s0.add_argument("--json", action="store_true", help="machine-readable output")

    p_verify = sub.add_parser("verify", help="grade one probe solution locally")
    p_verify.add_argument("task")
    p_verify.add_argument("-s", "--solution", help="path to a probe_solution.py")
    p_verify.add_argument("--reference", choices=["gold", "familiar", "stub", "bypass"],
                          help="grade a generated reference solution instead")
    p_verify.add_argument("--json", action="store_true")

    p_ch = sub.add_parser("cheats", help="run the cheat battery, emit a soundness receipt")
    p_ch.add_argument("task")
    p_ch.add_argument("--suite", action="store_true",
                      help="pool across every probe archetype for a usable Wilson interval")
    p_ch.add_argument("--json", action="store_true")
    p_ch.add_argument("-o", "--out", metavar="FILE", help="write the receipt as JSON")

    p_cal = sub.add_parser("calibrate", help="measure how informative each probe is")
    p_cal.add_argument("action", choices=["ingest", "report", "recommend"])
    p_cal.add_argument("paths", nargs="*", help="Harbor trials dir(s) or report JSON")
    p_cal.add_argument("--model", help="model name to attribute runs to")
    p_cal.add_argument("--top", type=int, default=5)
    p_cal.add_argument("--reset", action="store_true", help="discard existing counts")

    p_nd = sub.add_parser("new-domain", help="scaffold a bespoke authored domain")
    p_nd.add_argument("name")

    return parser


DISPATCH = {
    "info": cmd_info,
    "probes": cmd_probes,
    "preflight": cmd_preflight,
    "doctor": cmd_doctor,
    "wrap": cmd_wrap,
    "unwrap": cmd_unwrap,
    "stage0": cmd_stage0,
    "verify": cmd_verify,
    "cheats": cmd_cheats,
    "calibrate": cmd_calibrate,
    "new-domain": cmd_new_domain,
}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = _repo_root()

    if args.version:
        return cmd_version(args, root)
    if not args.command:
        parser.print_help()
        return 0

    fn = DISPATCH.get(args.command)
    if fn is None:
        parser.print_help()
        return 1

    try:
        code = fn(args, root)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"{RED}error: {exc}{RESET}", file=sys.stderr)
        if os.environ.get("PRIORLOCK_TRACEBACK"):
            raise
        return 1
    sys.exit(code)


if __name__ == "__main__":
    main()
