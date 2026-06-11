"""Severity model for change-magnitude intelligence.

``ChangeSeverity`` augments a detected change with a deterministic, explainable
severity level and the underlying version magnitude. It is a separate layer
(like impact) keyed by ``change_id`` so the diff engine stays purely
descriptive while severity policy stays auditable and editable in one place.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value

    @property
    def rank(self) -> int:
        return _RANK[self]


_RANK: dict[Severity, int] = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def max_severity(a: Severity, b: Severity) -> Severity:
    return a if a.rank >= b.rank else b


class VersionMagnitude(str, Enum):
    NONE = "none"
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"
    UNKNOWN = "unknown"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class ChangeSeverity(BaseModel):
    """Deterministic severity assessment for a single detected change."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str
    severity: Severity
    version_magnitude: VersionMagnitude = VersionMagnitude.NONE
    rationale: str
    reasons: tuple[str, ...] = ()
