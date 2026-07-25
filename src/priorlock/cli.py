"""PriorLock CLI — priorlock <command> [args]"""
import argparse
import os
import subprocess
import sys


# ── helpers ──────────────────────────────────────────────────────────────────

def _find_stage0(path: str) -> str | None:
    """Find the stage0.py closest to a given task or domain path."""
    # Walk upward looking for scripts/stage0.py
    candidate = os.path.abspath(path)
    for _ in range(4):
        s0 = os.path.join(candidate, "scripts", "stage0.py")
        if os.path.isfile(s0):
            return s0
        candidate = os.path.dirname(candidate)
    return None


def _find_domains(root: str) -> list[dict]:
    """Return a list of discovered domain dirs (have scripts/stage0.py)."""
    domains = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "scripts", "stage0.py")):
            tasks = []
            tasks_dir = os.path.join(d, "tasks")
            if os.path.isdir(tasks_dir):
                tasks = [t for t in sorted(os.listdir(tasks_dir))
                         if os.path.isdir(os.path.join(tasks_dir, t))]
            domains.append({"name": name, "path": d, "tasks": tasks})
    return domains


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_info(args, root: str):
    """Show discovered domains and tasks."""
    from priorlock import __version__
    print(f"PriorLock v{__version__}")
    print(f"Root: {root}\n")
    domains = _find_domains(root)
    if not domains:
        print("No domains found. Expected directories with scripts/stage0.py")
        return 0
    for d in domains:
        print(f"  domain: {d['name']}")
        for t in d["tasks"]:
            task_toml = os.path.join(d["path"], "tasks", t, "task.toml")
            marker = "✓" if os.path.isfile(task_toml) else "?"
            print(f"    [{marker}] {t}")
        print()
    print(f"Harbor run:  harbor trial start -p <domain>/tasks/<task>")
    print(f"Stage-0 QA:  priorlock stage0 <domain>")
    return 0


def cmd_stage0(args, root: str):
    """Run Stage-0 offline gates for a domain."""
    target = os.path.abspath(args.path) if args.path else root
    s0 = _find_stage0(target)
    if not s0:
        # Try each known domain
        domains = _find_domains(root)
        if not domains:
            print(f"ERROR: no stage0.py found near '{target}'", file=sys.stderr)
            return 1
        if len(domains) == 1:
            s0 = os.path.join(domains[0]["path"], "scripts", "stage0.py")
        else:
            print("Multiple domains found. Specify one:")
            for d in domains:
                print(f"  priorlock stage0 {d['name']}")
            return 1

    domain_root = os.path.dirname(os.path.dirname(s0))  # strip /scripts/stage0.py
    print(f"Running Stage-0 for: {os.path.basename(domain_root)}\n")
    result = subprocess.run([sys.executable, s0], cwd=domain_root)
    return result.returncode


def cmd_version(args, root: str):
    from priorlock import __version__
    print(f"priorlock {__version__}")
    return 0


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    # Locate repo root: walk up from CWD looking for pyproject.toml
    root = os.getcwd()
    for _ in range(5):
        if os.path.isfile(os.path.join(root, "pyproject.toml")):
            break
        root = os.path.dirname(root)
    else:
        root = os.getcwd()

    parser = argparse.ArgumentParser(
        prog="priorlock",
        description="PriorLock — benchmark for prior-override capability in AI agents",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    sub = parser.add_subparsers(dest="command")

    # info
    sub.add_parser("info", help="List discovered domains and tasks")

    # stage0
    p_s0 = sub.add_parser("stage0", help="Run Stage-0 offline gates (no Docker/API key)")
    p_s0.add_argument("path", nargs="?", default=None,
                       help="Domain dir or task dir (default: auto-discover)")

    args = parser.parse_args()

    if args.version or args.command is None and not args.version:
        if args.version:
            return cmd_version(args, root)
        parser.print_help()
        return 0

    dispatch = {
        "info": cmd_info,
        "stage0": cmd_stage0,
    }
    fn = dispatch.get(args.command)
    if fn is None:
        parser.print_help()
        return 1

    sys.exit(fn(args, root))


if __name__ == "__main__":
    main()
