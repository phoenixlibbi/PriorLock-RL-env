"""Empirical probe calibration.

What calibration is *not* for
----------------------------
It does not establish the 0.40 baseline. That number is structural — it falls
out of the scoring ladder in ``probes.base`` and is verified offline by Stage-0
gate G2 for every wrapped task. This is the single biggest difference from the
hand-authored deviation model: there, 0.40 had to be re-derived per domain by
the task author, and a mis-derived value silently invalidated the measurement.

What calibration *is* for
-------------------------
Measuring how **informative** each probe is against a given model. A probe that
every model overrides is a ceiling; a probe no model ever overrides is a floor.
Neither tells you much. The useful probes sit in the middle, and which ones
those are drifts as models improve.

Two numbers per (probe, model):

``discrimination``
    Fraction of runs that produced an unambiguous verdict — ``override`` or
    ``prior_locked``. Low discrimination means the probe is confusing agents
    rather than measuring them, and it should be demoted in selection.

``familiar_rate``
    Of those unambiguous runs, the fraction that were ``prior_locked``. This is
    the prior-lock rate: how often the model applied its memorized default in the
    face of documentation saying otherwise. **This is the headline number.**

Ingest paths
------------
``ingest_trial_dir``   read Harbor trial output directories
``ingest_reports``     read raw probe grader JSON
Both feed ``update_calibration``, which merges counts into ``calibration.json``.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .probes import BY_ID, load_calibration, save_calibration

UNAMBIGUOUS = {"override", "prior_locked"}


@dataclass
class Tally:
    runs: int = 0
    override: int = 0
    prior_locked: int = 0
    bypassed: int = 0
    incorrect: int = 0
    other: int = 0

    def add(self, verdict: str) -> None:
        self.runs += 1
        if verdict == "override":
            self.override += 1
        elif verdict == "prior_locked":
            self.prior_locked += 1
        elif verdict == "bypassed":
            self.bypassed += 1
        elif verdict in ("incorrect", "correct_call_bad_output"):
            self.incorrect += 1
        else:
            self.other += 1

    @property
    def unambiguous(self) -> int:
        return self.override + self.prior_locked

    @property
    def discrimination(self) -> float:
        return round(self.unambiguous / self.runs, 4) if self.runs else 0.0

    @property
    def familiar_rate(self) -> float:
        return round(self.prior_locked / self.unambiguous, 4) if self.unambiguous else 0.0

    def merge(self, other: "Tally") -> "Tally":
        return Tally(
            runs=self.runs + other.runs,
            override=self.override + other.override,
            prior_locked=self.prior_locked + other.prior_locked,
            bypassed=self.bypassed + other.bypassed,
            incorrect=self.incorrect + other.incorrect,
            other=self.other + other.other,
        )

    def to_dict(self) -> dict:
        return {
            "runs": self.runs,
            "override": self.override,
            "prior_locked": self.prior_locked,
            "bypassed": self.bypassed,
            "incorrect": self.incorrect,
            "other": self.other,
            "discrimination": self.discrimination,
            "familiar_rate": self.familiar_rate,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Tally":
        return cls(
            runs=int(d.get("runs", 0)),
            override=int(d.get("override", 0)),
            prior_locked=int(d.get("prior_locked", 0)),
            bypassed=int(d.get("bypassed", 0)),
            incorrect=int(d.get("incorrect", 0)),
            other=int(d.get("other", 0)),
        )


@dataclass
class Observation:
    """One graded run of one wrapped task by one model."""
    model: str
    task_id: str
    gap_score: float
    verdicts: dict[str, str] = field(default_factory=dict)   # probe_id -> verdict
    flags: list[str] = field(default_factory=list)


# ═════════════════════════════════════════════════════════════════════════════
#  Ingest
# ═════════════════════════════════════════════════════════════════════════════

def ingest_reports(paths: list[str | Path], model: str,
                   task_id: str = "unknown") -> list[Observation]:
    """Read raw probe-grader JSON files."""
    out: list[Observation] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        out.append(Observation(
            model=model,
            task_id=data.get("task_id", task_id),
            gap_score=float(data.get("gap_score", 0.0)),
            verdicts={pr["id"]: pr["verdict"] for pr in data.get("probes", [])},
            flags=list(data.get("flags", [])),
        ))
    return out


def ingest_trial_dir(trials_dir: str | Path, model: str | None = None) -> list[Observation]:
    """Walk a Harbor ``trials/`` tree and collect every probe report found.

    Looks for ``verifier/probe_details.json`` (written by the composite verifier)
    and falls back to ``verifier/priorlock_summary.json``. The model name is read
    from the trial's ``config.json`` when not supplied.
    """
    root = Path(trials_dir)
    out: list[Observation] = []
    if not root.is_dir():
        return out

    seen = set()
    for marker in sorted(list(root.rglob("verifier/probe_details.json"))
                         + list(root.rglob("verifier/priorlock_summary.json"))):
        trial = marker.parent.parent
        if trial in seen:
            continue
        seen.add(trial)
        detail = trial / "verifier" / "probe_details.json"
        summary = trial / "verifier" / "priorlock_summary.json"
        config = trial / "config.json"

        run_model = model
        if run_model is None and config.is_file():
            try:
                cfg = json.loads(config.read_text())
                run_model = (
                    cfg.get("model")
                    or cfg.get("model_name")
                    or (cfg.get("agent") or {}).get("model")
                    or "unknown"
                )
            except json.JSONDecodeError:
                run_model = "unknown"
        run_model = run_model or "unknown"

        task_id = trial.name.split("__")[0]

        if detail.is_file():
            try:
                data = json.loads(detail.read_text())
            except json.JSONDecodeError:
                continue
            out.append(Observation(
                model=run_model, task_id=task_id,
                gap_score=float(data.get("gap_score", 0.0)),
                verdicts={p["id"]: p["verdict"] for p in data.get("probes", [])},
                flags=list(data.get("flags", [])),
            ))
        elif summary.is_file():
            try:
                data = json.loads(summary.read_text())
            except json.JSONDecodeError:
                continue
            out.append(Observation(
                model=run_model, task_id=task_id,
                gap_score=float(data.get("components", {}).get("gap_score", 0.0)),
                verdicts={p["id"]: p["verdict"] for p in data.get("probes", [])},
                flags=list(data.get("flags", [])),
            ))
    return out


# ═════════════════════════════════════════════════════════════════════════════
#  Aggregate + persist
# ═════════════════════════════════════════════════════════════════════════════

def aggregate(observations: list[Observation]) -> tuple[dict, dict]:
    """Return ``(per_probe, per_model_per_probe)`` tallies."""
    per_probe: dict[str, Tally] = defaultdict(Tally)
    per_model: dict[str, dict[str, Tally]] = defaultdict(lambda: defaultdict(Tally))
    for obs in observations:
        for pid, verdict in obs.verdicts.items():
            per_probe[pid].add(verdict)
            per_model[obs.model][pid].add(verdict)
    return per_probe, per_model


def update_calibration(observations: list[Observation], merge: bool = True) -> dict:
    """Merge observations into ``calibration.json`` and return the new document."""
    data = load_calibration() if merge else {"schema": 1, "probes": {}, "models": {}}
    data.setdefault("probes", {})
    data.setdefault("models", {})

    per_probe, per_model = aggregate(observations)

    for pid, tally in per_probe.items():
        prior = Tally.from_dict(data["probes"].get(pid, {})) if merge else Tally()
        combined = prior.merge(tally)
        entry = combined.to_dict()
        probe = BY_ID.get(pid)
        if probe:
            entry["family"] = probe.family
            entry["category"] = probe.category
        data["probes"][pid] = entry

    for model, probes in per_model.items():
        bucket = data["models"].setdefault(model, {})
        for pid, tally in probes.items():
            prior = Tally.from_dict(bucket.get(pid, {})) if merge else Tally()
            bucket[pid] = prior.merge(tally).to_dict()

    data["note"] = load_calibration().get("note", "")
    save_calibration(data)
    return data


# ═════════════════════════════════════════════════════════════════════════════
#  Reporting
# ═════════════════════════════════════════════════════════════════════════════

def report(model: str | None = None) -> str:
    data = load_calibration()
    if model:
        table = data.get("models", {}).get(model, {})
        header = f"Calibration · {model}"
    else:
        table = data.get("probes", {})
        header = "Calibration · all models"

    if not table:
        return (f"{header}\n\nNo calibration data yet.\n\n"
                "Run wrapped tasks through Harbor, then:\n"
                "  priorlock calibrate ingest <trials-dir> --model <name>\n\n"
                "The 0.40 baseline does not depend on this — it is verified "
                "offline by Stage-0 G2 for every wrapped task.")

    rows = sorted(table.items(), key=lambda kv: -float(kv[1].get("familiar_rate", 0)))
    width = max(len(k) for k, _ in rows)
    lines = [
        header, "",
        f"{'PROBE'.ljust(width)}  RUNS  OVERRIDE  LOCKED  BYPASS  DISCRIM  PRIOR-LOCK RATE",
        f"{'-' * width}  ----  --------  ------  ------  -------  ---------------",
    ]
    for pid, e in rows:
        lines.append(
            f"{pid.ljust(width)}  {e.get('runs', 0):>4}  {e.get('override', 0):>8}  "
            f"{e.get('prior_locked', 0):>6}  {e.get('bypassed', 0):>6}  "
            f"{float(e.get('discrimination', 0)):>7.2f}  "
            f"{float(e.get('familiar_rate', 0)):>15.2f}"
        )

    total_runs = sum(int(e.get("runs", 0)) for _, e in rows)
    locked = sum(int(e.get("prior_locked", 0)) for _, e in rows)
    unamb = sum(int(e.get("override", 0)) + int(e.get("prior_locked", 0)) for _, e in rows)
    lines += [
        "",
        f"overall prior-lock rate: {locked / unamb:.3f}" if unamb else "overall: n/a",
        f"probe-observations: {total_runs}",
        "",
        "discrimination < 0.60 → probe is confusing agents, demote it in selection",
        "prior-lock rate  > 0.90 → probe is a floor for this model, low information",
        "prior-lock rate  < 0.10 → probe is a ceiling for this model, low information",
    ]
    return "\n".join(lines)


def recommended_probes(model: str, top: int = 5) -> list[str]:
    """Probes with the most information for a given model.

    Prefers high discrimination and a prior-lock rate near 0.5 — probes that
    genuinely split the model's behaviour rather than always going one way.
    """
    data = load_calibration().get("models", {}).get(model, {})
    scored = []
    for pid, e in data.items():
        if pid not in BY_ID:
            continue
        disc = float(e.get("discrimination", 0.0))
        rate = float(e.get("familiar_rate", 0.0))
        runs = int(e.get("runs", 0))
        if runs < 3:
            continue
        information = disc * (1.0 - abs(rate - 0.5) * 2.0)
        scored.append((information, pid))
    scored.sort(reverse=True)
    return [pid for _, pid in scored[:top]]
