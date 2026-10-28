"""Run a generated probe grader and read its report safely.

A solution being graded can, on Linux and as the same user, write into the
grader's stdout through ``/proc/<pid>/fd/1``. So the caller hands the grader a
fresh random nonce on stdin (read before the solution starts, never visible to
it) and accepts only the report line that carries that nonce.
"""
from __future__ import annotations

import json
import secrets
import subprocess


def run_grader(cmd: list[str], *, timeout: float, cwd: str | None = None,
               env: dict | None = None) -> tuple[dict | None, subprocess.CompletedProcess]:
    """Run *cmd* (a probe_grade.py invocation) and return (report, process).

    The report is ``None`` when no line carries the nonce.
    """
    nonce = secrets.token_hex(16)
    proc = subprocess.run(cmd + ["--nonce-stdin"], input=nonce + "\n",
                          capture_output=True, text=True, timeout=timeout,
                          cwd=cwd, env=env)
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("nonce") == nonce:
            obj.pop("nonce", None)
            return obj, proc
    return None, proc
