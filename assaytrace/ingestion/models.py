"""Contracts for manifest ingestion."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """The kind of external pipeline definition an adapter consumes."""

    NEXTFLOW = "nextflow"
    NF_CORE = "nf_core"
    DRAGEN = "dragen"
    DOCKER = "docker"
    GIT = "git"
    CWL = "cwl"
    WDL = "wdl"
    GENERIC = "generic"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class ManifestFragment(BaseModel):
    """A partial manifest contribution produced by an adapter.

    Deliberately permissive (plain dicts of component / environment / qc data),
    because the adapter's job is extraction, not validation. The caller merges
    fragments and validates the assembled ``AssayManifest``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    analysis_components: dict = Field(default_factory=dict)
    reference_resources: dict = Field(default_factory=dict)
    qc: dict = Field(default_factory=dict)
    environment: dict = Field(default_factory=dict)
    extras: dict = Field(default_factory=dict)


class IngestionResult(BaseModel):
    """Deterministic output of an ingestion attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_type: SourceType
    fragment: ManifestFragment
    provenance: dict = Field(
        default_factory=dict,
        description="How the fragment was derived (source path, tool, digest).",
    )
    warnings: tuple[str, ...] = ()
    complete: bool = Field(
        default=False,
        description="True only if the adapter believes the fragment is a full, "
        "self-sufficient manifest; otherwise the caller must supply the rest.",
    )
