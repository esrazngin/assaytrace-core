"""Externalized rules for claim-impact matching.

Component changes are matched to claims purely through the Step-1 dependency
wiring (``depends_on_components`` / ``depends_on_categories``) — that is the
authoritative mechanism and lives in the mapper.

Non-component changes (QC thresholds, etc.) carry no component identity or
category, so they cannot be matched through the wiring. For those, this table
provides a transparent, deterministic bridge from the change's impact domain to
the claim types it can affect. The table is data, not logic: edit it to change
policy. It is intentionally minimal and conservative — only mappings that are
clearly defensible are included, to avoid false "claim affected" flags.
"""

from __future__ import annotations

from ..impact.models import ImpactDomain
from ..models.enums import ClaimType

# Domain -> claim types it can affect, used ONLY for non-component changes.
DOMAIN_CLAIM_TYPES: dict[ImpactDomain, frozenset[ClaimType]] = {
    ImpactDomain.QUALITY: frozenset({ClaimType.QC_DECISION_STABILITY}),
    # ANALYTICAL / INTERPRETIVE non-component changes (e.g., panel edits) are
    # intentionally NOT bridged here: region-coverage impact is not expressible
    # via the Step-1 dependency wiring, so inferring it would be speculation.
    # INFRASTRUCTURE / DOCUMENTATION / NONE map to no claim types by design.
}


def claim_types_for_domain(domain: ImpactDomain) -> frozenset[ClaimType]:
    return DOMAIN_CLAIM_TYPES.get(domain, frozenset())


# ---------------------------------------------------------------------------
# QC threshold -> performance characteristic -> claim types (Critical Issue #1)
#
# A QC threshold change (e.g. minimum_vaf 0.05 -> 0.03) materially affects assay
# performance and therefore the analytical claims that depend on that
# performance. Because a QC change carries no component identity, the Step-1
# dependency wiring cannot reach it; this externalized, extensible table makes
# the connection explicit and deterministic:
#
#     QC parameter  ->  performance characteristic  ->  affected claim types
#
# Edit the tables (data, not logic) to add parameters or re-map characteristics.
# Conservative by design: an unknown QC parameter maps to nothing rather than
# guessing.
# ---------------------------------------------------------------------------

# Performance characteristic each QC parameter governs.
QC_PARAMETER_CHARACTERISTIC: dict[str, str] = {
    "minimum_vaf": "sensitivity / limit of detection",
    "minimum_coverage": "analytical sensitivity (depth-dependent detection)",
    "minimum_depth": "analytical sensitivity (depth-dependent detection)",
    "minimum_alt_reads": "sensitivity / limit of detection",
    "minimum_mapping_quality": "alignment confidence / analytical specificity",
    "minimum_base_quality": "base accuracy / analytical specificity",
    "maximum_contamination": "specificity / false-positive control",
    "minimum_tumor_purity": "sensitivity / limit of detection",
}

# Performance characteristic -> claim types it can perturb.
CHARACTERISTIC_CLAIM_TYPES: dict[str, frozenset[ClaimType]] = {
    "sensitivity / limit of detection": frozenset({
        ClaimType.SNV_DETECTION, ClaimType.INDEL_DETECTION,
        ClaimType.LIMIT_OF_DETECTION,
    }),
    "analytical sensitivity (depth-dependent detection)": frozenset({
        ClaimType.SNV_DETECTION, ClaimType.INDEL_DETECTION,
        ClaimType.CNV_DETECTION, ClaimType.LIMIT_OF_DETECTION,
    }),
    "alignment confidence / analytical specificity": frozenset({
        ClaimType.SNV_DETECTION, ClaimType.INDEL_DETECTION,
    }),
    "base accuracy / analytical specificity": frozenset({
        ClaimType.SNV_DETECTION, ClaimType.INDEL_DETECTION,
    }),
    "specificity / false-positive control": frozenset({
        ClaimType.SNV_DETECTION, ClaimType.INDEL_DETECTION,
    }),
}


def qc_characteristic_for_parameter(metric: str) -> str | None:
    """Return the performance characteristic a QC parameter governs, or None."""
    return QC_PARAMETER_CHARACTERISTIC.get(metric)


def qc_claim_types_for_parameter(metric: str) -> frozenset[ClaimType]:
    """Claim types a QC parameter can perturb (empty for unknown parameters)."""
    characteristic = QC_PARAMETER_CHARACTERISTIC.get(metric)
    if characteristic is None:
        return frozenset()
    return CHARACTERISTIC_CLAIM_TYPES.get(characteristic, frozenset())
