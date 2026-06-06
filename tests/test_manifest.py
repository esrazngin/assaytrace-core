from __future__ import annotations

import copy

from assaytrace import AssayManifest


def test_baseline_is_valid(valid_manifest: AssayManifest) -> None:
    assert valid_manifest.assay.assay_name == "SolidTumor500"
    assert valid_manifest.assay_content_sha256


def test_component_traversal_is_uniform(valid_manifest: AssayManifest) -> None:
    identities = valid_manifest.component_identities()
    # reference genome + 5 annotation resources + 4 software (aligner, caller,
    # cnv, sv) + 1 additional filter
    assert "variant_caller:mutect2" in identities
    assert "annotation:clinvar" in identities
    assert "reference_genome:grch38" in identities
    assert len(identities) == 1 + 5 + 5


def test_content_hash_ignores_document_envelope(valid_dict: dict) -> None:
    """Two manifests differing only in envelope metadata must hash identically.
    This is the property the change-detection engine relies on."""
    a = AssayManifest.model_validate(valid_dict)

    other = copy.deepcopy(valid_dict)
    other["manifest_id"] = "22222222-2222-2222-2222-222222222222"
    other["generated_at"] = "2030-06-01T00:00:00+00:00"
    other["generated_by"] = "someone-else"
    other["status"] = "draft"
    other["tags"] = ["different"]
    b = AssayManifest.model_validate(other)

    assert a.content_hash() == b.content_hash()
    assert a.manifest_id != b.manifest_id


def test_content_hash_changes_when_component_version_changes(valid_dict: dict) -> None:
    a = AssayManifest.model_validate(valid_dict)
    other = copy.deepcopy(valid_dict)
    other["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"
    b = AssayManifest.model_validate(other)
    assert a.content_hash() != b.content_hash()


def test_present_categories(valid_manifest: AssayManifest) -> None:
    from assaytrace.models.enums import ComponentCategory

    cats = valid_manifest.present_categories()
    assert ComponentCategory.CNV_CALLER in cats
    assert ComponentCategory.TRANSCRIPT_SET in cats
