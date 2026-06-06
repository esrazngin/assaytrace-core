"""End-to-end demonstration of the manifest API.

Run from the repo root:  python -m examples.demo
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from assaytrace import AssayManifest, dump_manifest, load_manifest

EXAMPLES = Path(__file__).resolve().parent


def main() -> None:
    # 1. Load + validate (validation happens during construction) ------------
    manifest = load_manifest(EXAMPLES / "manifest.json")
    print(f"Loaded assay: {manifest.assay.assay_name} v{manifest.assay.assay_version}")
    print(f"Status: {manifest.status.value} | schema {manifest.manifest_schema_version}")

    # 2. Stable assay-identity hash (ignores document envelope) --------------
    print(f"Assay content sha256: {manifest.content_hash()}")

    # 3. Generic component traversal (what Step 2/3 will consume) ------------
    print("\nVersioned components:")
    for identity, version in manifest.iter_components():
        print(f"  {identity:<38} {version}")

    # 4. Claim -> dependency wiring (what Step 3 maps changes onto) ----------
    print("\nClaims and their declared dependencies:")
    for claim in manifest.claims:
        cats = ", ".join(c.value for c in claim.depends_on_categories) or "-"
        comps = ", ".join(claim.depends_on_components) or "-"
        print(f"  {claim.claim_id} [{claim.claim_type.value}]")
        print(f"      categories: {cats}")
        print(f"      components: {comps}")

    # 5. Serialize back out (round-trips by content hash) --------------------
    out = EXAMPLES / "_roundtrip.yaml"
    dump_manifest(manifest, out)
    reloaded = load_manifest(out)
    assert reloaded.content_hash() == manifest.content_hash()
    out.unlink()
    print("\nRound-trip OK (content hash preserved).")

    # 6. Validation failure is explicit and aggregated -----------------------
    broken = manifest.model_dump(mode="json")
    broken["analysis_components"]["cnv_caller"] = None  # but CLAIM-CNV-001 needs it
    try:
        AssayManifest.model_validate(broken)
    except ValidationError as exc:
        print(f"\nExpected validation failure caught ({exc.error_count()} error(s)):")
        print("  ", str(exc).splitlines()[-2].strip())


if __name__ == "__main__":
    main()
