from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from assaytrace import AssayManifest


def _expect_error(d: dict, *, contains: str) -> None:
    with pytest.raises(ValidationError) as exc:
        AssayManifest.model_validate(d)
    assert contains in str(exc.value)


def test_claim_dependency_must_resolve(valid_dict: dict) -> None:
    valid_dict["claims"][0]["depends_on_components"] = ["variant_caller:does-not-exist"]
    _expect_error(valid_dict, contains="not present in the pipeline")


def test_claim_unresolved_category(valid_dict: dict) -> None:
    # depend on a category that isn't in the pipeline
    valid_dict["claims"][0]["depends_on_categories"].append("basecaller")
    _expect_error(valid_dict, contains="not present")


def test_cnv_claim_requires_cnv_caller(valid_dict: dict) -> None:
    valid_dict["analysis_components"]["cnv_caller"] = None
    # CLAIM-CNV-001 depends on cnv_caller:cnvkit -> both integrity rules fire
    _expect_error(valid_dict, contains="cnv_caller")


def test_somatic_requires_vaf_threshold(valid_dict: dict) -> None:
    valid_dict["qc"]["thresholds"] = [
        t for t in valid_dict["qc"]["thresholds"] if t["metric"] != "minimum_vaf"
    ]
    _expect_error(valid_dict, contains="minimum_vaf")


def test_duplicate_claim_ids(valid_dict: dict) -> None:
    dup = copy.deepcopy(valid_dict["claims"][0])
    valid_dict["claims"].append(dup)
    _expect_error(valid_dict, contains="duplicate claim_id")


def test_slot_category_mismatch(valid_dict: dict) -> None:
    valid_dict["analysis_components"]["aligner"]["category"] = "variant_caller"
    _expect_error(valid_dict, contains="aligner")


def test_bad_checksum_length(valid_dict: dict) -> None:
    valid_dict["reference_resources"]["reference_genome"]["checksum"]["value"] = "abc123"
    _expect_error(valid_dict, contains="hex chars")


def test_targeted_panel_requires_targets(valid_dict: dict) -> None:
    valid_dict["assay_scope"]["bed_file"] = None
    valid_dict["assay_scope"]["target_regions_hash"] = None
    _expect_error(valid_dict, contains="bed_file or target_regions_hash")


def test_invalid_git_commit(valid_dict: dict) -> None:
    valid_dict["environment"]["git_commit"] = "not-a-sha"
    _expect_error(valid_dict, contains="git_commit")


def test_extra_fields_forbidden(valid_dict: dict) -> None:
    valid_dict["unexpected_field"] = 123
    _expect_error(valid_dict, contains="unexpected_field")


def test_proportion_metric_bounds(valid_dict: dict) -> None:
    valid_dict["claims"][0]["claimed_performance"][0]["value"] = 1.5
    _expect_error(valid_dict, contains="proportion")


def test_naive_datetime_rejected(valid_dict: dict) -> None:
    valid_dict["generated_at"] = "2026-01-15T09:00:00"  # no tzinfo
    _expect_error(valid_dict, contains="timezone-aware")


def test_duplicate_qc_metric_scope(valid_dict: dict) -> None:
    dup = copy.deepcopy(valid_dict["qc"]["thresholds"][0])
    valid_dict["qc"]["thresholds"].append(dup)
    _expect_error(valid_dict, contains="duplicate QC threshold")
