"""Deterministic, human-friendly labels.

A single mapping layer that turns the platform's machine identifiers (component
categories, change types, revalidation types, and policy rule ids) into plain
language for laboratory directors and QA teams. Pure lookups and structural
derivation — no free text, no AI. The underlying ids are always preserved by
callers; these labels are presentation only.
"""

from __future__ import annotations

from .decision.models import RevalidationType
from .diff.models import ChangeType
from .models.enums import ComponentCategory
from .severity.models import VersionMagnitude

CATEGORY_LABELS: dict[ComponentCategory, str] = {
    ComponentCategory.BASECALLER: "Basecaller",
    ComponentCategory.DEMULTIPLEXER: "Demultiplexer",
    ComponentCategory.READ_TRIMMER: "Read Trimmer",
    ComponentCategory.ALIGNER: "Aligner",
    ComponentCategory.DUPLICATE_MARKER: "Duplicate Marker",
    ComponentCategory.BASE_RECALIBRATOR: "Base Recalibrator",
    ComponentCategory.VARIANT_CALLER: "Variant Caller",
    ComponentCategory.CNV_CALLER: "CNV Caller",
    ComponentCategory.SV_CALLER: "SV Caller",
    ComponentCategory.VARIANT_FILTER: "Variant Filter",
    ComponentCategory.ANNOTATION: "Annotation Database",
    ComponentCategory.REFERENCE_GENOME: "Reference Genome",
    ComponentCategory.KNOWN_SITES: "Known-Sites Resource",
    ComponentCategory.TRANSCRIPT_SET: "Transcript Set",
    ComponentCategory.QC_TOOL: "QC Tool",
    ComponentCategory.OTHER: "Component",
}

CHANGE_TYPE_LABELS: dict[ChangeType, str] = {
    ChangeType.COMPONENT_ADDED: "Component Added",
    ChangeType.COMPONENT_REMOVED: "Component Removed",
    ChangeType.COMPONENT_VERSION_CHANGED: "Version Change",
    ChangeType.COMPONENT_PARAMETERS_CHANGED: "Parameter Change",
    ChangeType.QC_THRESHOLD_ADDED: "QC Threshold Added",
    ChangeType.QC_THRESHOLD_REMOVED: "QC Threshold Removed",
    ChangeType.QC_THRESHOLD_CHANGED: "QC Threshold Change",
    ChangeType.PANEL_CHANGED: "Panel / Scope Change",
    ChangeType.PIPELINE_CHANGED: "Pipeline Change",
    ChangeType.ENVIRONMENT_CHANGED: "Environment Change",
    ChangeType.CLAIM_ADDED: "Claim Added",
    ChangeType.CLAIM_REMOVED: "Claim Removed",
    ChangeType.CLAIM_CHANGED: "Claim Change",
}

REVALIDATION_LABELS: dict[RevalidationType, str] = {
    RevalidationType.NONE: "No revalidation required",
    RevalidationType.TARGETED_ANALYTICAL: "Targeted analytical revalidation",
    RevalidationType.FULL_ANALYTICAL: "Full analytical revalidation",
    RevalidationType.FULL_OR_TARGETED_ANALYTICAL: "Full or targeted analytical revalidation",
    RevalidationType.CLASSIFICATION_CONCORDANCE_REVIEW: "Classification concordance review",
    RevalidationType.SCOPE_REVIEW_AND_TARGETED: "Scope review and targeted validation",
    RevalidationType.QC_VERIFICATION: "QC verification",
    RevalidationType.INFRASTRUCTURE_VERIFICATION: "Infrastructure verification",
    RevalidationType.DOCUMENTATION_UPDATE: "Documentation update",
}

_MAGNITUDE_WORD: dict[VersionMagnitude, str] = {
    VersionMagnitude.PATCH: "Patch",
    VersionMagnitude.MINOR: "Minor",
    VersionMagnitude.MAJOR: "Major",
    VersionMagnitude.NONE: "",
    VersionMagnitude.UNKNOWN: "",
}

# Approval workflow (Sprint 4): plain-language state + laboratory disposition.
APPROVAL_STATUS_LABELS: dict[str, str] = {
    "not_reviewed": "Not Reviewed",
    "pending": "Pending Review",
    "approved": "Approved",
    "approved_with_conditions": "Approved With Conditions",
    "rejected": "Rejected",
}

APPROVAL_DISPOSITIONS: dict[str, str] = {
    "not_reviewed": "Awaiting laboratory review",
    "pending": "Pending laboratory review",
    "approved": "Approved Deviation",
    "approved_with_conditions": "Approved Deviation (conditional)",
    "rejected": "Rejected - revalidation required",
}


def approval_status_label(status: str | None) -> str:
    if not status:
        return "Not Reviewed"
    return APPROVAL_STATUS_LABELS.get(status, status.replace("_", " ").title())


def approval_disposition(status: str | None) -> str:
    if not status:
        return "Awaiting laboratory review"
    return APPROVAL_DISPOSITIONS.get(status, status.replace("_", " ").title())


def category_label(category: ComponentCategory | None) -> str:
    if category is None:
        return "Configuration"
    return CATEGORY_LABELS.get(category, category.value.replace("_", " ").title())


def change_type_label(change_type: ChangeType) -> str:
    return CHANGE_TYPE_LABELS.get(change_type, change_type.value.replace("_", " ").title())


def revalidation_label(rt: RevalidationType) -> str:
    return REVALIDATION_LABELS.get(rt, rt.value.replace("_", " "))


def magnitude_word(magnitude: VersionMagnitude | None) -> str:
    if magnitude is None:
        return ""
    return _MAGNITUDE_WORD.get(magnitude, "")


def rule_label(
    rule_id: str | None,
    *,
    category: ComponentCategory | None = None,
    change_type: ChangeType | None = None,
    magnitude: VersionMagnitude | None = None,
) -> str:
    """Human label for a triggered rule, derived structurally from the change.

    Examples: 'Minor Variant Caller Upgrade', 'Reference Genome Change',
    'QC Threshold Change (default policy)'. The raw ``rule_id`` is preserved by
    the caller and shown alongside the label.
    """
    if not rule_id:
        return "No rule applied"

    is_builtin = rule_id.startswith("builtin:")
    suffix = " (default policy)" if is_builtin else ""

    word = magnitude_word(magnitude)
    if category is not None:
        noun = category_label(category)
        if word and change_type is ChangeType.COMPONENT_VERSION_CHANGED:
            return f"{word} {noun} Upgrade{suffix}"
        return f"{noun} Change{suffix}"
    if change_type is not None:
        return f"{change_type_label(change_type)}{suffix}"
    # Fallback: derive from the id tail without inventing meaning.
    tail = rule_id.split(":")[-1].replace("_", " ").title()
    return f"{tail}{suffix}"
