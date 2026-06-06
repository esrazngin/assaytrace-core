"""The structural sections of a pipeline manifest other than assay metadata
and claims: pipeline/engine identity, reference resources, the core analysis
components, the assay's genomic scope, and the execution environment.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
    Checksum,
    FileResource,
    GenomeReference,
    NonEmptyStr,
    ResourceComponent,
    SoftwareComponent,
)
from .enums import (
    ComponentCategory,
    ContainerRuntime,
    SequencingScope,
    WorkflowEngine,
)

_BASE_CONFIG = ConfigDict(
    frozen=True, extra="forbid", str_strip_whitespace=True, use_enum_values=False
)


class PipelineMetadata(BaseModel):
    model_config = _BASE_CONFIG

    pipeline_name: NonEmptyStr
    pipeline_version: NonEmptyStr
    workflow_engine: WorkflowEngine
    workflow_version: NonEmptyStr


class ReferenceResources(BaseModel):
    """Reference genome plus all versioned data resources (annotation DBs,
    known-sites VCFs, transcript sets)."""

    model_config = _BASE_CONFIG

    reference_genome: GenomeReference
    annotation_resources: tuple[ResourceComponent, ...] = Field(default=())

    @model_validator(mode="after")
    def _annotation_categories(self) -> "ReferenceResources":
        allowed = {
            ComponentCategory.ANNOTATION,
            ComponentCategory.KNOWN_SITES,
            ComponentCategory.TRANSCRIPT_SET,
        }
        for r in self.annotation_resources:
            if r.category not in allowed:
                raise ValueError(
                    f"annotation_resources entry '{r.name}' has category "
                    f"'{r.category.value}', expected one of {sorted(c.value for c in allowed)}"
                )
        return self


class CoreAnalysisComponents(BaseModel):
    """The analysis tools. Required slots (aligner, variant_caller) are typed
    explicitly; optional structural callers are nullable; anything else lives
    in `additional_components` so the schema never blocks an unusual pipeline."""

    model_config = _BASE_CONFIG

    aligner: SoftwareComponent
    variant_caller: SoftwareComponent
    cnv_caller: SoftwareComponent | None = None
    sv_caller: SoftwareComponent | None = None
    additional_components: tuple[SoftwareComponent, ...] = Field(default=())

    @model_validator(mode="after")
    def _slot_categories_match(self) -> "CoreAnalysisComponents":
        expected = {
            "aligner": ComponentCategory.ALIGNER,
            "variant_caller": ComponentCategory.VARIANT_CALLER,
            "cnv_caller": ComponentCategory.CNV_CALLER,
            "sv_caller": ComponentCategory.SV_CALLER,
        }
        for attr, cat in expected.items():
            comp = getattr(self, attr)
            if comp is not None and comp.category != cat:
                raise ValueError(
                    f"'{attr}' slot must hold a component with category "
                    f"'{cat.value}', got '{comp.category.value}'"
                )
        return self

    def as_tuple(self) -> tuple[SoftwareComponent, ...]:
        core = [self.aligner, self.variant_caller]
        if self.cnv_caller is not None:
            core.append(self.cnv_caller)
        if self.sv_caller is not None:
            core.append(self.sv_caller)
        core.extend(self.additional_components)
        return tuple(core)


class AssayScope(BaseModel):
    """What genomic territory the assay interrogates."""

    model_config = _BASE_CONFIG

    sequencing_scope: SequencingScope
    panel_name: str | None = None
    panel_version: str | None = None
    bed_file: FileResource | None = None
    target_regions_hash: Checksum | None = Field(
        default=None,
        description="Digest of the canonical target-region set; enables fast "
        "integrity comparison without re-parsing the BED.",
    )

    @model_validator(mode="after")
    def _panel_requires_targets(self) -> "AssayScope":
        if self.sequencing_scope in {
            SequencingScope.TARGETED_PANEL,
            SequencingScope.HOTSPOT,
        }:
            if self.bed_file is None and self.target_regions_hash is None:
                raise ValueError(
                    "targeted/hotspot assays must declare a bed_file or "
                    "target_regions_hash to anchor their scope"
                )
        return self


class Environment(BaseModel):
    """Execution provenance: how and from what code the pipeline was built."""

    model_config = _BASE_CONFIG

    container_runtime: ContainerRuntime
    container_image: str | None = Field(
        default=None, description="Image reference, e.g. registry/org/image."
    )
    container_version: str | None = Field(
        default=None, description="Image tag, e.g. '1.4.2'."
    )
    image_digest: Checksum | None = None
    git_commit: str | None = Field(
        default=None, description="Full or abbreviated commit SHA of the pipeline repo."
    )
    build_date: date | None = None

    @model_validator(mode="after")
    def _validate_git_commit(self) -> "Environment":
        if self.git_commit is not None:
            c = self.git_commit.strip().lower()
            if not (7 <= len(c) <= 40) or any(ch not in "0123456789abcdef" for ch in c):
                raise ValueError(
                    "git_commit must be a 7-40 character hexadecimal SHA"
                )
        return self

    @property
    def container_reference(self) -> str | None:
        if self.container_image and self.container_version:
            return f"{self.container_image}:{self.container_version}"
        return self.container_image
