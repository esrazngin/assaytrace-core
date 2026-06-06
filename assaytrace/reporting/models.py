"""Audit-ready validation binder — structured report model (Step 12).

The ``AuditBinder`` is the deterministic, fully serializable "PDF-ready" model
that aggregates every analysis output into one change-control artifact. The
HTML generator (``reporting.html``) renders this model; a future PDF renderer
would consume the same model unchanged.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..claims_impact.models import ClaimImpactRecord
from ..decision.models import DecisionRecord
from ..decision.no_revalidation import NoRevalidationRecord
from ..diff.models import ChangeRecord
from ..evidence.benchmark import BenchmarkPackage
from ..evidence.models import GiabEvidencePackage
from ..impact.models import ImpactRecord
from ..regression.models import MetricComparison
from ..reportable.classification import VariantClassificationDelta
from ..reportable.models import ReportableVariantDelta

DISCLAIMER: str = (
    "This document is decision-support output for laboratory quality processes. "
    "It is not a medical device and does not constitute CLIA/CAP/IVDR "
    "certification or a clinical determination. All revalidation decisions and "
    "their final disposition rest with the laboratory director."
)


class SignOffSection(BaseModel):
    """Manual sign-off block. Fields left None render as blank signature lines."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prepared_by: str | None = None
    prepared_date: str | None = None
    reviewed_by: str | None = None
    reviewed_date: str | None = None
    approved_by: str | None = None
    approved_date: str | None = None
    statement: str = (
        "I confirm the change-control assessment above has been reviewed and the "
        "revalidation determinations are appropriate for this assay."
    )


class AuditBinder(BaseModel):
    """Complete, deterministic audit package for a manifest change."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    generated_at: datetime

    assay_name: str
    assay_version: str
    laboratory_name: str
    laboratory_id: str
    old_manifest_id: str
    new_manifest_id: str
    old_content_hash: str
    new_content_hash: str

    changes: tuple[ChangeRecord, ...] = Field(default=())
    impacts: tuple[ImpactRecord, ...] = Field(default=())
    claim_impacts: tuple[ClaimImpactRecord, ...] = Field(default=())
    decisions: tuple[DecisionRecord, ...] = Field(default=())
    no_revalidation_records: tuple[NoRevalidationRecord, ...] = Field(default=())

    baseline_benchmark: GiabEvidencePackage | None = None
    current_benchmark: GiabEvidencePackage | None = None
    baseline_benchmark_pkg: BenchmarkPackage | None = None
    current_benchmark_pkg: BenchmarkPackage | None = None
    regression: tuple[MetricComparison, ...] = Field(default=())
    reportable_deltas: tuple[ReportableVariantDelta, ...] = Field(default=())
    variant_classification_deltas: tuple[VariantClassificationDelta, ...] = Field(default=())

    sign_off: SignOffSection = Field(default_factory=SignOffSection)
    disclaimer: str = DISCLAIMER