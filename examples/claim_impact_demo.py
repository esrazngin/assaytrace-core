"""Step 2 + 3 + 4 demonstration: detected changes, impact domains, and the
affected assay claims. Prints no revalidation decisions.

Run from the repo root:  python -m examples.claim_impact_demo
"""

from __future__ import annotations

import copy

from assaytrace import AssayManifest
from assaytrace.claims_impact import ClaimImpactMapper
from assaytrace.diff import ChangeDetector
from assaytrace.impact import ChangeImpactGraph
from examples.build import build


def _with_qc_claim(manifest: AssayManifest) -> AssayManifest:
    d = copy.deepcopy(manifest.model_dump(mode="json"))
    d["claims"].append(
        {
            "claim_id": "CLAIM-QC-001",
            "claim_type": "qc_decision_stability",
            "title": "QC decision stability under threshold updates",
            "description": None,
            "status": "established",
            "variant_types": [],
            "genomic_scope": None,
            "claimed_performance": [],
            "depends_on_categories": [],
            "depends_on_components": [],
            "evidence_references": [],
        }
    )
    return AssayManifest.model_validate(d)


def _new_from(old: AssayManifest) -> AssayManifest:
    d = copy.deepcopy(old.model_dump(mode="json"))
    d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"   # analytical
    for r in d["reference_resources"]["annotation_resources"]:
        if r["name"] == "ClinVar":
            r["version"] = "2026-01-01"                                  # interpretive
    for t in d["qc"]["thresholds"]:
        if t["metric"] == "minimum_coverage":
            t["threshold"] = 300                                        # quality
    return AssayManifest.model_validate(d)


def main() -> None:
    old = _with_qc_claim(build())
    new = _new_from(old)

    changes = ChangeDetector().compare(old, new)
    impacts = ChangeImpactGraph().evaluate(changes)
    claim_impacts = ClaimImpactMapper().map(manifest=new, changes=changes, impacts=impacts)

    domain_by_change = {i.change_id: i.impact_domain for i in impacts}

    print("## Detected Changes\n")
    for c in changes:
        print(f"{c.component_identity}: {c.old_value} -> {c.new_value}")

    print("\n## Impact Domains\n")
    for c in changes:
        print(f"{c.component_identity:<34} {domain_by_change[c.change_id].value}")

    print("\n## Affected Assay Claims\n")
    for r in claim_impacts:
        print(f"{r.claim_id} [{r.claim_type.value}] ({r.impact_domain.value})")
        print(f"    name: {r.claim_name}")
        print(f"    via:  {r.rationale}\n")


if __name__ == "__main__":
    main()