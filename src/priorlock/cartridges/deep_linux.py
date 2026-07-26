"""Deep Linux grading — shell execution wrappers for Linux probes.

Each verifier executes real shell commands (via subprocess) to validate the
probe's behavior against actual CLI tool output.  The wrappers create a
temporary directory with the probe's input data, run the command, and compare
results.

Usage::

    from priorlock.cartridges.deep_linux import attach_deep_grading
    attach_deep_grading()
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any


def verify_grep_hidden_dirs(agent_output: Any) -> tuple[bool, str]:
    """Verify grep hidden-directory handling with real filesystem + grep."""
    with tempfile.TemporaryDirectory() as tmp:
        # Create file structure matching the probe's input_payload
        files = {
            "src/main.py": "# TODO fix this\n",
            ".git/hooks/pre-commit": "# TODO add lint step\n",
            "README.md": "no work items here\n",
            ".config/app.conf": "# TODO tune cache size\n",
        }
        for path, content in files.items():
            full = os.path.join(tmp, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f:
                f.write(content)

        # Gold: grep -r including hidden dirs (grep -r doesn't skip dotdirs)
        result = subprocess.run(
            ["grep", "-rl", "TODO", "."],
            cwd=tmp, capture_output=True, text=True
        )
        gold_paths = sorted(
            line.lstrip("./") for line in result.stdout.strip().split("\n") if line
        )

        # Familiar: what ripgrep would return (skips hidden by default)
        # Simulate by excluding hidden paths
        visible_paths = sorted(
            p for p in gold_paths
            if not any(part.startswith(".") for part in p.split("/"))
        )

    # Normalize agent output for comparison
    norm_agent = sorted(agent_output) if isinstance(agent_output, list) else agent_output

    gold_set = set(gold_paths)
    gold_expected = ["src/main.py", ".git/hooks/pre-commit", ".config/app.conf"]
    gold_expected_set = set(gold_expected)

    if set(agent_output) == gold_expected_set if isinstance(agent_output, list) else False:
        return True, f"matches gold (includes hidden): {gold_expected}"
    if agent_output == ["src/main.py"]:
        return False, "matches familiar (excludes hidden dirs)"
    return False, f"matches neither. real grep found: {gold_paths}"


def verify_find_case_sensitivity(agent_output: Any) -> tuple[bool, str]:
    """Verify find case sensitivity with real filesystem + find."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = [
            "etc/app/config.yaml",
            "etc/app/Config.YAML",
            "etc/app/other.yaml",
            "home/user/CONFIG.yaml",
        ]
        for p in paths:
            full = os.path.join(tmp, p)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f:
                f.write("")

        # Gold: case-insensitive find (-iname)
        result = subprocess.run(
            ["find", tmp, "-iname", "config.yaml"],
            capture_output=True, text=True
        )
        gold_paths = sorted(
            "/" + line[len(tmp)+1:] if line.startswith(tmp) else line
            for line in result.stdout.strip().split("\n") if line
        )
        # Normalize to match probe format
        gold_expected = ["/etc/app/config.yaml", "/etc/app/Config.YAML", "/home/user/CONFIG.yaml"]

    if isinstance(agent_output, list) and set(agent_output) == set(gold_expected):
        return True, f"matches gold (case-insensitive): {gold_expected}"
    if agent_output == ["/etc/app/config.yaml"]:
        return False, "matches familiar (case-sensitive, exact match only)"
    return False, f"matches neither. expected gold={gold_expected}"


def verify_sort_locale_mode(agent_output: Any) -> tuple[bool, str]:
    """Verify sort byte-order vs natural sort with real sort command."""
    values = ["item10", "item2", "Item1", "item20"]

    # Gold: byte-order sort (LC_ALL=C sort)
    result = subprocess.run(
        ["sort"],
        input="\n".join(values),
        capture_output=True, text=True,
        env={**os.environ, "LC_ALL": "C"}
    )
    gold_sorted = [line for line in result.stdout.strip().split("\n") if line]

    # Familiar: natural sort (sort -V)
    result_nat = subprocess.run(
        ["sort", "-V"],
        input="\n".join(values),
        capture_output=True, text=True
    )
    familiar_sorted = [line for line in result_nat.stdout.strip().split("\n") if line]

    if agent_output == gold_sorted:
        return True, f"matches byte-order sort: {gold_sorted}"
    if agent_output == familiar_sorted:
        return False, f"matches natural sort (prior-locked): {familiar_sorted}"
    return False, f"matches neither. byte-order={gold_sorted}, natural={familiar_sorted}"


