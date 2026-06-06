"""Assay claims — the validated performance assertions of the assay.

These are the single most important objects for the downstream revalidation
engine. A claim is NOT a string; it is a structured assertion that declares:

  * what it claims (claim_type + quantified performance)
  * over what scope (variant types, optional genomic region label)
  * *which pipeline components it depends on* (categories and/or specific
    component identities)

The dependency declaration is the seam the Change Impact Graph (Step 3) walks:
"caller X changed -> which claims list VARIANT_CALLER (or X's identity) as a
dependency?" -> those claims are candidates for revalidation.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import NonEmptyStr
from .enums import (
    PROPORTION_METRICS,
    ClaimStatus,
    ClaimType,
    ComponentCategory,
    PerformanceMetricType,
    VariantType,
)

_BASE_CONFIG = ConfigDict(
    frozen=True, extra="forbid", str_strip_whitespace=True, use_enum_values=False
)

ClaimId = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_\-]*$")]


class ConfidenceInterval(BaseModel):
    model_config = _BASE_CONFIG

    lower: float
    upper: float
    level: float = Field(default=0.95, gt=0.0, lt=1.0)

    @model_validator(mode="after")
    def _ordered(self) -> "ConfidenceInterval":
        if self.lower > self.upper:
            raise ValueError("confidence interval lower bound exceeds upper bound")
        return self


class PerformanceMetric(BaseModel):
    """A single quantified performance figure backing a claim."""

    model_config = _BASE_CONFIG

    metric: PerformanceMetricType
    value: float
    unit: str | None = None
    variant_type: VariantType | None = None
    confidence_interval: ConfidenceInterval | None = None
    evidence_reference: str | None = Field(
        default=None, description="Pointer to the validation study / document ID."
    )

    @model_validator(mode="after")
    def _proportion_bounds(self) -> "PerformanceMetric":
        if self.metric in PROPORTION_METRICS and not (0.0 <= self.value <= 1.0):
            raise ValueError(
                f"{self.metric.value} is a proportion and must be within [0, 1]"
            )
        return self


class AssayClaim(BaseModel):
    model_config = _BASE_CONFIG

    claim_id: ClaimId
    claim_type: ClaimType
    title: NonEmptyStr
    description: str | None = None
    status: ClaimStatus = ClaimStatus.ESTABLISHED

    variant_types: tuple[VariantType, ...] = Field(
        default=(), description="Variant scope this claim covers."
    )
    genomic_scope: str | None = Field(
        default=None,
        description="Human-readable region scope, e.g. 'panel target regions' "
        "or 'coding exons of BRCA1/2'.",
    )
    claimed_performance: tuple[PerformanceMetric, ...] = Field(default=())

    depends_on_categories: tuple[ComponentCategory, ...] = Field(
        default=(),
        description="Component categories whose change can invalidate this claim.",
    )
    depends_on_components: tuple[str, ...] = Field(
        default=(),
        description="Specific component identities (category:slug) this claim "
        "depends on, for finer-grained impact than category alone.",
    )
    evidence_references: tuple[str, ...] = Field(
        default=(),
        description="Validation evidence document/record IDs supporting the claim.",
    )

    @field_validator("depends_on_categories")
    @classmethod
    def _no_duplicate_categories(
        cls, v: tuple[ComponentCategory, ...]
    ) -> tuple[ComponentCategory, ...]:
        if len(set(v)) != len(v):
            raise ValueError("depends_on_categories contains duplicates")
        return v
