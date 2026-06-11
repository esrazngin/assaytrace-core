"""Models for the Transparent Revalidation Decision Engine (Steps 5-6)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from ..impact.models import ImpactDomain
from ..severity.models import Severity, VersionMagnitude


class RevalidationType(str, Enum):
    """The revalidation action a change requires. Fully enumerated and auditable."""

    NONE = "no_revalidation_required"
    TARGETED_ANALYTICAL = "targeted_analytical_revalidation"
    FULL_ANALYTICAL = "full_analytical_revalidation"
    FULL_OR_TARGETED_ANALYTICAL = "full_or_targeted_analytical_revalidation"
    CLASSIFICATION_CONCORDANCE_REVIEW = "classification_concordance_review"
    SCOPE_REVIEW_AND_TARGETED = "scope_review_and_targeted_validation"
    QC_VERIFICATION = "qc_verification"
    INFRASTRUCTURE_VERIFICATION = "infrastructure_verification"
    DOCUMENTATION_UPDATE = "documentation_update"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class DecisionRecord(BaseModel):
    """A single, fully explainable revalidation decision for one change."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    change_id: str
    decision_type: RevalidationType
    impact_domain: ImpactDomain
    rationale: str
    affected_claims: tuple[str, ...] = Field(default=())
    required_evidence: tuple[str, ...] = Field(default=())
    # Intelligence/auditability additions (additive; default-safe).
    severity: Severity | None = None
    version_magnitude: VersionMagnitude | None = None
    triggered_by_rule: str = Field(
        default="",
        description="Identifier of the rule that produced this decision, e.g. "
        "'policy:mutect2:minor_version' or 'builtin:category:variant_caller'.",
    )
