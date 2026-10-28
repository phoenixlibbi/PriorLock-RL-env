"""Probe archetype contract.

A *probe* is a pre-calibrated, domain-agnostic unit that measures whether an
agent overrode a memorized prior. Probes are injected automatically into any
Harbor / Terminal-Bench task — the task author never writes one.

Design invariant (the whole point of this module)
-------------------------------------------------
Every probe yields exactly three scores by *construction*, not by empirical luck:

    1.00  agent read the shipped docs and acted on them
    0.40  agent applied its memorized prior (confident but wrong)
    0.00  agent bypassed / tampered / crashed / produced garbage

Because the 0.40 rung is structural, the familiar baseline no longer needs to be
re-derived per domain. Stage-0 G2 becomes a *tautology check* on the harness
rather than a per-domain calibration exercise. This is what makes PriorLock
runnable on an arbitrary task with zero author effort.

Three probe families
--------------------
``default_flip``
    A keyword argument exists in both versions, but the *default value* was
    inverted. A prior-locked agent omits the argument and inherits the wrong
    default. A doc-reading agent passes it explicitly.
    Signal source: **call arguments** (un-fakeable, observed via signature bind).

``value_remap``
    The keyword argument and its accepted values both still exist, but one
    value's *meaning* was reassigned. A prior-locked agent passes the value that
    used to be correct. A doc-reading agent passes the new one.
    Signal source: **call arguments**.

``result_shape``
    No argument changed; the *return shape* did (extra tied rows, sentinel
    ``None`` instead of ``0``, always-a-list instead of a bare record). A
    prior-locked agent "sanity-corrects" the result back to what it expects.
    Signal source: **output values**.

Why call-argument grading matters
---------------------------------
Output diffing alone is weak: an agent can stumble onto the right answer, and a
reward hacker can pattern-match the expected shape. Call-argument grading asks a
question with no accidental answers — *did you pass ``keep="first"`` or not?*
The observation is made by the verifier re-executing the agent's submission
against a pristine, verifier-owned copy of the library with instrumented
functions. Nothing the agent writes to disk participates in scoring.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# The structural familiar baseline. Do not change without re-deriving Stage-0 G2.
FAMILIAR_BASELINE = 0.40

FAMILIES = ("default_flip", "value_remap", "result_shape")

CATEGORIES = (
    "collection",   # grouping, dedupe, ordering, slicing
    "numeric",      # rounding, aggregation, normalisation
    "text",         # casing, padding, tokenising
    "temporal",     # date parsing, timezone handling
    "mapping",      # dict merge, key normalisation, indexing
)


@dataclass(frozen=True)
class Probe:
    """One pre-calibrated prior-override measurement.

    Everything the injection engine needs to (a) emit a self-contained synthetic
    library function, (b) document it honestly in-container, (c) state a task
    requirement that the familiar default fails, and (d) grade the result — with
    no reference back to PriorLock at runtime.
    """

    # ── identity ──────────────────────────────────────────────────────────────
    id: str
    family: str
    category: str
    summary: str

    # ── generated library surface ─────────────────────────────────────────────
    fn: str
    signature: str
    impl: str                       # module-level `def` source, installed (v2) semantics
    api_doc: str                    # goes into docs/<lib>-api.md
    changelog: str                  # goes into docs/<lib>-CHANGELOG.md (honest, complete)

    # ── the discriminating call ───────────────────────────────────────────────
    param: str | None               # kwarg carrying the changed semantics; None for result_shape
    gold_kwargs: dict               # what a doc-reading agent must supply
    familiar_kwargs: dict           # what a prior-locked agent supplies (often {})
    familiar_behaviour: str         # human-readable: what the prior expects
    installed_behaviour: str        # human-readable: what actually ships

    # ── the task requirement ──────────────────────────────────────────────────
    task_clause: str                # appended to instruction.md; states WHAT, never HOW
    output_key: str

    # ── data + oracle ─────────────────────────────────────────────────────────
    input_payload: Any
    gold_output: Any
    familiar_output: Any

    # ── metadata ──────────────────────────────────────────────────────────────
    tags: tuple[str, ...] = ()
    weight: float = 1.0
    domain: str = "coding"              # which cartridge owns this probe
    level: int = 1                      # L1=atomic, L2=coupled, L3=workflow, L4=evolving
    dependencies: tuple[str, ...] = ()  # ids of probes that must co-occur (L2+)

    # ── IRT-based difficulty tiering ─────────────────────────────────────────
    # Estimated a priori. Updated empirically by `priorlock calibrate ingest`.
    # Used by select_probes() for model-adaptive selection.
    difficulty: float = 0.5             # 0=easy, 1=hard. Easy probes test obvious
                                        # changes; hard probes test subtle ones
    is_counterfactual: bool = False     # True for no-change control probes

    # ── validation ────────────────────────────────────────────────────────────
    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError(f"{self.id}: unknown family {self.family!r}")
        if not self.category:
            raise ValueError(f"{self.id}: category must be non-empty")
        if self.family == "result_shape":
            if self.gold_kwargs or self.familiar_kwargs:
                raise ValueError(f"{self.id}: result_shape probes take no discriminating kwargs")
        else:
            if not self.param:
                raise ValueError(f"{self.id}: {self.family} requires a param")
            if self.gold_kwargs == self.familiar_kwargs:
                raise ValueError(f"{self.id}: gold and familiar calls are identical")
        if self.gold_output == self.familiar_output:
            raise ValueError(f"{self.id}: gold and familiar outputs are identical — no signal")
        if f"def {self.fn}(" not in self.impl:
            raise ValueError(f"{self.id}: impl does not define {self.fn}()")

    # ── grading ───────────────────────────────────────────────────────────────
    def call_is_gold(self, supplied: dict) -> bool:
        """True if the observed explicitly-supplied arguments match gold semantics.

        ``supplied`` comes from ``inspect.Signature.bind(...).arguments`` on the
        pristine function, so it contains *only* arguments the agent actually
        passed — defaults are absent. That distinction is the measurement.
        """
        if self.family == "result_shape":
            return True                      # invocation alone is the requirement
        assert self.param is not None
        want = self.gold_kwargs[self.param]
        return self.param in supplied and supplied[self.param] == want

    def call_is_familiar(self, supplied: dict) -> bool:
        """True if the observed call reflects the memorized prior."""
        if self.family == "result_shape":
            return False
        assert self.param is not None
        if self.family == "default_flip":
            # prior-locked agents omit the arg entirely, or pass the installed default
            return self.param not in supplied or supplied[self.param] != self.gold_kwargs[self.param]
        # value_remap: prior-locked agents pass the value that *used* to be right
        return supplied.get(self.param) == self.familiar_kwargs.get(self.param)

    def score(self, *, invoked: bool, supplied: dict, output: Any) -> tuple[float, str]:
        """Return ``(score, verdict)`` on the {0.0, 0.40, 1.0} ladder."""
        if not invoked:
            return 0.0, "bypassed"
        if output == self.gold_output and self.call_is_gold(supplied):
            return 1.0, "override"
        if output == self.familiar_output:
            return FAMILIAR_BASELINE, "prior_locked"
        if self.call_is_gold(supplied):
            # right call, mangled post-processing — partial credit is not on the ladder
            return 0.0, "correct_call_bad_output"
        return 0.0, "incorrect"

    def score_calls(self, *, invocations: list[dict], output: Any) -> tuple[float, str]:
        """Score every recorded call together, with the same rule as the grader.

        All calls must agree on the probed argument (spraying values scores 0),
        full credit needs the documented call and the right output, and a right
        output reached any other way earns the baseline, never more.
        """
        if not invocations:
            return 0.0, "bypassed"
        if self.family != "result_shape":
            values = {repr(s.get(self.param, "<default>")) for s in invocations}
            if len(values) > 1:
                return 0.0, "inconsistent_calls"
        gold_call = all(self.call_is_gold(s) for s in invocations)
        if output == self.gold_output and gold_call:
            return 1.0, "override"
        if output == self.familiar_output:
            return FAMILIAR_BASELINE, "prior_locked"
        if output == self.gold_output:
            return FAMILIAR_BASELINE, "correct_output_other_call"
        if gold_call:
            return 0.0, "correct_call_bad_output"
        return 0.0, "incorrect"

    # ── serialisation (embedded verbatim into the generated grader) ────────────
    def to_grader_dict(self) -> dict:
        return {
            "id": self.id,
            "family": self.family,
            "category": self.category,
            "fn": self.fn,
            "param": self.param,
            "gold_kwargs": self.gold_kwargs,
            "familiar_kwargs": self.familiar_kwargs,
            "output_key": self.output_key,
            "gold_output": self.gold_output,
            "familiar_output": self.familiar_output,
            "weight": self.weight,
        }

    def to_manifest_dict(self) -> dict:
        d = self.to_grader_dict()
        d.update({
            "summary": self.summary,
            "familiar_behaviour": self.familiar_behaviour,
            "installed_behaviour": self.installed_behaviour,
            "tags": list(self.tags),
        })
        return d


# ── verdict vocabulary, shared by grader / gates / calibration ────────────────

VERDICTS = {
    "override":                 "read the shipped docs and acted on them",
    "prior_locked":             "applied the memorized prior — confident but wrong",
    "bypassed":                 "never called the library function",
    "tampered":                 "modified the library source",
    "correct_call_bad_output":  "called correctly but mangled the result",
    "incorrect":                "output matches neither gold nor familiar",
    "crashed":                  "solution raised before producing output",
    "absent":                   "no probe solution submitted",
}


def gap_score(probe_scores: list[float], weights: list[float] | None = None) -> float:
    """Weighted mean of per-probe scores. Empty -> 0.0."""
    if not probe_scores:
        return 0.0
    w = weights or [1.0] * len(probe_scores)
    total = sum(w)
    if total <= 0:
        return 0.0
    return round(sum(s * wi for s, wi in zip(probe_scores, w)) / total, 4)


def composite_reward(task_score: float, gap: float, w_task: float = 0.5,
                     w_gap: float = 0.5) -> float:
    """Blend the native task reward with the prior-override reward."""
    denom = w_task + w_gap
    if denom <= 0:
        return 0.0
    return round((task_score * w_task + gap * w_gap) / denom, 4)


def dumps(obj: Any) -> str:
    """Deterministic JSON for hashing and for embedding in generated files."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))