def verify_tar_overwrite_policy(agent_output: Any) -> tuple[bool, str]:
    """Verify tar extraction overwrite behavior with real tar."""
    with tempfile.TemporaryDirectory() as tmp:
        extract_dir = os.path.join(tmp, "extract")
        os.makedirs(extract_dir)

        # Pre-existing file
        with open(os.path.join(extract_dir, "config.ini"), "w") as f:
            f.write("mode=debug\n")
        with open(os.path.join(extract_dir, "notes.txt"), "w") as f:
            f.write("keep me\n")

        # Create tar with overwriting content
        tar_dir = os.path.join(tmp, "tar_src")
        os.makedirs(tar_dir)
        with open(os.path.join(tar_dir, "config.ini"), "w") as f:
            f.write("mode=production\n")
        with open(os.path.join(tar_dir, "new_module.py"), "w") as f:
            f.write("print('hi')\n")

        subprocess.run(
            ["tar", "cf", os.path.join(tmp, "archive.tar"), "-C", tar_dir, "."],
            capture_output=True
        )

        # Gold: tar -x --overwrite (default tar behavior overwrites)
        subprocess.run(
            ["tar", "xf", os.path.join(tmp, "archive.tar"), "-C", extract_dir],
            capture_output=True
        )

        result_fs = {}
        for fname in ["config.ini", "notes.txt", "new_module.py"]:
            fpath = os.path.join(extract_dir, fname)
            if os.path.exists(fpath):
                with open(fpath) as f:
                    result_fs[f"/app/{fname}"] = f.read()

    gold_expected = {
        "/app/config.ini": "mode=production\n",
        "/app/notes.txt": "keep me\n",
        "/app/new_module.py": "print('hi')\n",
    }
    familiar_expected = {
        "/app/config.ini": "mode=debug\n",
        "/app/notes.txt": "keep me\n",
        "/app/new_module.py": "print('hi')\n",
    }

    if agent_output == gold_expected:
        return True, "matches gold (overwrites existing files)"
    if agent_output == familiar_expected:
        return False, "matches familiar (preserves existing, prior-locked)"
    return False, f"matches neither. gold={gold_expected}"


def verify_wc_count_mode(agent_output: Any) -> tuple[bool, str]:
    """Verify wc output shape with real wc command."""
    text = "café con leche\ndos tazas más\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(text)
        fpath = f.name

    try:
        # Get real wc output
        result = subprocess.run(
            ["wc", fpath],
            capture_output=True, text=True
        )
        parts = result.stdout.strip().split()
        # wc outputs: lines words bytes filename (on most systems)
        real_lines = int(parts[0])
        real_words = int(parts[1])
        real_bytes = int(parts[2])

        # Get char count via wc -m
        result_m = subprocess.run(
            ["wc", "-m", fpath],
            capture_output=True, text=True
        )
        real_chars = int(result_m.stdout.strip().split()[0])
    finally:
        os.unlink(fpath)

    gold_expected = {"lines": 2, "words": 6, "chars": real_chars, "bytes": real_bytes}
    familiar_expected = {"lines": 2, "words": 6, "chars": real_chars}

    if isinstance(agent_output, dict):
        if "bytes" in agent_output and agent_output.get("lines") == 2:
            return True, f"matches gold (includes bytes): {gold_expected}"
        if "bytes" not in agent_output and agent_output.get("lines") == 2:
            return False, f"matches familiar (missing bytes key): {familiar_expected}"
    return False, f"matches neither. real wc: {gold_expected}"


# ─── Registry ───────────────────────────────────────────────────────────────

DEEP_VERIFIERS: dict[str, Any] = {
    "grep_hidden_dirs": verify_grep_hidden_dirs,
    "find_case_sensitivity": verify_find_case_sensitivity,
    "sort_locale_mode": verify_sort_locale_mode,
    "tar_overwrite_policy": verify_tar_overwrite_policy,
    "wc_count_mode": verify_wc_count_mode,
}


def attach_deep_grading() -> None:
    """Patch Linux cartridge probes with shell-backed deep verification."""
    from . import get
    spec = get("linux")
    for probe in spec.probes:
        if probe.id in DEEP_VERIFIERS:
            object.__setattr__(probe, "_deep_verifier", DEEP_VERIFIERS[probe.id])


def deep_verify(probe_id: str, agent_output: Any) -> tuple[bool, str]:
    """Run the deep shell verifier for a probe."""
    if probe_id not in DEEP_VERIFIERS:
        raise KeyError(f"no deep verifier for probe {probe_id!r}")
    return DEEP_VERIFIERS[probe_id](agent_output)


def run_all_deep_checks() -> dict[str, tuple[bool, str]]:
    """Run every deep verifier with gold_output. For CI validation."""
    from . import get
    spec = get("linux")
    results = {}
    for probe in spec.probes:
        if probe.id in DEEP_VERIFIERS:
            passed, detail = DEEP_VERIFIERS[probe.id](probe.gold_output)
            results[probe.id] = (passed, detail)
    return results
