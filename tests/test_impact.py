from __future__ import annotations

import copy

import pytest

from assaytrace import AssayManifest
from assaytrace.diff import ChangeDetector, ChangeRecord, ChangeType
from assaytrace.impact import ChangeImpactGraph, ImpactDomain
from assaytrace.models.enums import ComponentCategory


@pytest.fixture()
def detector() -> ChangeDetector:
    return ChangeDetector()


@pytest.fixture()
def graph() -> ChangeImpactGraph:
    return ChangeImpactGraph()


def _domain_for(detector, graph, valid_dict, mutate) -> dict[str, ImpactDomain]:
    old = AssayManifest.model_validate(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    mutate(new_d)
    new = AssayManifest.model_validate(new_d)
    changes = detector.compare(old, new)
    impacts = graph.evaluate(changes)
    return {i.change_id: i.impact_domain for i in impacts}


def test_variant_caller_is_analytical(detector, graph, valid_dict):
    def m(d):
        d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"

    domains = list(_domain_for(detector, graph, valid_dict, m).values())
    assert domains == [ImpactDomain.ANALYTICAL]


def test_aligner_is_analytical(detector, graph, valid_dict):
    def m(d):
        d["analysis_components"]["aligner"]["version"] = "2.2.2"

    assert list(_domain_for(detector, graph, valid_dict, m).values()) == [
        ImpactDomain.ANALYTICAL
    ]


def test_reference_genome_is_analytical(detector, graph, valid_dict):
    def m(d):
        d["reference_resources"]["reference_genome"]["version"] = "GRCh38.p15"

    assert list(_domain_for(detector, graph, valid_dict, m).values()) == [
        ImpactDomain.ANALYTICAL
    ]


def test_clinvar_is_interpretive(detector, graph, valid_dict):
    def m(d):
        for r in d["reference_resources"]["annotation_resources"]:
            if r["name"] == "ClinVar":
                r["version"] = "2026-02-01"

    assert list(_domain_for(detector, graph, valid_dict, m).values()) == [
        ImpactDomain.INTERPRETIVE
    ]


def test_transcript_set_is_interpretive(detector, graph, valid_dict):
    def m(d):
        for r in d["reference_resources"]["annotation_resources"]:
            if r["name"] == "MANE Select":
                r["version"] = "1.4"

    assert list(_domain_for(detector, graph, valid_dict, m).values()) == [
        ImpactDomain.INTERPRETIVE
    ]


def test_qc_change_is_quality(detector, graph, valid_dict):
    def m(d):
        for t in d["qc"]["thresholds"]:
            if t["metric"] == "minimum_coverage":
                t["threshold"] = 250

    assert list(_domain_for(detector, graph, valid_dict, m).values()) == [
        ImpactDomain.QUALITY
    ]


def test_environment_is_infrastructure(detector, graph, valid_dict):
    def m(d):
        d["environment"]["container_version"] = "2.4.0"

    assert list(_domain_for(detector, graph, valid_dict, m).values()) == [
        ImpactDomain.INFRASTRUCTURE
    ]


def test_pipeline_is_infrastructure(detector, graph, valid_dict):
    def m(d):
        d["pipeline"]["workflow_version"] = "25.04.0"

    assert list(_domain_for(detector, graph, valid_dict, m).values()) == [
        ImpactDomain.INFRASTRUCTURE
    ]


def test_panel_is_analytical(detector, graph, valid_dict):
    def m(d):
        d["assay_scope"]["target_regions_hash"]["value"] = "e" * 64
        d["assay_scope"]["bed_file"]["checksum"]["value"] = "e" * 64

    assert set(_domain_for(detector, graph, valid_dict, m).values()) == {
        ImpactDomain.ANALYTICAL
    }


def test_claim_change_is_documentation(detector, graph, valid_dict):
    def m(d):
        d["claims"][0]["description"] = "Clarified wording only."

    assert list(_domain_for(detector, graph, valid_dict, m).values()) == [
        ImpactDomain.DOCUMENTATION
    ]


def test_unmapped_category_defaults_with_disclosed_rationale(graph):
    """A future/unmapped component category falls back to analytical, and the
    rationale must disclose that a default — not an explicit rule — was used."""
    change = ChangeRecord(
        change_id="component_version_changed|other:mystery-tool",
        change_type=ChangeType.COMPONENT_VERSION_CHANGED,
        category=ComponentCategory.OTHER,
        component_identity="other:mystery-tool",
        old_value="1.0",
        new_value="2.0",
        description="x",
    )
    [impact] = graph.evaluate([change])
    assert impact.impact_domain is ImpactDomain.ANALYTICAL
    assert "default" in impact.rationale.lower()


def test_rationale_is_traceable(detector, graph, valid_dict):
    def m(d):
        d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"

    old = AssayManifest.model_validate(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    m(new_d)
    new = AssayManifest.model_validate(new_d)
    impacts = graph.evaluate(detector.compare(old, new))
    assert "CATEGORY_IMPACT" in impacts[0].rationale


def test_empty_changes_yield_no_impacts(graph):
    assert graph.evaluate([]) == []


def test_defensive_none_path_for_unmapped_noncomponent(graph):
    """A record with no category whose change_type is not in CHANGE_TYPE_IMPACT
    (a malformed/edge record) is classified NONE with a disclosing rationale."""
    edge = ChangeRecord(
        change_id="component_version_changed|orphan",
        change_type=ChangeType.COMPONENT_VERSION_CHANGED,  # component type but no category
        category=None,
        component_identity="orphan",
        old_value="1",
        new_value="2",
        description="edge",
    )
    [impact] = graph.evaluate([edge])
    assert impact.impact_domain is ImpactDomain.NONE
    assert "no impact rule" in impact.rationale.lower()