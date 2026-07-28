"""Probe scoring ladder {0.0, 0.40, 1.0} and verdict vocabulary."""
from __future__ import annotations

from priorlock.probes import BY_ID
from priorlock.probes.base import FAMILIAR_BASELINE


def test_ladder_bypassed_prior_locked_override():
    probe = BY_ID["dedupe_keep_policy"]

    score, verdict = probe.score(invoked=False, supplied={}, output=None)
    assert (score, verdict) == (0.0, "bypassed")

    score, verdict = probe.score(
        invoked=True,
        supplied={},
        output=probe.familiar_output,
    )
    assert score == FAMILIAR_BASELINE == 0.40
    assert verdict == "prior_locked"

    score, verdict = probe.score(
        invoked=True,
        supplied=dict(probe.gold_kwargs),
        output=probe.gold_output,
    )
    assert (score, verdict) == (1.0, "override")
