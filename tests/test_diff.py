from __future__ import annotations

import copy

import pytest

from assaytrace import AssayManifest
from assaytrace.diff import ChangeDetector, ChangeType


@pytest.fixture()
def detector() -> ChangeDetector:
    return ChangeDetector()


def _manifest(d: dict) -> AssayManifest:
    return AssayManifest.model_validate(d)


def _ids_by_type(changes, change_type: ChangeType):
    return [c for c in changes if c.change_type is change_type]


# 1. Variant caller version update -------------------------------------------
def test_variant_caller_version_update(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"
    new = _manifest(new_d)

    changes = detector.compare(old, new)
    vc = _ids_by_type(changes, ChangeType.COMPONENT_VERSION_CHANGED)
    assert len(vc) == 1
    rec = vc[0]
    assert rec.component_identity == "variant_caller:mutect2"
    assert rec.old_value == "4.5.0.0"
    assert rec.new_value == "4.6.0.0"
    assert rec.category.value == "variant_caller"


# 2. Aligner version update --------------------------------------------------
def test_aligner_version_update(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["analysis_components"]["aligner"]["version"] = "2.2.2"
    new = _manifest(new_d)

    changes = detector.compare(old, new)
    vc = _ids_by_type(changes, ChangeType.COMPONENT_VERSION_CHANGED)
    assert len(vc) == 1
    assert vc[0].component_identity == "aligner:bwa-mem2"


# 3. ClinVar (annotation resource) version update ----------------------------
def test_clinvar_version_update(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    for r in new_d["reference_resources"]["annotation_resources"]:
        if r["name"] == "ClinVar":
            r["version"] = "2026-01-01"
    new = _manifest(new_d)

    changes = detector.compare(old, new)
    vc = _ids_by_type(changes, ChangeType.COMPONENT_VERSION_CHANGED)
    assert len(vc) == 1
    assert vc[0].component_identity == "annotation:clinvar"
    assert vc[0].category.value == "annotation"


# 4. QC threshold change -----------------------------------------------------
def test_qc_threshold_change(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    for t in new_d["qc"]["thresholds"]:
        if t["metric"] == "minimum_coverage":
            t["threshold"] = 300
    new = _manifest(new_d)

    changes = detector.compare(old, new)
    qc = _ids_by_type(changes, ChangeType.QC_THRESHOLD_CHANGED)
    assert len(qc) == 1
    assert qc[0].component_identity == "qc:minimum_coverage"
    assert qc[0].old_value["threshold"] == 500
    assert qc[0].new_value["threshold"] == 300


# 5. BED hash change ---------------------------------------------------------
def test_bed_hash_change(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["assay_scope"]["target_regions_hash"]["value"] = "d" * 64
    new_d["assay_scope"]["bed_file"]["checksum"]["value"] = "d" * 64
    new = _manifest(new_d)

    changes = detector.compare(old, new)
    panel = _ids_by_type(changes, ChangeType.PANEL_CHANGED)
    identities = {c.component_identity for c in panel}
    assert "assay_scope:bed_file" in identities
    assert "assay_scope:target_regions_hash" in identities


# 6. Component addition ------------------------------------------------------
def test_component_addition(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["analysis_components"]["additional_components"].append(
        {
            "category": "read_trimmer",
            "name": "fastp",
            "version": "0.23.4",
            "vendor": None,
            "digest": None,
            "parameters": {},
            "purpose": None,
        }
    )
    new = _manifest(new_d)

    changes = detector.compare(old, new)
    added = _ids_by_type(changes, ChangeType.COMPONENT_ADDED)
    assert len(added) == 1
    assert added[0].component_identity == "read_trimmer:fastp"
    assert added[0].new_value == "0.23.4"


# 7. Component removal -------------------------------------------------------
def test_component_removal(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["analysis_components"]["sv_caller"] = None
    # remove the claim that depends on sv? none depends on sv here; safe.
    new = _manifest(new_d)

    changes = detector.compare(old, new)
    removed = _ids_by_type(changes, ChangeType.COMPONENT_REMOVED)
    assert len(removed) == 1
    assert removed[0].component_identity == "sv_caller:manta"


# 8. No-op comparison --------------------------------------------------------
def test_noop_comparison(detector, valid_manifest):
    changes = detector.compare(valid_manifest, valid_manifest)
    assert changes == []


# Additional coverage --------------------------------------------------------
def test_parameters_change(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["analysis_components"]["variant_caller"]["parameters"]["min_base_quality_score"] = 30
    new = _manifest(new_d)
    changes = detector.compare(old, new)
    params = _ids_by_type(changes, ChangeType.COMPONENT_PARAMETERS_CHANGED)
    assert len(params) == 1
    assert params[0].component_identity == "variant_caller:mutect2"


def test_pipeline_change(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["pipeline"]["workflow_version"] = "25.04.0"
    new = _manifest(new_d)
    changes = detector.compare(old, new)
    pc = _ids_by_type(changes, ChangeType.PIPELINE_CHANGED)
    assert len(pc) == 1
    assert pc[0].component_identity == "pipeline:workflow_version"


def test_environment_change(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["environment"]["git_commit"] = "abcdef1"
    new = _manifest(new_d)
    changes = detector.compare(old, new)
    ec = _ids_by_type(changes, ChangeType.ENVIRONMENT_CHANGED)
    assert len(ec) == 1
    assert ec[0].component_identity == "environment:git_commit"


def test_claim_change_lists_fields(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["claims"][0]["title"] = "Updated SNV sensitivity claim"
    new = _manifest(new_d)
    changes = detector.compare(old, new)
    cc = _ids_by_type(changes, ChangeType.CLAIM_CHANGED)
    assert len(cc) == 1
    assert "title" in cc[0].description


def test_determinism_and_sorting(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["analysis_components"]["aligner"]["version"] = "9.9.9"
    new_d["analysis_components"]["variant_caller"]["version"] = "9.9.9"
    new = _manifest(new_d)
    first = detector.compare(old, new)
    second = detector.compare(old, new)
    assert [c.change_id for c in first] == [c.change_id for c in second]
    assert [c.change_id for c in first] == sorted(c.change_id for c in first)


def test_change_records_are_frozen(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["analysis_components"]["aligner"]["version"] = "2.2.9"
    new = _manifest(new_d)
    rec = detector.compare(old, new)[0]
    with pytest.raises(Exception):
        rec.old_value = "tampered"  # frozen


def test_qc_threshold_added_and_removed(detector, valid_dict):
    old = _manifest(valid_dict)
    # remove maximum_contamination, add a new metric
    new_d = copy.deepcopy(valid_dict)
    new_d["qc"]["thresholds"] = [
        t for t in new_d["qc"]["thresholds"] if t["metric"] != "maximum_contamination"
    ]
    new_d["qc"]["thresholds"].append(
        {
            "metric": "ts_tv_ratio",
            "comparator": ">=",
            "threshold": 2.0,
            "unit": None,
            "severity": "warning",
            "applies_to": [],
            "description": None,
        }
    )
    new = _manifest(new_d)
    changes = detector.compare(old, new)
    added = _ids_by_type(changes, ChangeType.QC_THRESHOLD_ADDED)
    removed = _ids_by_type(changes, ChangeType.QC_THRESHOLD_REMOVED)
    assert {c.component_identity for c in added} == {"qc:ts_tv_ratio"}
    assert {c.component_identity for c in removed} == {"qc:maximum_contamination"}


def test_claim_added_and_removed(detector, valid_dict):
    old = _manifest(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    # remove the CNV claim (and its caller dep is fine to keep)
    new_d["claims"] = [c for c in new_d["claims"] if c["claim_id"] != "CLAIM-CNV-001"]
    new = _manifest(new_d)
    changes = detector.compare(old, new)
    removed = _ids_by_type(changes, ChangeType.CLAIM_REMOVED)
    assert {c.component_identity for c in removed} == {"claim:CLAIM-CNV-001"}

    # reverse direction: old has fewer claims -> added
    changes_rev = detector.compare(new, old)
    added = _ids_by_type(changes_rev, ChangeType.CLAIM_ADDED)
    assert {c.component_identity for c in added} == {"claim:CLAIM-CNV-001"}