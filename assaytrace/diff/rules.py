"""Extraction rules for change detection.

These pure functions define *how a manifest is decomposed into comparable
units* (components, QC thresholds, scope aspects, pipeline aspects,
environment aspects, claims). Keeping them here — separate from the detector's
orchestration — means the "what counts as a unit and how is it keyed" policy is
inspectable and testable in isolation.

The component map reuses the Step-1 public traversal (``as_tuple()`` and the
public ``reference_resources`` fields); it does not reach into private state
and requires no schema change.
"""

from __future__ import annotations

from typing import Any

from ..models.common import GenomeReference, ResourceComponent, SoftwareComponent
from ..models.manifest import AssayManifest

# A versioned component is anything exposing ``identity`` and ``version``.
VersionedComponent = SoftwareComponent | ResourceComponent | GenomeReference


def component_map(manifest: AssayManifest) -> dict[str, VersionedComponent]:
    """All versioned components keyed by their stable Step-1 identity.

    Uniform across software tools, data resources, and the reference genome, so
    detection logic never branches on which kind of component it is — and any
    future component type is picked up automatically.
    """
    result: dict[str, VersionedComponent] = {}
    rr = manifest.reference_resources
    result[rr.reference_genome.identity] = rr.reference_genome
    for resource in rr.annotation_resources:
        result[resource.identity] = resource
    for comp in manifest.analysis_components.as_tuple():
        result[comp.identity] = comp
    return result


def component_parameters(component: VersionedComponent) -> dict[str, Any]:
    """Runtime parameters for a component, or empty if it has none
    (resources and the reference genome carry no parameters)."""
    return dict(getattr(component, "parameters", {}) or {})


def qc_threshold_map(manifest: AssayManifest) -> dict[str, Any]:
    """QC thresholds keyed by 'qc:<metric>' (plus scope when variant-scoped).

    Value is a stable comparable tuple of the threshold's defining attributes,
    so any change to comparator/value/unit/severity is detectable.
    """
    out: dict[str, Any] = {}
    for t in manifest.qc.thresholds:
        scope = "" if not t.applies_to else "[" + ",".join(v.value for v in t.applies_to) + "]"
        key = f"qc:{t.metric}{scope}"
        out[key] = {
            "comparator": t.comparator.value,
            "threshold": t.threshold,
            "unit": t.unit,
            "severity": t.severity.value,
        }
    return out


def scope_aspect_map(manifest: AssayManifest) -> dict[str, Any]:
    """Comparable aspects of the assay scope (panel + targets)."""
    s = manifest.assay_scope
    bed_digest = None
    if s.bed_file is not None and s.bed_file.checksum is not None:
        bed_digest = str(s.bed_file.checksum)
    target_digest = str(s.target_regions_hash) if s.target_regions_hash else None
    return {
        "assay_scope:sequencing_scope": s.sequencing_scope.value,
        "assay_scope:panel_name": s.panel_name,
        "assay_scope:panel_version": s.panel_version,
        "assay_scope:bed_file": bed_digest,
        "assay_scope:target_regions_hash": target_digest,
    }


def pipeline_aspect_map(manifest: AssayManifest) -> dict[str, Any]:
    p = manifest.pipeline
    return {
        "pipeline:pipeline_name": p.pipeline_name,
        "pipeline:pipeline_version": p.pipeline_version,
        "pipeline:workflow_engine": p.workflow_engine.value,
        "pipeline:workflow_version": p.workflow_version,
    }


def environment_aspect_map(manifest: AssayManifest) -> dict[str, Any]:
    e = manifest.environment
    return {
        "environment:container_runtime": e.container_runtime.value,
        "environment:container_image": e.container_image,
        "environment:container_version": e.container_version,
        "environment:image_digest": str(e.image_digest) if e.image_digest else None,
        "environment:git_commit": e.git_commit,
        "environment:build_date": e.build_date.isoformat() if e.build_date else None,
    }


def claim_map(manifest: AssayManifest) -> dict[str, dict[str, Any]]:
    """Claims keyed by 'claim:<claim_id>', value = full serialized claim."""
    return {f"claim:{c.claim_id}": c.model_dump(mode="json") for c in manifest.claims}