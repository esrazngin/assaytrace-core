"""Externalized severity rule tables.

All severity policy lives here as data: magnitude -> severity, change-type ->
severity, category severity floors, and the relaxation threshold for QC. The
scorer performs lookups and bounded escalation only — no hidden heuristics.
Edit these tables to change how severity is assigned.
"""

from __future__ import annotations

from ..diff.models import ChangeType
from ..models.enums import ComponentCategory
from .models import Severity, VersionMagnitude

# Version-change severity is driven primarily by magnitude.
SEVERITY_BY_MAGNITUDE: dict[VersionMagnitude, Severity] = {
    VersionMagnitude.NONE: Severity.LOW,
    VersionMagnitude.PATCH: Severity.LOW,
    VersionMagnitude.MINOR: Severity.MEDIUM,
    VersionMagnitude.MAJOR: Severity.HIGH,
    # Non-numeric versions (e.g., dated DB releases) can't be ranked by magnitude;
    # treat conservatively as MEDIUM and disclose the uncertainty in the rationale.
    VersionMagnitude.UNKNOWN: Severity.MEDIUM,
}

# Base severity for non-version change types.
SEVERITY_BY_CHANGE_TYPE: dict[ChangeType, Severity] = {
    ChangeType.COMPONENT_ADDED: Severity.MEDIUM,
    ChangeType.COMPONENT_REMOVED: Severity.HIGH,
    ChangeType.COMPONENT_PARAMETERS_CHANGED: Severity.MEDIUM,
    ChangeType.QC_THRESHOLD_ADDED: Severity.MEDIUM,
    ChangeType.QC_THRESHOLD_REMOVED: Severity.HIGH,
    ChangeType.QC_THRESHOLD_CHANGED: Severity.MEDIUM,  # refined by relaxation analysis
    ChangeType.PANEL_CHANGED: Severity.HIGH,
    ChangeType.PIPELINE_CHANGED: Severity.MEDIUM,
    ChangeType.ENVIRONMENT_CHANGED: Severity.LOW,
    ChangeType.CLAIM_ADDED: Severity.LOW,
    ChangeType.CLAIM_REMOVED: Severity.MEDIUM,
    ChangeType.CLAIM_CHANGED: Severity.LOW,
}

# A category-specific lower bound: a change touching this category can never be
# scored below the given severity, regardless of magnitude. The reference genome
# is foundational — even a "minor" change has assay-wide reach.
CATEGORY_SEVERITY_FLOOR: dict[ComponentCategory, Severity] = {
    ComponentCategory.REFERENCE_GENOME: Severity.HIGH,
    ComponentCategory.VARIANT_CALLER: Severity.LOW,
}

# Categories whose add/remove or major-version change escalates to CRITICAL.
CRITICAL_ON_REPLACEMENT: frozenset[ComponentCategory] = frozenset(
    {ComponentCategory.REFERENCE_GENOME}
)

# QC relaxation: relative change at/above this fraction is "substantial".
QC_SUBSTANTIAL_RELAXATION: float = 0.20

# Human-readable rationale fragments by magnitude.
MAGNITUDE_PHRASE: dict[VersionMagnitude, str] = {
    VersionMagnitude.PATCH: "Patch version change detected",
    VersionMagnitude.MINOR: "Minor version change detected",
    VersionMagnitude.MAJOR: "Major version change detected",
    VersionMagnitude.NONE: "Version unchanged",
    VersionMagnitude.UNKNOWN: "Version change detected (non-numeric versioning; magnitude could not be determined)",
}
