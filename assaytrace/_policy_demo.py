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


def demo_germline_policy_dict() -> dict:
    """A small germline SOP, used to populate the policy registry."""
    return {
        "name": "germline-sop-v1",
        "assay_type": "germline",
        "version": "v1",
        "haplotypecaller": {
            "major_version": {
                "action": "full_revalidation",
                "rationale": "Major caller change; full germline revalidation.",
            },
            "minor_version": {
                "action": "targeted_revalidation",
                "rationale": "Minor caller change; targeted revalidation.",
            },
        },
        "category:reference_genome": {
            "any": {
                "action": "full_revalidation",
                "rationale": "Reference genome change; full revalidation.",
            }
        },
    }


def demo_policy_registry() -> list[dict]:
    """Deterministic registry of real policies for the Policy Management UI.

    Each descriptor's ``hash`` is the real ``content_hash()`` of a parsed
    ``RevalidationPolicy`` — no fabricated values. Carries governance metadata
    (owner, dates, usage) and groups into families with a version history so the
    tab reads like an SOP management platform rather than static cards.
    """
    from .policy import parse_policy

    def desc(spec, version, status, *, owner, created, modified, active_since,
             decisions, assays, family, assay_type, description):
        s = dict(spec)
        s["version"] = version
        pol = parse_policy(s)
        return {
            "name": pol.name, "family": family, "version": version,
            "assay_type": assay_type, "status": status,
            "hash": pol.content_hash(), "rule_count": len(pol.rules),
            "owner": owner, "created": created, "last_modified": modified,
            "active_since": active_since, "decisions_generated": decisions,
            "assays_using": assays, "description": description,
        }

    som, germ = demo_policy_dict(), demo_germline_policy_dict()
    som_desc = "Revalidation policy for somatic solid-tumor NGS assays (caller, reference genome, annotation, QC)."
    germ_desc = "Revalidation policy for hereditary germline NGS panels."
    return [
        # Somatic SOP family: v1/v2 archived, v3 active, v4 draft.
        desc(som, "v1", "archived", owner="Dr. A. Yilmaz", created="2024-03-01",
             modified="2024-08-12", active_since="2024-03-10", decisions=412,
             assays=["SolidTumor500", "Myeloid Panel"], family="Somatic SOP",
             assay_type="somatic", description=som_desc),
        desc(som, "v2", "archived", owner="Dr. A. Yilmaz", created="2024-09-01",
             modified="2025-04-20", active_since="2024-09-15", decisions=688,
             assays=["SolidTumor500", "Myeloid Panel", "Colon Panel"], family="Somatic SOP",
             assay_type="somatic", description=som_desc),
        desc(som, "v3", "active", owner="Dr. A. Yilmaz", created="2025-05-01",
             modified="2026-05-28", active_since="2025-05-10", decisions=531,
             assays=["SolidTumor500", "Myeloid Panel", "Colon Panel", "RNA Fusion", "Liquid Biopsy"],
             family="Somatic SOP", assay_type="somatic", description=som_desc),
        desc(som, "v4", "draft", owner="Dr. A. Yilmaz", created="2026-06-01",
             modified="2026-06-03", active_since=None, decisions=0,
             assays=[], family="Somatic SOP", assay_type="somatic",
             description=som_desc + " Draft: tightened minor-caller rule, added annotation rule."),
        # Germline SOP family: v1 archived, v2 active.
        desc(germ, "v1", "archived", owner="Dr. M. Demir", created="2024-06-01",
             modified="2025-01-15", active_since="2024-06-10", decisions=205,
             assays=["BRCA Germline"], family="Germline SOP", assay_type="germline",
             description=germ_desc),
        desc(germ, "v2", "active", owner="Dr. M. Demir", created="2025-02-01",
             modified="2026-05-30", active_since="2025-02-12", decisions=174,
             assays=["BRCA Germline"], family="Germline SOP", assay_type="germline",
             description=germ_desc),
    ]


def demo_somatic_approvals() -> list[dict]:
    """One approved deviation for the somatic release's QC threshold relaxation.

    Retained for backward compatibility; the web demo now builds a richer,
    history-bearing approval set from the detected changes (see web.app).
    """
    return [
        {
            "change_id": "qc_threshold_changed|qc:minimum_vaf[snv,indel]",
            "status": "approved",
            "reviewer": "Lab Director",
            "approval_date": "2026-02-01",
            "rationale": "VAF floor lowered 0.05 -> 0.03 to improve sensitivity for "
            "low-VAF ctDNA; validated on contrived controls per SOP-19.",
        }
    ]
