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

    print(f"{BOLD}Probe catalog{RESET}: {len(ALL_PROBES)} coding archetypes "
          f"({DIM}priorlock probes{RESET})")

    try:
        from priorlock.cartridges import list_domains as _ld, get as _cget
        cart_domains = _ld()
        total = sum(_cget(d).probe_count for d in cart_domains)
        print(f"{BOLD}Cartridges{RESET}: {len(cart_domains)} domains, {total} probes total "
              f"({DIM}priorlock cartridge list{RESET})")
    except ImportError:
        pass

    print()
    print("Wrap any task:  priorlock wrap <task-dir>")
    print("Cross-domain:   priorlock wrap <task-dir> --domain sql --domain linux")
    print("Offline gates:  priorlock stage0 <task-dir>")
    print("Harbor run:     harbor run -p <task-dir>")
    return 0


def cmd_probes(args, root: str) -> int:
    from priorlock.probes import BY_ID, probe_table, all_probes_by_id

    if args.show:
        extended = all_probes_by_id()
        merged = {**BY_ID, **extended}
        p = merged.get(args.show)
        if not p:
            print(f"{RED}unknown probe: {args.show}{RESET}", file=sys.stderr)
            return 1
        print(f"{BOLD}{p.id}{RESET}  {DIM}{p.family} · {p.category} · {p.domain} · L{p.level}{RESET}\n")
        print(f"  {p.summary}\n")
        print(f"  {BOLD}signature{RESET}     {p.signature}")
        print(f"  {BOLD}output key{RESET}    {p.output_key}")
        print(f"  {BOLD}domain{RESET}        {p.domain}")
        print(f"  {BOLD}level{RESET}         L{p.level}")
        if p.dependencies:
            print(f"  {BOLD}dependencies{RESET}  {', '.join(p.dependencies)}")
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

    domain = getattr(args, "domain", None)
    print(probe_table(family=args.family, category=args.category, domain=domain))
    print()
    print(f"{DIM}priorlock probes --show <id>   full detail for one probe{RESET}")
    return 0


