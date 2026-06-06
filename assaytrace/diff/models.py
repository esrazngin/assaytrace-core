"""Models for the Change Detection Engine (Step 2).

A ``ChangeRecord`` is a pure, factual statement that *something differs*
between two manifests. It carries no judgment about risk, impact, or
revalidation — those belong to Steps 3 and 4. Records are frozen and fully
serializable so they can be embedded verbatim in an audit trail.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import ComponentCategory


class ChangeType(str, Enum):
    """The kind of difference detected. Coarse, stable, and exhaustive over the
    things the manifest can express.

    Design note: versioned *resources* (annotation DBs, transcript sets,
    reference genome) are deliberately reported as ``COMPONENT_*`` changes,
    disambiguated by the record's ``category``. The Step-1 schema models them
    as uniform components, so giving them a separate ``RESOURCE_CHANGED`` type
    would reintroduce field-by-field special-casing and break the "works for
    future components automatically" guarantee. One vocabulary, not two.
    """

    COMPONENT_ADDED = "component_added"
    COMPONENT_REMOVED = "component_removed"
    COMPONENT_VERSION_CHANGED = "component_version_changed"
    COMPONENT_PARAMETERS_CHANGED = "component_parameters_changed"
    QC_THRESHOLD_ADDED = "qc_threshold_added"
    QC_THRESHOLD_REMOVED = "qc_threshold_removed"
    QC_THRESHOLD_CHANGED = "qc_threshold_changed"
    PANEL_CHANGED = "panel_changed"
    PIPELINE_CHANGED = "pipeline_changed"
    ENVIRONMENT_CHANGED = "environment_changed"
    CLAIM_ADDED = "claim_added"
    CLAIM_REMOVED = "claim_removed"
    CLAIM_CHANGED = "claim_changed"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class ChangeRecord(BaseModel):
    """A single detected difference.

    ``change_id`` is *deterministic* — derived from the change type and the
    locator — so the same pair of manifests always yields the same ids. There
    is no randomness anywhere in detection.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str = Field(
        description="Deterministic identifier: '<change_type>|<locator>'."
    )
    change_type: ChangeType
    category: ComponentCategory | None = Field(
        default=None,
        description="Component category, when the change concerns a versioned "
        "component; None for QC/panel/pipeline/environment/claim changes.",
    )
    component_identity: str = Field(
        description="Locator for the changed entity. For components this is the "
        "Step-1 'category:slug' identity; for other changes a stable key such as "
        "'qc:minimum_coverage', 'assay_scope:bed_file', or 'claim:CLAIM-CNV-001'.",
    )
    old_value: Any | None = None
    new_value: Any | None = None
    description: str

    @staticmethod
    def make_id(change_type: ChangeType, locator: str) -> str:
        return f"{change_type.value}|{locator}"