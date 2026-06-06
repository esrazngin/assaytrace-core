from __future__ import annotations

import copy

import pytest

from assaytrace import AssayManifest
from assaytrace.claims_impact import ClaimImpactMapper
from assaytrace.decision import RevalidationDecisionEngine, RevalidationType
from assaytrace.diff import ChangeDetector, ChangeType
from assaytrace.impact import ChangeImpactGraph, ImpactDomain


@pytest.fixture()
def pipeline():
    detector = ChangeDetector()
    graph = ChangeImpactGraph()
    mapper = ClaimImpactMapper()
    engine = RevalidationDecisionEngine()

    def run(old: AssayManifest, new: AssayManifest):
        changes = detector.compare(old, new)
        impacts = graph.evaluate(changes)
        claim_impacts = mapper.map(manifest=new, changes=changes, impacts=impacts)
        decisions = engine.decide(changes, impacts, claim_impacts)
        return changes, impacts, claim_impacts, decisions

    return run


def _mutate(valid_dict, fn) -> tuple[AssayManifest, AssayManifest]:
    old = AssayManifest.model_validate(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    fn(new_d)
    return old, AssayManifest.model_validate(new_d)


def _add_qc_claim(d: dict) -> None:
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


# 1. Variant caller update ---------------------------------------------------
def test_scenario_variant_caller(pipeline, valid_dict):
    old, new = _mutate(valid_dict, lambda d: d["analysis_components"]["variant_caller"].__setitem__("version", "4.6.0.0"))
    changes, impacts, claim_impacts, decisions = pipeline(old, new)

    assert [c.change_type for c in changes] == [ChangeType.COMPONENT_VERSION_CHANGED]
    assert impacts[0].impact_domain is ImpactDomain.ANALYTICAL
    assert {ci.claim_id for ci in claim_impacts} == {"CLAIM-SNV-001", "CLAIM-INDEL-001"}
    assert len(decisions) == 1
    d = decisions[0]
    assert d.decision_type is RevalidationType.TARGETED_ANALYTICAL
    assert set(d.affected_claims) == {"CLAIM-SNV-001", "CLAIM-INDEL-001"}
    assert any("GIAB" in e for e in d.required_evidence)
    assert "SNV/indel" in d.rationale


# 2. Aligner update ----------------------------------------------------------
def test_scenario_aligner(pipeline, valid_dict):
    old, new = _mutate(valid_dict, lambda d: d["analysis_components"]["aligner"].__setitem__("version", "2.2.2"))
    changes, impacts, claim_impacts, decisions = pipeline(old, new)

    assert impacts[0].impact_domain is ImpactDomain.ANALYTICAL
    assert decisions[0].decision_type is RevalidationType.TARGETED_ANALYTICAL
    assert set(decisions[0].affected_claims) == {"CLAIM-SNV-001", "CLAIM-INDEL-001"}


# 3. Reference genome update -------------------------------------------------
def test_scenario_reference_genome(pipeline, valid_dict):
    old, new = _mutate(valid_dict, lambda d: d["reference_resources"]["reference_genome"].__setitem__("version", "GRCh38.p15"))
    changes, impacts, claim_impacts, decisions = pipeline(old, new)

    assert impacts[0].impact_domain is ImpactDomain.ANALYTICAL
    assert decisions[0].decision_type is RevalidationType.FULL_OR_TARGETED_ANALYTICAL
    assert set(decisions[0].affected_claims) == {"CLAIM-SNV-001", "CLAIM-INDEL-001"}


# 4. ClinVar update ----------------------------------------------------------
def test_scenario_clinvar(pipeline, valid_dict):
    def m(d):
        for r in d["reference_resources"]["annotation_resources"]:
            if r["name"] == "ClinVar":
                r["version"] = "2026-02-01"

    old, new = _mutate(valid_dict, m)
    changes, impacts, claim_impacts, decisions = pipeline(old, new)

    assert impacts[0].impact_domain is ImpactDomain.INTERPRETIVE
    assert decisions[0].decision_type is RevalidationType.CLASSIFICATION_CONCORDANCE_REVIEW
    assert decisions[0].affected_claims == ("CLAIM-CLASS-001",)


# 5. BED file change ---------------------------------------------------------
def test_scenario_bed_file(pipeline, valid_dict):
    def m(d):
        d["assay_scope"]["target_regions_hash"]["value"] = "d" * 64
        d["assay_scope"]["bed_file"]["checksum"]["value"] = "d" * 64

    old, new = _mutate(valid_dict, m)
    changes, impacts, claim_impacts, decisions = pipeline(old, new)

    assert all(c.change_type is ChangeType.PANEL_CHANGED for c in changes)
    assert all(i.impact_domain is ImpactDomain.ANALYTICAL for i in impacts)
    assert all(d.decision_type is RevalidationType.SCOPE_REVIEW_AND_TARGETED for d in decisions)
    # region-coverage claim linkage is not expressible via wiring -> no claims
    assert all(d.affected_claims == () for d in decisions)
    assert any("scope" in e.lower() for d in decisions for e in d.required_evidence)


# 6. QC threshold change -----------------------------------------------------
def test_scenario_qc_threshold(pipeline, valid_dict):
    base = copy.deepcopy(valid_dict)
    _add_qc_claim(base)

    def m(d):
        for t in d["qc"]["thresholds"]:
            if t["metric"] == "minimum_coverage":
                t["threshold"] = 300

    old, new = _mutate(base, m)
    changes, impacts, claim_impacts, decisions = pipeline(old, new)

    assert impacts[0].impact_domain is ImpactDomain.QUALITY
    assert decisions[0].decision_type is RevalidationType.QC_VERIFICATION
    assert decisions[0].affected_claims == ("CLAIM-QC-001",)


# 7. No-op change ------------------------------------------------------------
def test_scenario_noop(pipeline, valid_manifest):
    changes, impacts, claim_impacts, decisions = pipeline(valid_manifest, valid_manifest)
    assert changes == []
    assert impacts == []
    assert claim_impacts == []
    assert decisions == []  # no revalidation required


def test_decision_is_fully_explainable_and_frozen(pipeline, valid_dict):
    old, new = _mutate(valid_dict, lambda d: d["analysis_components"]["variant_caller"].__setitem__("version", "4.6.0.0"))
    _, _, _, decisions = pipeline(old, new)
    d = decisions[0]
    assert d.decision_id and d.change_id and d.rationale
    assert d.decision_type and d.impact_domain
    with pytest.raises(Exception):
        d.decision_type = RevalidationType.NONE  # frozen