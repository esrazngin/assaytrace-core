"""Manifest ingestion framework (Medium Issue #5).

An extensible, deterministic contract for turning external pipeline definitions
(Nextflow, nf-core, DRAGEN, Docker, Git, CWL, WDL, ...) into AssayTrace manifest
fragments. This package defines the *architecture* — adapter contract, result
type, and a registry — not full connectors. Each adapter is responsible for one
source type and declares whether it can handle a given payload.

Design goals: deterministic (no network, no inference at this layer), additive
(does not touch the analysis engines), and pluggable (register an adapter to add
a source). Adapters emit a partial manifest dict plus provenance and warnings;
assembling/validating a full ``AssayManifest`` remains the caller's
responsibility, so ingestion can never silently fabricate a validated manifest.
"""

from .models import IngestionResult, ManifestFragment, SourceType
from .base import ManifestSourceAdapter, IngestionError, NotImplementedAdapter
from .registry import AdapterRegistry, default_registry
from . import adapters

__all__ = [
    "IngestionResult",
    "ManifestFragment",
    "SourceType",
    "ManifestSourceAdapter",
    "IngestionError",
    "NotImplementedAdapter",
    "AdapterRegistry",
    "default_registry",
    "adapters",
]
