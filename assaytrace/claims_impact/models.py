"""Models for the Assay-Claim Impact Map (Step 4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..impact.models import ImpactDomain
from ..models.enums import ClaimType


class ClaimImpactRecord(BaseModel):
    """A deterministic statement that a detected change touches a specific
    validated claim. No risk, no decision, no probability — only the fact of a
    dependency match, with a rationale naming the mechanism that matched."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str = Field(description="ChangeRecord.change_id that triggered this.")
    claim_id: str
    claim_type: ClaimType
    claim_name: str
    impact_domain: ImpactDomain = Field(
        description="The impact domain carried over from the Step-3 classification."
    )
    rationale: str = Field(
        description="Names the exact matching mechanism (depends_on_components, "
        "depends_on_categories, or the externalized domain rule)."
    )