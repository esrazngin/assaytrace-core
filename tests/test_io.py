from __future__ import annotations

from pathlib import Path

import pytest

from assaytrace import AssayManifest, dump_manifest, load_manifest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.mark.parametrize("name", ["manifest.json", "manifest.yaml"])
def test_load_examples(name: str) -> None:
    m = load_manifest(EXAMPLES / name)
    assert isinstance(m, AssayManifest)
    assert m.assay.assay_version == "2.3.0"


def test_json_yaml_equivalent_content_hash() -> None:
    j = load_manifest(EXAMPLES / "manifest.json")
    y = load_manifest(EXAMPLES / "manifest.yaml")
    assert j.content_hash() == y.content_hash()


def test_round_trip(tmp_path: Path) -> None:
    original = load_manifest(EXAMPLES / "manifest.json")
    out = tmp_path / "rt.json"
    dump_manifest(original, out)
    reloaded = load_manifest(out)
    assert reloaded.content_hash() == original.content_hash()


def test_round_trip_yaml(tmp_path: Path) -> None:
    original = load_manifest(EXAMPLES / "manifest.json")
    out = tmp_path / "rt.yaml"
    dump_manifest(original, out)
    reloaded = load_manifest(out)
    assert reloaded.content_hash() == original.content_hash()


def test_unsupported_extension(tmp_path: Path) -> None:
    bad = tmp_path / "manifest.txt"
    bad.write_text("nope")
    with pytest.raises(ValueError, match="unsupported"):
        load_manifest(bad)
