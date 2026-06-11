"""Example adapter plus the roadmap of declared connectors.

``GenericManifestAdapter`` is a fully-working reference implementation: given a
payload that already carries manifest-shaped sections, it extracts them into an
``IngestionResult`` deterministically. The roadmap adapters (Nextflow, nf-core,
DRAGEN, Docker, Git, CWL, WDL) are declared via ``NotImplementedAdapter`` so the
framework advertises intended sources without pretending to support them yet.
"""

from __future__ import annotations

from .base import ManifestSourceAdapter, NotImplementedAdapter
from .models import IngestionResult, ManifestFragment, SourceType

_FRAGMENT_KEYS = ("analysis_components", "reference_resources", "qc", "environment")


class GenericManifestAdapter(ManifestSourceAdapter):
    """Reference adapter: ingests an already manifest-shaped dict.

    Useful on its own (callers that can produce manifest sections from their own
    tooling) and as a worked example of the contract for real connectors.
    """

    source_type = SourceType.GENERIC

    def can_handle(self, payload: dict) -> bool:
        if not isinstance(payload, dict):
            return False
        if payload.get("source_type") == SourceType.GENERIC.value:
            return True
        return any(k in payload for k in _FRAGMENT_KEYS)

    def ingest(self, payload: dict) -> IngestionResult:
        fragment = ManifestFragment(
            analysis_components=dict(payload.get("analysis_components", {})),
            reference_resources=dict(payload.get("reference_resources", {})),
            qc=dict(payload.get("qc", {})),
            environment=dict(payload.get("environment", {})),
            extras=dict(payload.get("extras", {})),
        )
        present = [k for k in _FRAGMENT_KEYS if payload.get(k)]
        warnings: list[str] = []
        for k in _FRAGMENT_KEYS:
            if not payload.get(k):
                warnings.append(f"No '{k}' section supplied; caller must provide it.")
        return IngestionResult(
            source_type=SourceType.GENERIC,
            fragment=fragment,
            provenance={"sections": present, "adapter": "generic"},
            warnings=tuple(warnings),
            complete=len(present) == len(_FRAGMENT_KEYS),
        )


def roadmap_adapters() -> list[ManifestSourceAdapter]:
    """Declared-but-unbuilt connectors, advertised by the framework."""
    return [
        NotImplementedAdapter(SourceType.NEXTFLOW),
        NotImplementedAdapter(SourceType.NF_CORE),
        NotImplementedAdapter(SourceType.DRAGEN),
        NotImplementedAdapter(SourceType.DOCKER),
        NotImplementedAdapter(SourceType.GIT),
        NotImplementedAdapter(SourceType.CWL),
        NotImplementedAdapter(SourceType.WDL),
    ]
