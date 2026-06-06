"""GIAB-backed evidence package models (Step 8, MVP).

Structured evidence only — no GIAB execution and no hap.py. The model captures
a benchmark comparison result so that downstream regression detection can run
on structured data now, while leaving a clear seam for real benchmark
integration later (a future parser can populate the same model from hap.py
output).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

_PROPORTION = dict(ge=0.0, le=1.0)


class GiabEvidencePackage(BaseModel):
    """A single benchmark comparison for one GIAB sample."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sample: str = Field(default="HG002", description="GIAB sample identifier.")
    snv_precision: float = Field(**_PROPORTION)
    snv_recall: float = Field(**_PROPORTION)
    indel_precision: float = Field(**_PROPORTION)
    indel_recall: float = Field(**_PROPORTION)
    comparison_date: date
    evidence_source: str = Field(
        description="Provenance of the metrics (e.g., tool/version or document ID)."
    )

    def as_metric_map(self) -> dict[str, float]:
        """Flat metric map consumed by the performance regression detector."""
        return {
            "snv_precision": self.snv_precision,
            "snv_recall": self.snv_recall,
            "indel_precision": self.indel_precision,
            "indel_recall": self.indel_recall,
        }