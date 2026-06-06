"""Performance regression models (Step 9).

Configurable thresholds via ``RegressionThresholds`` (a global tolerance plus
optional per-metric overrides). The comparison result for each metric carries
the old/new value, the signed delta, and a deterministic status.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RegressionStatus(str, Enum):
    IMPROVED = "improved"
    WITHIN_TOLERANCE = "within_tolerance"
    REGRESSION_DETECTED = "regression_detected"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class RegressionThresholds(BaseModel):
    """Configurable tolerances. A drop greater than the tolerance is a
    regression; a rise greater than the tolerance is an improvement; anything
    in between is within tolerance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    default_tolerance: float = Field(default=0.01, ge=0.0)
    per_metric: dict[str, float] = Field(default_factory=dict)

    def tolerance_for(self, metric: str) -> float:
        return self.per_metric.get(metric, self.default_tolerance)


class MetricComparison(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str
    old_value: float
    new_value: float
    delta: float
    status: RegressionStatus
    rationale: str = ""