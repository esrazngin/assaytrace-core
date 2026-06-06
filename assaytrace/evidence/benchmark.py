"""Standardized benchmark evidence schema (Part 1).

A richer, canonical benchmark model than the original MVP ``GiabEvidencePackage``:
SNV / INDEL / (optional) CNV metric triplets (precision, recall, f1) plus full
provenance metadata. It integrates with the existing evidence module and, like
``GiabEvidencePackage``, exposes ``as_metric_map()`` so the regression detector
consumes it with no changes.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

_PROPORTION = dict(ge=0.0, le=1.0)


class MetricTriplet(BaseModel):
    """Precision / recall / F1 for one variant class."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    precision: float = Field(**_PROPORTION)
    recall: float = Field(**_PROPORTION)
    f1: float = Field(**_PROPORTION)

    @model_validator(mode="after")
    def _f1_is_consistent(self) -> "MetricTriplet":
        # Eğer hem precision hem recall 0 ise, sıfıra bölünme hatasını önlemek için f1'i 0 kabul ediyoruz
        if self.precision + self.recall == 0:
            expected_f1 = 0.0
        else:
            expected_f1 = (
                2 * self.precision * self.recall
            ) / (self.precision + self.recall)

        if abs(self.f1 - expected_f1) > 0.02:
            raise ValueError(
                "f1 is inconsistent with precision and recall"
            )
        return self


class BenchmarkPackage(BaseModel):
    """A standardized benchmark evidence package (e.g., a GIAB comparison)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sample_id: str = Field(description="Sample identifier, e.g. 'HG002'.")
    benchmark_name: str = Field(description="Benchmark name, e.g. 'GIAB'.")
    benchmark_version: str = Field(description="Benchmark release, e.g. 'v4.2.1'.")
    truthset: str = Field(description="Truth-set identifier used for comparison.")
    run_date: date

    snv: MetricTriplet
    indel: MetricTriplet
    cnv: MetricTriplet | None = None

    def as_metric_map(self) -> dict[str, float]:
        """Flat metric map consumed by the performance regression detector.

        Keys are '<class>_<metric>' (e.g. 'snv_recall'). CNV keys are present
        only when CNV metrics are supplied.
        """
        out: dict[str, float] = {
            "snv_precision": self.snv.precision,
            "snv_recall": self.snv.recall,
            "snv_f1": self.snv.f1,
            "indel_precision": self.indel.precision,
            "indel_recall": self.indel.recall,
            "indel_f1": self.indel.f1,
        }
        if self.cnv is not None:
            out.update(
                {
                    "cnv_precision": self.cnv.precision,
                    "cnv_recall": self.cnv.recall,
                    "cnv_f1": self.cnv.f1,
                }
            )
        return out