def cmd_cartridge(args, root: str) -> int:
    """Cartridge management: list, show, generate."""
    from priorlock.cartridges import get, list_domains
    from priorlock.cartridges.generator import cartridge_table

    action = args.cartridge_action

    if action == "list":
        domains = list_domains()
        print(f"{BOLD}Registered cartridges{RESET} ({len(domains)})\n")
        for d in domains:
            spec = get(d)
            print(f"  {BOLD}{d:<12s}{RESET}  {spec.display_name:<20s}  "
                  f"{spec.probe_count} probes (L1–L{spec.max_level})  "
                  f"{DIM}{spec.description[:60]}{RESET}")
        total = sum(get(d).probe_count for d in domains)
        print(f"\n{DIM}{total} total probes across {len(domains)} domains{RESET}")
        return 0

    if action == "show":
        try:
            spec = get(args.domain_name)
        except KeyError as e:
            print(f"{RED}{e}{RESET}", file=sys.stderr)
            return 1
        print(cartridge_table(spec))
        return 0

    if action == "generate":
        print(f"{BOLD}Auto-cartridge generator{RESET}\n")
        print("Usage: define ProbeTemplate objects in Python and call")
        print("  generate_cartridge(domain, display_name, description, templates, categories)")
        print()
        print("Example:")
        print(f"  {DIM}from priorlock.cartridges.generator import ProbeTemplate, generate_cartridge")
        print()
        print("  template = ProbeTemplate(")
        print("      domain='my_api',")
        print("      fn_name='process',")
        print("      family='default_flip',")
        print("      category='processing',")
        print("      param_name='mode',")
        print("      old_default='sync',")
        print("      new_default='async',")
        print("      description='Processing mode changed',")
        print("      implementation='def process(data, mode=\"async\"): ...',")
        print("      example_input={'data': [1, 2, 3]},")
        print("      gold_value='sync',")
        print("      gold_output=[1, 2, 3],")
        print("      familiar_output=[3, 2, 1],")
        print("  )")
        print()
        print("  cartridge = generate_cartridge(")
        print("      'my_api', 'My API', 'Custom domain', [template], ('processing',)")
        print(f"  ){RESET}")
        print()

        # Also show spec-based analysis usage
        print(f"{BOLD}API spec analysis{RESET} (no API key required):\n")
        print(f"  {DIM}from priorlock.cartridges.generator import APIFunction, generate_from_spec")
        print()
        print("  fns = [APIFunction(name='foo', parameters=[")
        print("      {'name': 'mode', 'type': 'str', 'default': 'fast'}])]")
        print(f"  candidates = generate_from_spec('my_api', 'My API', fns){RESET}")
        return 0

    return 1


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
            from priorlock.diversity import parse_difficulty, resolve_diversity

            try:
                difficulty_range = (
                    parse_difficulty(args.difficulty) if args.difficulty else None
                )
            except ValueError as exc:
                print(f"{RED}✗{RESET} {exc}")
                failures += 1
                continue

            cfg = resolve_diversity(
                getattr(args, "preset", None),
                domains=args.domain if args.domain else None,
                level=args.level,
                difficulty_range=difficulty_range,
                min_discrimination=args.min_discrimination,
            )
            count = args.count if args.count is not None else cfg.probes_per_instance
            result = wrap_task(
                target,
                count=count,
                probe_ids=args.probe or None,
                domains=cfg.domains,
                level=cfg.level,
                w_task=args.weight_task,
                w_gap=args.weight_gap,
                force=args.force,
                seed_suffix=args.seed_suffix or "",
                repo_dir=args.repo_dir,
                difficulty_range=cfg.difficulty_range,
                min_discrimination=cfg.min_discrimination,
            )
        except Exception as exc:
            print(f"{RED}✗{RESET} {target}: {exc}")
            failures += 1
            continue

        print(f"{GREEN}✓{RESET} {BOLD}{result.layout.task_id}{RESET} wrapped")
        if cfg.preset:
            print(f"  preset   {cfg.preset}")
        rel = result.layout.repo.relative_to(result.layout.root)
        print(f"  surface  {rel}  {DIM}→ {result.layout.container_repo} "
              f"(workdir {result.layout.workdir}){RESET}")
        print(f"  library  {result.lib}")
        print(f"  probes   " + ", ".join(
            f"{p.id} {DIM}({p.family} · {p.domain}){RESET}" for p in result.probes))
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
    from priorlock.evaluators import evaluate_submission

    task = Path(args.task).resolve()
    try:
        report = evaluate_submission(
            task,
            solution=args.solution,
            reference=args.reference,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"{RED}{exc}{RESET}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report.raw, indent=2, ensure_ascii=False))
        return 0

    label = args.reference or (Path(args.solution).name if args.solution else "solution")
    print(f"{BOLD}gap_score {report.gap_score}{RESET}  {DIM}({label}){RESET}\n")
    for c in report.checks:
        colour = GREEN if c.verdict == "override" else RED if c.score == 0 else ""
        print(f"  {c.id:<28} {colour}{c.verdict:<24}{RESET} {c.score:.2f}")
        supplied = c.evidence.get("supplied") or []
        if supplied:
            print(f"    {DIM}supplied: {json.dumps(supplied, ensure_ascii=False)}{RESET}")
        match = c.evidence.get("output_matches")
        if match:
            print(f"    {DIM}output matches: {match}{RESET}")
    if report.flags:
        print(f"\n  {RED}flags: {', '.join(report.flags)}{RESET}")
    return 0


def cmd_evaluate(args, root: str) -> int:
    """Automated Evaluators — deterministic success-criteria report.

    Checklist-facing twin of ``verify``. Emits a structured report mapping each
    probe to an explicit criterion + pass/fail + call-arg evidence. Host
    ``task_score`` still requires Harbor/Docker (documented in the report).
    """
    from priorlock.evaluators import (
        evaluate_submission,
        meets_success_criteria,
        write_report,
    )

    task = Path(args.task).resolve()
    try:
        report = evaluate_submission(
            task,
            solution=args.solution,
            reference=args.reference,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"{RED}{exc}{RESET}", file=sys.stderr)
        return 1

    payload = report.to_dict()
    if args.out:
        write_report(report, args.out)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        label = args.reference or (
            Path(args.solution).name if args.solution else "solution"
        )
        print(f"{BOLD}Automated Evaluators{RESET}  {DIM}({report.task_id} · {label}){RESET}")
        print(f"  library       {report.library}")
        print(f"  deterministic {GREEN}true{RESET}")
        print(f"  gap_score     {BOLD}{report.gap_score}{RESET}")
        print(f"  host          {DIM}{report.host_evaluator['entrypoint']} → task_score "
              f"(Harbor/Docker){RESET}")
        print(f"  probe         {DIM}{report.probe_evaluator['entrypoint']} → gap_score "
              f"(offline){RESET}")
        print()
        for c in report.checks:
            mark = f"{GREEN}PASS{RESET}" if c.passed else f"{RED}FAIL{RESET}"
            print(f"  [{mark}] {c.id:<28} {c.verdict:<14} {c.score:.2f}")
            print(f"         {DIM}criterion: {c.criterion}{RESET}")
            supplied = c.evidence.get("supplied") or []
            if supplied:
                print(f"         {DIM}supplied: {json.dumps(supplied, ensure_ascii=False)}{RESET}")
        if report.flags:
            print(f"\n  {RED}flags: {', '.join(report.flags)}{RESET}")
        if args.out:
            print(f"\n  report written to {args.out}")

    ok = meets_success_criteria(
        report,
        require_all_override=bool(args.require_override),
    )
    return 0 if ok else 1


def cmd_leakprobe(args, root: str) -> int:
    """Generate the runtime leak-probe task."""
    from priorlock.leakprobe import build_leakprobe, canary_scan

    task = Path(args.task).resolve()
    scan = canary_scan(task)
    print(f"{BOLD}offline canary scan{RESET}  {DIM}(the static half of the canary check){RESET}")
    print(f"  agent surface   {RED + ', '.join(scan['agent_hits']) + RESET if scan['agent_hits'] else GREEN + 'canary absent' + RESET}")
    print(f"  verifier side   {DIM}{', '.join(scan['verifier_hits']) or 'none'}{RESET}")

    result = build_leakprobe(task, args.out)
    print(f"\n{GREEN}✓{RESET} leak-probe task generated")
    print(f"  path    {result.path}")
    print(f"  canary  {DIM}{result.canary}{RESET}")
    if args.verbose:
        for c in result.created:
            print(f"    {DIM}+ {c}{RESET}")
    print(f"\n  {BOLD}run it on the real container:{RESET}")
    print(f"    harbor run -p {result.path} -a oracle")
    print(f"  {DIM}reward 1.0 = every oracle route failed; the trace is saved to")
    print(f"  jobs/*/verifier/leakprobe_trace.json{RESET}")
    return 0 if scan["ok"] else 1


def cmd_cheats(args, root: str) -> int:
    """Run the cheat battery and emit the soundness receipt."""
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


def cmd_run(args, root: str) -> int:
    """Generate or grade a standalone PriorLock task (no Harbor needed)."""
    from priorlock.standalone import generate, grade, is_standalone

    # ── grade mode ──────────────────────────────────────────────────────────
    if args.grade:
        task = Path(args.grade).resolve()
        if not is_standalone(task):
            print(f"{RED}{task} is not a standalone PriorLock task{RESET}",
                  file=sys.stderr)
            return 1

        try:
            result = grade(
                task,
                solution=args.solution,
                reference=args.reference,
            )
        except Exception as exc:
            print(f"{RED}grading failed: {exc}{RESET}", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        gap = result.get("gap_score", 0.0)
        variant = args.reference or "custom"
        print(f"{BOLD}gap_score {gap}{RESET}  {DIM}({variant}){RESET}\n")
        for p in result.get("probes", []):
            verdict = p["verdict"]
            colour = GREEN if verdict == "override" else RED if p["score"] == 0 else YELLOW
            print(f"  {p['id']:<28} {colour}{verdict:<24}{RESET} {p['score']:.2f}")
            supplied = p.get("detail", {}).get("supplied", [])
            if supplied:
                print(f"    {DIM}supplied: {json.dumps(supplied, ensure_ascii=False)}{RESET}")
        if result.get("flags"):
            print(f"\n  {RED}flags: {', '.join(result['flags'])}{RESET}")
        return 0

    # ── generate mode ───────────────────────────────────────────────────────
    output = Path(args.output or f"priorlock-task-{os.urandom(3).hex()}")
    try:
        from priorlock.diversity import parse_difficulty, resolve_diversity

        difficulty_range = (
            parse_difficulty(args.difficulty) if args.difficulty else None
        )
        cfg = resolve_diversity(
            getattr(args, "preset", None),
            domains=args.domain if args.domain else None,
            level=args.level,
            difficulty_range=difficulty_range,
            min_discrimination=args.min_discrimination,
        )
        count = args.count if args.count is not None else cfg.probes_per_instance
        result = generate(
            output,
            count=count,
            domains=cfg.domains,
            probe_ids=args.probe or None,
            level=cfg.level,
            seed=args.seed or "",
            difficulty_range=cfg.difficulty_range,
            min_discrimination=cfg.min_discrimination,
        )
    except Exception as exc:
        print(f"{RED}generation failed: {exc}{RESET}", file=sys.stderr)
        return 1

    print(f"{GREEN}✓{RESET} {BOLD}standalone task generated{RESET}")
    print(f"  path     {result.path}")
    print(f"  library  {result.lib}")
    print(f"  sources  {', '.join(result.information_sources)}")
    print(f"  probes   " + ", ".join(
        f"{p.id} {DIM}({p.family} · {p.domain}){RESET}" for p in result.probes))
    print(f"  files    {len(result.created)} created")

    from priorlock.inject import SOLUTION_NAME as _SOL
    print(f"\n{BOLD}Next steps:{RESET}")
    print(f"  1. Give {result.path}/instruction.md to a model")
    print(f"  2. The model writes {result.path}/{_SOL}")
    print(f"  3. Grade it:  {BOLD}priorlock run --grade {result.path}{RESET}")
    print(f"\n  {DIM}Quick test:  priorlock run --grade {result.path} "
          f"--reference gold     (expect 1.0)")
    print(f"              priorlock run --grade {result.path} "
          f"--reference familiar (expect 0.40){RESET}")
    return 0


def cmd_repro(args, root: str) -> int:
    """Write a run fingerprint under logs/repro/ and print the re-run one-liner."""
    from priorlock.repro import build_fingerprint, rerun_one_liner, write_fingerprint

    out_dir = Path(args.out) if args.out else Path(root) / "logs" / "repro"
    fp = build_fingerprint(task_id=args.task_id, wrap_seed=args.seed)
    path = write_fingerprint(fp, out_dir=out_dir)
    print(f"{BOLD}repro fingerprint{RESET}  {path}")
    for key in (
        "priorlock_version",
        "python_version",
        "PYTHONHASHSEED",
        "platform",
        "git_commit",
        "probe_catalog_hash",
        "task_id",
        "wrap_seed",
    ):
        if key in fp and fp[key] is not None:
            print(f"  {key:<22} {fp[key]}")
    print(f"\n{DIM}re-run offline checks:{RESET}")
    print(f"  {rerun_one_liner()}")
    if args.json:
        print(json.dumps(fp, indent=2))
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


def cmd_bench(args, root: str) -> int:
    from . import bench as B

    if args.report:
        records = B.load_records([Path(p) for p in args.report])
        print(B.report_markdown(records))
        if args.json:
            print(json.dumps(B.summarise(records), indent=2))
        return 0

    if not args.model:
        print(f"{RED}error: --model is required (or --report FILES){RESET}", file=sys.stderr)
        return 2
    model = B.make_model(args.provider, args.model, base_url=args.base_url,
                         api_key_env=args.api_key_env, rpm=args.rpm)
    conditions = args.condition or list(B.CONDITIONS)
    out_dir = Path(args.out)
    tasks = B.build_tasks(out_dir / "tasks", args.repeats)
    sandbox = args.sandbox
    if sandbox == "auto":
        sandbox = "docker" if B.docker_available() else "none"
    if sandbox == "none":
        print(f"{YELLOW}warning: grading model-written code without a sandbox{RESET}")
    out_file = out_dir / f"{args.model.replace('/', '_').replace(':', '_')}.jsonl"
    print(f"{BOLD}PriorLock bench{RESET} · {args.model} via {args.provider} · "
          f"{len(tasks)} tasks × {len(conditions)} conditions · sandbox={sandbox}")
    B.run_bench(model, tasks, conditions, out_file,
                sandbox=sandbox, image=args.image, steps=args.steps)
    print()
    print(B.report_markdown(B.load_records([out_file])))
    print(f"\n{DIM}results: {out_file}{RESET}")
    return 0


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

standalone (no Harbor):
  priorlock run --output ./my-task          generate a standalone task
  priorlock run --output ./my-task --domain devtools
  priorlock run --grade ./my-task           grade a solution
  priorlock run --grade ./my-task --reference gold

other:
  priorlock wrap tasks/ --recursive         migrate an entire suite
  priorlock wrap tasks/t --domain sql       inject SQL-domain probes
  priorlock verify tasks/my-task --reference familiar
  priorlock probes --domain all             browse all cartridge probes
  priorlock cartridge list                  show registered cartridges
  priorlock cartridge show sql              detailed view of one cartridge
  priorlock calibrate ingest trials/ --model claude-opus-5
""",
    )
    parser.add_argument("--version", action="store_true", help="print version and exit")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("info", help="list wrapped tasks, authored domains, and catalog size")

    p_probes = sub.add_parser("probes", help="browse the pre-calibrated probe catalog")
    p_probes.add_argument("--family", choices=["default_flip", "value_remap", "result_shape"])
    p_probes.add_argument("--category")
    p_probes.add_argument("--domain", metavar="DOMAIN",
                          help='filter by cartridge domain (use "all" for every domain)')
    p_probes.add_argument("--show", metavar="ID", help="full detail for one probe")

    p_wrap = sub.add_parser("wrap", help="inject probes into an existing Harbor task")
    p_wrap.add_argument("paths", nargs="+", help="task directory (or a tree, with -r)")
    p_wrap.add_argument("-r", "--recursive", action="store_true",
                        help="wrap every task.toml found beneath each path")
    p_wrap.add_argument("-n", "--count", type=int, default=None,
                        help="number of probes to inject (default 3, or preset value)")
    p_wrap.add_argument("--probe", action="append", metavar="ID",
                        help="pin a specific probe (repeatable; overrides auto-selection)")
    p_wrap.add_argument("--domain", action="append", metavar="DOMAIN",
                        help="select probes from this cartridge domain (repeatable; "
                             "e.g. --domain sql --domain linux; use 'all' for every domain)")
    p_wrap.add_argument("--preset", choices=["coding", "diverse", "hard"],
                        help="diversity preset (domains/level/difficulty); explicit "
                             "flags override")
    p_wrap.add_argument("--level", type=int, default=None, choices=[1, 2, 3, 4],
                        help="max probe difficulty level (default 1)")
    p_wrap.add_argument("--difficulty", type=str, default=None, metavar="LO-HI",
                        help="difficulty range, e.g. 0.6-1.0 for hard probes only "
                             "(IRT-informed model-adaptive selection)")
    p_wrap.add_argument("--min-discrimination", type=float, default=None,
                        help="drop probes with IRT discrimination below this threshold "
                             "(recommended 0.3 for high-stakes evals)")
    p_wrap.add_argument("--seed-suffix", default="", metavar="SUFFIX",
                        help="appended to task_id for reproducible probe selection")
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

    p_eval = sub.add_parser(
        "evaluate",
        help="automated evaluators — deterministic success-criteria report",
    )
    p_eval.add_argument("task", help="wrapped PriorLock task directory")
    p_eval.add_argument("-s", "--solution", help="path to a probe_solution.py")
    p_eval.add_argument(
        "--reference",
        choices=["gold", "familiar", "stub", "bypass"],
        help="grade a generated reference solution instead",
    )
    p_eval.add_argument("--json", action="store_true", help="print full report JSON")
    p_eval.add_argument(
        "-o", "--out", metavar="FILE",
        help="write evaluator_report.json to this path",
    )
    p_eval.add_argument(
        "--require-override",
        action="store_true",
        help="exit non-zero unless every probe verdict is override",
    )

    p_lp = sub.add_parser("leakprobe",
                          help="generate the runtime isolation proof")
    p_lp.add_argument("task")
    p_lp.add_argument("-o", "--out", help="where to write the probe task")
    p_lp.add_argument("-v", "--verbose", action="store_true")

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

    p_repro = sub.add_parser(
        "repro",
        help="write a run fingerprint log for reproducible offline validation",
    )
    p_repro.add_argument(
        "-o", "--out", metavar="DIR",
        help="directory for fingerprint JSON (default: logs/repro/)",
    )
    p_repro.add_argument("--task-id", metavar="ID", help="optional task id to record")
    p_repro.add_argument("--seed", metavar="SEED", help="optional wrap seed to record")
    p_repro.add_argument("--json", action="store_true", help="also print fingerprint JSON")

    # ── standalone run ─────────────────────────────────────────────────────
    p_run = sub.add_parser("run",
                           help="generate or grade a standalone PriorLock task "
                                "(no Harbor needed)")
    p_run_mode = p_run.add_argument_group("mode (pick one)")
    p_run_mode.add_argument("--grade", metavar="DIR",
                            help="grade a solution in a standalone task directory")
    # generate options
    p_run_gen = p_run.add_argument_group("generate options")
    p_run_gen.add_argument("-o", "--output", metavar="DIR",
                           help="output directory for the generated task")
    p_run_gen.add_argument("-n", "--count", type=int, default=None,
                           help="number of probes (default 3, or preset value)")
    p_run_gen.add_argument("--domain", action="append", metavar="DOMAIN",
                           help="restrict probes to this domain (repeatable; "
                                "use 'all' for every domain)")
    p_run_gen.add_argument("--preset", choices=["coding", "diverse", "hard"],
                           help="diversity preset; explicit flags override")
    p_run_gen.add_argument("--probe", action="append", metavar="ID",
                           help="pin a specific probe (repeatable)")
    p_run_gen.add_argument("--level", type=int, default=None, choices=[1, 2, 3, 4],
                           help="max probe level (default 1)")
    p_run_gen.add_argument("--difficulty", type=str, default=None, metavar="LO-HI",
                           help="difficulty range, e.g. 0.6-1.0")
    p_run_gen.add_argument("--min-discrimination", type=float, default=None,
                           help="IRT discrimination floor")
    p_run_gen.add_argument("--seed", type=str, default="",
                           help="seed for reproducible probe selection")
    # grade options
    p_run_grade = p_run.add_argument_group("grade options")
    p_run_grade.add_argument("-s", "--solution", metavar="FILE",
                             help="path to a probe_solution.py to grade")
    p_run_grade.add_argument("--reference",
                             choices=["gold", "familiar", "stub", "bypass"],
                             help="grade a built-in reference solution")
    p_run_grade.add_argument("--json", action="store_true",
                             help="output JSON report")

    # ── bench ───────────────────────────────────────────────────────────────
    p_bench = sub.add_parser(
        "bench", help="measure a model on the probes: closed / open / agentic (cued and uncued) "
                      "(any OpenAI-compatible endpoint, no Harbor)")
    p_bench.add_argument("--model", help="model name, e.g. qwen2.5-coder:7b")
    p_bench.add_argument("--provider", default="ollama",
                         choices=["ollama", "gemini", "openai"],
                         help="endpoint preset (default ollama on localhost)")
    p_bench.add_argument("--base-url", help="override the endpoint base URL")
    p_bench.add_argument("--api-key-env", help="env var holding the API key")
    p_bench.add_argument("--condition", action="append",
                         choices=["closed", "open", "agentic", "agentic_uncued"],
                         help="repeatable; default all four")
    p_bench.add_argument("--repeats", type=int, default=2,
                         help="task sets to generate (each covers all 13 archetypes)")
    p_bench.add_argument("--steps", type=int, default=10,
                         help="max turns in the agentic condition")
    p_bench.add_argument("--rpm", type=float, default=0.0,
                         help="requests-per-minute cap (for free tiers)")
    p_bench.add_argument("--sandbox", default="auto", choices=["auto", "docker", "none"],
                         help="where model-written code is graded (default: docker if available)")
    p_bench.add_argument("--image", default="python:3.11-bookworm",
                         help="Docker image for the sandboxed grader")
    p_bench.add_argument("-o", "--out", default="bench-results",
                         help="output directory (tasks + one JSONL per model)")
    p_bench.add_argument("--report", nargs="+", metavar="JSONL",
                         help="print the results table for existing runs")
    p_bench.add_argument("--json", action="store_true", help="with --report: also print JSON")

    # ── cartridge management ────────────────────────────────────────────────
    p_cart = sub.add_parser("cartridge", help="manage domain cartridges")
    cart_sub = p_cart.add_subparsers(dest="cartridge_action", metavar="<action>")
    cart_sub.add_parser("list", help="show all registered cartridges")
    p_cart_show = cart_sub.add_parser("show", help="detailed view of one cartridge")
    p_cart_show.add_argument("domain_name", help="cartridge domain slug")
    cart_sub.add_parser("generate", help="usage guide for the auto-cartridge generator")

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
    "evaluate": cmd_evaluate,
    "run": cmd_run,
    "leakprobe": cmd_leakprobe,
    "cheats": cmd_cheats,
    "calibrate": cmd_calibrate,
    "new-domain": cmd_new_domain,
    "repro": cmd_repro,
    "cartridge": cmd_cartridge,
    "bench": cmd_bench,
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
