"""Models for the Change Impact Graph (Step 3).

An ``ImpactRecord`` classifies a detected change into a single technical
*impact domain*. It explicitly does NOT state whether revalidation is required
(Step 4). Every record carries a human-readable ``rationale`` naming the exact
rule that produced it, so an auditor can trace the classification back to code.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ImpactDomain(str, Enum):
    """The technical domain a change touches. Mutually exclusive per change."""

    ANALYTICAL = "analytical"          # affects what variants are detected / how
    INTERPRETIVE = "interpretive"      # affects annotation / classification
    QUALITY = "quality"               # affects QC acceptance behavior
    INFRASTRUCTURE = "infrastructure"  # affects execution environment / orchestration
    DOCUMENTATION = "documentation"    # affects documented specification / claims only
    NONE = "none"                      # no technical impact domain

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class ImpactRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str = Field(description="The ChangeRecord.change_id this classifies.")
    impact_domain: ImpactDomain
    rationale: str = Field(
        description="Plain-language statement of the rule that produced this "
        "classification, for audit traceability."
    )