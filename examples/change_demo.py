"""Step 2 + Step 3 demonstration.

Builds an 'old' baseline and a 'new' manifest with a handful of representative
changes, then prints the detected changes and their impact-domain
classifications. Deliberately prints NO revalidation decision — that is Step 4.

Run from the repo root:  python -m examples.change_demo
"""

from __future__ import annotations

import copy

from assaytrace import AssayManifest
from assaytrace.diff import ChangeDetector
from assaytrace.impact import ChangeImpactGraph
from examples.build import build


def _new_from(old: AssayManifest) -> AssayManifest:
    d = copy.deepcopy(old.model_dump(mode="json"))
    # analytical: variant caller version bump
    d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"
    # interpretive: ClinVar annotation update
    for r in d["reference_resources"]["annotation_resources"]:
        if r["name"] == "ClinVar":
            r["version"] = "2026-01-01"
    # quality: loosen minimum coverage
    for t in d["qc"]["thresholds"]:
        if t["metric"] == "minimum_coverage":
            t["threshold"] = 300
    # infrastructure: new container build
    d["environment"]["container_version"] = "2.4.0"
    return AssayManifest.model_validate(d)


def main() -> None:
    old = build()
    new = _new_from(old)

    changes = ChangeDetector().compare(old, new)
    impacts = {i.change_id: i for i in ChangeImpactGraph().evaluate(changes)}

    print("## Detected Changes\n")
    for c in changes:
        old_v = "-" if c.old_value is None else c.old_value
        new_v = "-" if c.new_value is None else c.new_value
        # compact value rendering for QC dicts
        if isinstance(c.old_value, dict) or isinstance(c.new_value, dict):
            old_v = _fmt(c.old_value)
            new_v = _fmt(c.new_value)
        print(f"{c.component_identity}")
        print(f"    {c.change_type.value}: {old_v} -> {new_v}\n")

    print("## Impact Domains\n")
    for c in changes:
        domain = impacts[c.change_id].impact_domain
        print(f"{c.component_identity:<34} {domain.value}")

    print("\n## Rationale (audit trace)\n")
    for c in changes:
        print(f"{c.change_id}")
        print(f"    {impacts[c.change_id].rationale}\n")


def _fmt(v) -> str:
    if isinstance(v, dict):
        return f"{v.get('comparator','')} {v.get('threshold','')} {v.get('unit') or ''}".strip()
    return "-" if v is None else str(v)


if __name__ == "__main__":
    main()