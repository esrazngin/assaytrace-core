"""Cross-cutting referential-integrity checks.

These live outside the models because they reason about the manifest *as a
whole* (claims referencing components, claim types requiring callers, somatic
assays requiring VAF thresholds). Keeping them here keeps the section models
cohesive and makes the rule set independently testable and, later, versionable
alongside the revalidation engine.

Each function returns a list of human-readable error strings; the root model
aggregates them and raises a single ValueError so callers get all problems at
once rather than one-at-a-time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models.enums import AssayType, ClaimType, ComponentCategory

if TYPE_CHECKING:  # avoid circular import at runtime
    from ..models.manifest import AssayManifest


# Which claim types structurally require which component category to be present.
_CLAIM_REQUIRES_CATEGORY: dict[ClaimType, ComponentCategory] = {
    ClaimType.SNV_DETECTION: ComponentCategory.VARIANT_CALLER,
    ClaimType.INDEL_DETECTION: ComponentCategory.VARIANT_CALLER,
    ClaimType.CNV_DETECTION: ComponentCategory.CNV_CALLER,
    ClaimType.SV_DETECTION: ComponentCategory.SV_CALLER,
}


def check_unique_claim_ids(manifest: "AssayManifest") -> list[str]:
    seen: set[str] = set()
    errors: list[str] = []
    for claim in manifest.claims:
        if claim.claim_id in seen:
            errors.append(f"duplicate claim_id '{claim.claim_id}'")
        seen.add(claim.claim_id)
    return errors


def check_claim_dependencies_resolve(manifest: "AssayManifest") -> list[str]:
    """Every category/identity a claim depends on must actually exist."""
    present_categories = manifest.present_categories()
    present_identities = manifest.component_identities()
    errors: list[str] = []
    for claim in manifest.claims:
        for cat in claim.depends_on_categories:
            if cat not in present_categories:
                errors.append(
                    f"claim '{claim.claim_id}' depends on category "
                    f"'{cat.value}' which is not present in the pipeline"
                )
        for ident in claim.depends_on_components:
            if ident not in present_identities:
                errors.append(
                    f"claim '{claim.claim_id}' depends on component "
                    f"'{ident}' which is not present in the pipeline"
                )
    return errors


def check_claim_types_have_required_components(manifest: "AssayManifest") -> list[str]:
    """A CNV_DETECTION claim with no cnv_caller is incoherent, etc."""
    present = manifest.present_categories()
    errors: list[str] = []
    for claim in manifest.claims:
        required = _CLAIM_REQUIRES_CATEGORY.get(claim.claim_type)
        if required is not None and required not in present:
            errors.append(
                f"claim '{claim.claim_id}' of type '{claim.claim_type.value}' "
                f"requires a '{required.value}' component, but none is present"
            )
    return errors


def check_somatic_vaf_threshold(manifest: "AssayManifest") -> list[str]:
    """Somatic assays must declare a minimum VAF threshold: it is a core part
    of the assay's limit-of-detection identity and downstream revalidation."""
    is_somatic = manifest.assay.assay_type in {
        AssayType.SOMATIC,
        AssayType.GERMLINE_AND_SOMATIC,
    }
    if is_somatic and not manifest.qc.has_metric("minimum_vaf"):
        return [
            "somatic assays must declare a 'minimum_vaf' QC threshold "
            "(limit of detection is part of the assay's identity)"
        ]
    return []


def run_all_integrity_checks(manifest: "AssayManifest") -> list[str]:
    errors: list[str] = []
    errors += check_unique_claim_ids(manifest)
    errors += check_claim_dependencies_resolve(manifest)
    errors += check_claim_types_have_required_components(manifest)
    errors += check_somatic_vaf_threshold(manifest)
    return errors
