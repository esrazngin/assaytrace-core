"""Operational impact estimation.

Translates each revalidation decision into the concrete operational burden a
laboratory should plan for: revalidation scope, expected benchmark runs,
estimated effort, and estimated review time. Every value is a deterministic
lookup keyed by ``RevalidationType`` — no AI, no free text, fully traceable to
the table below. Editing the table changes the estimates.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .decision.models import RevalidationType


class OperationalImpact(BaseModel):
    """Deterministic operational burden for a single decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str
    revalidation_scope: str
    expected_benchmark_runs: int
    estimated_effort: str          # None / Low / Medium / High
    estimated_review_time: str
    affected_claims: int


# RevalidationType -> (scope label, benchmark runs, effort, review time)
IMPACT_BY_REVALIDATION: dict[RevalidationType, tuple[str, int, str, str]] = {
    RevalidationType.NONE: ("None", 0, "None", "None"),
    RevalidationType.DOCUMENTATION_UPDATE: ("Documentation", 0, "Low", "< 1 day"),
    RevalidationType.INFRASTRUCTURE_VERIFICATION: ("Infrastructure", 0, "Low", "1 day"),
    RevalidationType.QC_VERIFICATION: ("QC verification", 0, "Low", "1 day"),
    RevalidationType.CLASSIFICATION_CONCORDANCE_REVIEW: ("Classification review", 0, "Medium", "2-3 days"),
    RevalidationType.TARGETED_ANALYTICAL: ("Targeted", 1, "Low", "1 day"),
    RevalidationType.SCOPE_REVIEW_AND_TARGETED: ("Scope + Targeted", 1, "Medium", "2-3 days"),
    RevalidationType.FULL_OR_TARGETED_ANALYTICAL: ("Full or Targeted", 1, "Medium", "3-5 days"),
    RevalidationType.FULL_ANALYTICAL: ("Full", 2, "High", "1-2 weeks"),
}

_DEFAULT_IMPACT = ("Targeted", 1, "Low", "1 day")

EFFORT_RANK: dict[str, int] = {"None": 0, "Low": 1, "Medium": 2, "High": 3}


def estimate(change_id: str, rt: RevalidationType, affected_claims: int) -> OperationalImpact:
    scope, runs, effort, review = IMPACT_BY_REVALIDATION.get(rt, _DEFAULT_IMPACT)
    return OperationalImpact(
        change_id=change_id,
        revalidation_scope=scope,
        expected_benchmark_runs=runs,
        estimated_effort=effort,
        estimated_review_time=review,
        affected_claims=affected_claims,
    )
