"""Reportable variant delta models (Step 10, MVP).

Structured objects only — no VCF parsing and no annotation pipeline. A
reportable variant is identified by an opaque string (e.g., 'BRCA1
c.68_69delAG') with a detection status; the delta records how that status
changed between two pipelines.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class VariantStatus(str, Enum):
    DETECTED = "detected"
    MISSING = "missing"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class DeltaType(str, Enum):
    UNCHANGED = "unchanged"
    GAINED = "gained"
    LOST = "lost"
    STATUS_CHANGED = "status_changed"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class ReportableVariantObservation(BaseModel):
    """A reportable variant and whether a pipeline reported it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variant: str
    status: VariantStatus = VariantStatus.DETECTED


class ReportableVariantDelta(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    variant: str
    old_status: VariantStatus
    new_status: VariantStatus
    delta_type: DeltaType