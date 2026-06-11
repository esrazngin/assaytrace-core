"""Example: using the manifest ingestion framework (Medium Issue #5).

Run: python -m examples.ingestion_example

Demonstrates the deterministic adapter contract: the GenericManifestAdapter
ingests an already manifest-shaped payload, while the declared roadmap
connectors (Nextflow, DRAGEN, ...) fail loudly until implemented.
"""

from __future__ import annotations

from assaytrace.ingestion import default_registry
from assaytrace.ingestion.base import IngestionError


def main() -> None:
    registry = default_registry()
    print("Available ingestion sources:", [s.value for s in registry.available()])

    payload = {
        "analysis_components": {"variant_caller": {"name": "mutect2", "version": "4.5.0.0"}},
        "environment": {"container": "ghcr.io/lab/pipeline:1.2.3"},
        "qc": {"thresholds": []},
    }
    result = registry.ingest(payload)
    print("\nGeneric ingest:")
    print("  source_type:", result.source_type.value)
    print("  complete:", result.complete)
    print("  provenance:", result.provenance)
    for w in result.warnings:
        print("  warning:", w)

    print("\nRoadmap connector (not yet built):")
    try:
        registry.ingest({"source_type": "dragen"})
    except IngestionError as exc:
        print("  IngestionError:", exc)


if __name__ == "__main__":
    main()
