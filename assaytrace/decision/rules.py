"""Externalized revalidation rule tables (Step 5).

All decision policy lives in data tables: component category -> revalidation
type, non-component change type -> revalidation type, revalidation type ->
required evidence, plus human-readable rationale templates. No if/else trees;
the engine performs dictionary lookups only. Edit the tables to change policy.
"""

from __future__ import annotations

from ..diff.models import ChangeType
from ..models.enums import ComponentCategory
from .models import RevalidationType

# --- Component category -> revalidation type ------------------------------- #
REVALIDATION_BY_CATEGORY: dict[ComponentCategory, RevalidationType] = {
    ComponentCategory.BASECALLER: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.DEMULTIPLEXER: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.READ_TRIMMER: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.ALIGNER: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.DUPLICATE_MARKER: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.BASE_RECALIBRATOR: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.VARIANT_CALLER: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.CNV_CALLER: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.SV_CALLER: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.VARIANT_FILTER: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.KNOWN_SITES: RevalidationType.TARGETED_ANALYTICAL,
    ComponentCategory.REFERENCE_GENOME: RevalidationType.FULL_OR_TARGETED_ANALYTICAL,
    ComponentCategory.ANNOTATION: RevalidationType.CLASSIFICATION_CONCORDANCE_REVIEW,
    ComponentCategory.TRANSCRIPT_SET: RevalidationType.CLASSIFICATION_CONCORDANCE_REVIEW,
    ComponentCategory.QC_TOOL: RevalidationType.QC_VERIFICATION,
}

# Applied when a component category has no explicit rule (e.g., a future
# category). Conservative: targeted analytical revalidation, with a rationale
# that discloses the default was used.
DEFAULT_COMPONENT_REVALIDATION: RevalidationType = RevalidationType.TARGETED_ANALYTICAL

# --- Non-component change type -> revalidation type ------------------------ #
REVALIDATION_BY_CHANGE_TYPE: dict[ChangeType, RevalidationType] = {
    ChangeType.QC_THRESHOLD_ADDED: RevalidationType.QC_VERIFICATION,
    ChangeType.QC_THRESHOLD_REMOVED: RevalidationType.QC_VERIFICATION,
    ChangeType.QC_THRESHOLD_CHANGED: RevalidationType.QC_VERIFICATION,
    ChangeType.PANEL_CHANGED: RevalidationType.SCOPE_REVIEW_AND_TARGETED,
    ChangeType.PIPELINE_CHANGED: RevalidationType.INFRASTRUCTURE_VERIFICATION,
    ChangeType.ENVIRONMENT_CHANGED: RevalidationType.INFRASTRUCTURE_VERIFICATION,
    ChangeType.CLAIM_ADDED: RevalidationType.DOCUMENTATION_UPDATE,
    ChangeType.CLAIM_REMOVED: RevalidationType.DOCUMENTATION_UPDATE,
    ChangeType.CLAIM_CHANGED: RevalidationType.DOCUMENTATION_UPDATE,
}

# --- Revalidation type -> required evidence -------------------------------- #
REQUIRED_EVIDENCE: dict[RevalidationType, tuple[str, ...]] = {
    RevalidationType.NONE: (),
    RevalidationType.TARGETED_ANALYTICAL: (
        "GIAB HG002 benchmark comparison (targeted regions)",
    ),
    RevalidationType.FULL_ANALYTICAL: (
        "GIAB HG002 full benchmark comparison",
    ),
    RevalidationType.FULL_OR_TARGETED_ANALYTICAL: (
        "GIAB HG002 benchmark comparison (full or targeted, per laboratory determination)",
    ),
    RevalidationType.CLASSIFICATION_CONCORDANCE_REVIEW: (
        "Variant classification concordance review across resource versions",
    ),
    RevalidationType.SCOPE_REVIEW_AND_TARGETED: (
        "Target-region scope review",
        "GIAB HG002 benchmark comparison (targeted regions)",
    ),
    RevalidationType.QC_VERIFICATION: (
        "QC metric verification on control samples",
    ),
    RevalidationType.INFRASTRUCTURE_VERIFICATION: (
        "Execution environment reproducibility verification",
    ),
    RevalidationType.DOCUMENTATION_UPDATE: (
        "Documentation / specification update record",
    ),
}

# --- Rationale templates --------------------------------------------------- #
RATIONALE_BY_CATEGORY: dict[ComponentCategory, str] = {
    ComponentCategory.ALIGNER: "Aligner changed and may alter alignment and downstream variant calls.",
    ComponentCategory.VARIANT_CALLER: "Variant caller version changed and may alter SNV/indel calls.",
    ComponentCategory.CNV_CALLER: "CNV caller changed and may alter copy-number calls.",
    ComponentCategory.SV_CALLER: "SV caller changed and may alter structural-variant calls.",
    ComponentCategory.VARIANT_FILTER: "Variant filter changed and may alter reported calls.",
    ComponentCategory.KNOWN_SITES: "Known-sites resource changed and may alter filtering/recalibration and calls.",
    ComponentCategory.REFERENCE_GENOME: "Reference genome changed and may alter coordinates and calls across the assay.",
    ComponentCategory.ANNOTATION: "Annotation resource changed and may alter variant classification.",
    ComponentCategory.TRANSCRIPT_SET: "Transcript set changed and may alter variant classification and nomenclature.",
    ComponentCategory.QC_TOOL: "QC tool changed and may alter QC acceptance behavior.",
}

RATIONALE_BY_CHANGE_TYPE: dict[ChangeType, str] = {
    ChangeType.QC_THRESHOLD_ADDED: "QC threshold added and may alter QC acceptance decisions.",
    ChangeType.QC_THRESHOLD_REMOVED: "QC threshold removed and may alter QC acceptance decisions.",
    ChangeType.QC_THRESHOLD_CHANGED: "QC threshold changed and may alter QC acceptance decisions.",
    ChangeType.PANEL_CHANGED: "Assay scope changed; target regions and coverage may be affected.",
    ChangeType.PIPELINE_CHANGED: "Pipeline/workflow changed; execution behavior may be affected.",
    ChangeType.ENVIRONMENT_CHANGED: "Execution environment changed; reproducibility may be affected.",
    ChangeType.CLAIM_ADDED: "Assay claim specification changed; documentation update required.",
    ChangeType.CLAIM_REMOVED: "Assay claim specification changed; documentation update required.",
    ChangeType.CLAIM_CHANGED: "Assay claim specification changed; documentation update required.",
}