"""Reproducibility fingerprints and grader re-run helpers."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__


def _repo_root() -> Path:
    """Best-effort package / checkout root (cwd if not in a git tree)."""
    here = Path(__file__).resolve()
    # src/priorlock/repro.py → repo root two levels up when editable.
    candidate = here.parents[2]
    if (candidate / "pyproject.toml").is_file():
        return candidate
    return Path.cwd()


def probe_catalog_hash() -> str:
    """Stable digest of the coding-domain probe catalog ids + weights."""
    from .probes import ALL_PROBES

    blob = "\n".join(
        f"{p.id}:{p.family}:{p.weight}:{p.difficulty}" for p in ALL_PROBES
    ).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def git_commit(cwd: Path | None = None) -> str | None:
    root = cwd or _repo_root()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def build_fingerprint(
    *,
    task_id: str | None = None,
    wrap_seed: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect env identity needed to re-run the same offline checks."""
    fp: dict[str, Any] = {
        "priorlock_version": __version__,
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
        "git_commit": git_commit(),
        "probe_catalog_hash": probe_catalog_hash(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if task_id is not None:
        fp["task_id"] = task_id
    if wrap_seed is not None:
        fp["wrap_seed"] = wrap_seed
    if extra:
        fp.update(extra)
    return fp


def write_fingerprint(
    fingerprint: dict[str, Any] | None = None,
    *,
    out_dir: str | Path | None = None,
    **kwargs: Any,
) -> Path:
    """Write ``logs/repro/<timestamp>.json`` and return the path."""
    root = _repo_root()
    dest_dir = Path(out_dir) if out_dir else root / "logs" / "repro"
    dest_dir.mkdir(parents=True, exist_ok=True)
    fp = fingerprint or build_fingerprint(**kwargs)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = dest_dir / f"{stamp}.json"
    path.write_text(json.dumps(fp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def rerun_one_liner() -> str:
    """Command others need to re-run the same offline checks."""
    return 'export PYTHONHASHSEED=0 && pytest -q && priorlock repro'


def assert_reproducible_grade(
    task: str | Path,
    reference: str,
    *,
    n: int = 20,
    max_flaky_rate: float = 0.02,
) -> dict[str, Any]:
    """Re-grade ``reference`` ``n`` times; require identical gap + verdicts.

    Flaky-rate = fraction of runs that disagree with the first. Default bar is
    < 2% mismatches; tests assert 0.
    """
    from .evaluators import grade_probes

    first = grade_probes(task, reference=reference)
    first_gap = float(first.get("gap_score") or 0.0)
    first_verdicts = [
        (p.get("id"), p.get("verdict"), p.get("score"))
        for p in (first.get("probes") or [])
    ]

    mismatches = 0
    for _ in range(n - 1):
        again = grade_probes(task, reference=reference)
        gap = float(again.get("gap_score") or 0.0)
        verdicts = [
            (p.get("id"), p.get("verdict"), p.get("score"))
            for p in (again.get("probes") or [])
        ]
        if gap != first_gap or verdicts != first_verdicts:
            mismatches += 1

    flaky_rate = mismatches / n if n else 0.0
    if flaky_rate >= max_flaky_rate:
        raise AssertionError(
            f"grader flaky-rate {flaky_rate:.4f} >= {max_flaky_rate} "
            f"({mismatches}/{n} mismatches for reference={reference!r})"
        )
    return {
        "reference": reference,
        "n": n,
        "gap_score": first_gap,
        "verdicts": first_verdicts,
        "mismatches": mismatches,
        "flaky_rate": flaky_rate,
    }
