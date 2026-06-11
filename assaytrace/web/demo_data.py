"""JSON-safe demo policy and approvals for the web showcase.

Kept out of the Flask module so the example data has one obvious home. Both
functions return plain dicts/lists that ``parse_policy`` and
``DeviationApproval.model_validate`` accept directly, so the auto-run demo
exercises the real policy engine and approval workflow end to end.
"""

from __future__ import annotations


def demo_policy_dict() -> dict:
    """A small somatic SOP policy in the ergonomic grouped form."""
    return {
        "name": "somatic-sop-v1",
        "assay_type": "somatic",
        "mutect2": {
            "major_version": {
                "action": "full_revalidation",
                "rationale": "Major variant-caller change; full analytical "
                "revalidation per SOP-12.",
            },
            "minor_version": {
                "action": "targeted_revalidation",
                "rationale": "Minor variant-caller upgrade affecting variant "
                "calling behavior; targeted analytical revalidation.",
            },
            "patch_version": {
                "action": "documentation_review",
                "rationale": "Patch variant-caller change; documentation review "
                "sufficient.",
            },
        },
        "category:reference_genome": {
            "any": {
                "action": "full_revalidation",
                "rationale": "Reference genome change has assay-wide reach; full "
                "revalidation.",
            }
        },
    }


def demo_somatic_approvals() -> list[dict]:
    """One approved deviation for the somatic demo's variant-caller change."""
    return [
        {
            "change_id": "component_version_changed|variant_caller:mutect2",
            "status": "approved",
            "reviewer": "Lab Director",
            "approval_date": "2026-02-01",
            "rationale": "Minor Mutect2 upgrade validated against GIAB HG002; "
            "approved per change-control SOP-12.",
        }
    ]