"""The Regression Gate (Critical Issue #2).

Turns informational regression evidence into a deterministic control that
influences decisions. A benchmark comparison can carry regressions of differing
magnitude; the gate classifies the *worst* regression and emits a state:

    no regression          -> PASS           (proceed)
    minor regression       -> MANUAL_REVIEW   (human review required)
    major regression       -> BLOCKED         (revalidation blocked)

"Major" is an explicit, configurable degradation threshold (absolute drop),
optionally overridden per metric. There is no scoring and no inference: a
regression is major iff its degradation meets the configured threshold.

The gate feeds the recommendation, the governance state, and the binder
lifecycle, so a major benchmark degradation cannot be silently approved.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .models import MetricComparison, RegressionStatus


class GateState(str, Enum):
    PASS = "pass"
    MANUAL_REVIEW = "manual_review"
    BLOCKED = "blocked"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class RegressionGateThresholds(BaseModel):
    """Configurable degradation thresholds for the gate.

    A *regression* (per the detector) is *major* when the absolute degradation
    (|delta| for a decreased metric) is at least ``major_degradation`` (or the
    per-metric override). Otherwise the regression is *minor*.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    major_degradation: float = Field(default=0.05, ge=0.0)
    per_metric: dict[str, float] = Field(default_factory=dict)

    def major_threshold_for(self, metric: str) -> float:
        return self.per_metric.get(metric, self.major_degradation)


class RegressionGate(BaseModel):
    """Deterministic gate decision over a set of metric comparisons."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: GateState
    severity: str  # "none" | "minor" | "major"
    rationale: str
    blocking_metrics: tuple[str, ...] = ()
    review_metrics: tuple[str, ...] = ()
    evaluated: bool = True

    @property
    def blocks_finalization(self) -> bool:
        return self.state is GateState.BLOCKED


def evaluate_gate(
    comparisons: list[MetricComparison] | tuple[MetricComparison, ...],
    thresholds: RegressionGateThresholds | None = None,
) -> RegressionGate:
    """Classify a benchmark comparison into a deterministic gate decision."""
    thresholds = thresholds or RegressionGateThresholds()

    if not comparisons:
        return RegressionGate(
            state=GateState.PASS,
            severity="none",
            rationale="No benchmark comparison supplied; regression gate not "
            "triggered.",
            evaluated=False,
        )

    blocking: list[str] = []
    review: list[str] = []
    for c in comparisons:
        if c.status is not RegressionStatus.REGRESSION_DETECTED:
            continue
        degradation = abs(c.delta)
        if degradation >= thresholds.major_threshold_for(c.metric):
            blocking.append(c.metric)
        else:
            review.append(c.metric)

    blocking.sort()
    review.sort()

    if blocking:
        return RegressionGate(
            state=GateState.BLOCKED,
            severity="major",
            rationale=(
                "Major performance regression in "
                f"{', '.join(blocking)}; revalidation is blocked until resolved "
                "or explicitly overridden by the laboratory director."
            ),
            blocking_metrics=tuple(blocking),
            review_metrics=tuple(review),
        )
    if review:
        return RegressionGate(
            state=GateState.MANUAL_REVIEW,
            severity="minor",
            rationale=(
                "Minor performance regression in "
                f"{', '.join(review)}; manual review required before approval."
            ),
            review_metrics=tuple(review),
        )
    return RegressionGate(
        state=GateState.PASS,
        severity="none",
        rationale="No performance regression detected; benchmarks within "
        "tolerance or improved.",
    )
