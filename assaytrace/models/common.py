"""Reusable, leaf-level building blocks.

Design intent: *every versioned thing in the manifest reduces to a small
number of uniform shapes* (`SoftwareComponent`, `ResourceComponent`,
`GenomeReference`). The change-detection engine can then walk a manifest
generically by `identity` instead of needing bespoke logic per field.

All models are frozen: a manifest is an immutable identity card. Immutability
also makes components hashable and safe to put in sets for integrity checks.
"""

from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import ComponentCategory, HashAlgorithm, ReferenceGenomeBuild

_HEX_RE = re.compile(r"^[0-9a-f]+$")

# A non-empty, whitespace-trimmed string used throughout for names/versions.
NonEmptyStr = Annotated[str, Field(min_length=1)]

_BASE_CONFIG = ConfigDict(
    frozen=True,
    extra="forbid",
    str_strip_whitespace=True,
    use_enum_values=False,
)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


class Checksum(BaseModel):
    """A cryptographic digest of a file or artifact, for integrity comparison."""

    model_config = _BASE_CONFIG

    algorithm: HashAlgorithm
    value: str

    @field_validator("value")
    @classmethod
    def _normalize_and_check_hex(cls, v: str) -> str:
        v = v.strip().lower()
        if not _HEX_RE.match(v):
            raise ValueError("checksum value must be lowercase hexadecimal")
        return v

    @field_validator("value")
    @classmethod
    def _length_matches_algorithm(cls, v: str, info) -> str:  # type: ignore[no-untyped-def]
        algo: HashAlgorithm | None = info.data.get("algorithm")
        if algo is not None and len(v) != algo.hex_length:
            raise ValueError(
                f"{algo.value} digest must be {algo.hex_length} hex chars, got {len(v)}"
            )
        return v

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.algorithm.value}:{self.value}"


class FileResource(BaseModel):
    """A file the assay depends on (e.g., a BED file), referenced by content
    digest rather than path so integrity survives relocation."""

    model_config = _BASE_CONFIG

    path: NonEmptyStr
    checksum: Checksum | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    line_count: int | None = Field(default=None, ge=0)
    description: str | None = None


class SoftwareComponent(BaseModel):
    """An executable, versioned analysis tool (aligner, caller, filter, ...).

    `identity` is the stable key the change-impact graph and claim-dependency
    resolution use. Two manifests are compared component-by-component on it.
    """

    model_config = _BASE_CONFIG

    category: ComponentCategory
    name: NonEmptyStr
    version: NonEmptyStr
    vendor: str | None = None
    digest: Checksum | None = Field(
        default=None,
        description="Digest of the binary/image, when pinned.",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Tool-specific runtime parameters that affect behavior. "
            "Kept as an open map for extensibility; the change engine diffs it deeply."
        ),
    )
    purpose: str | None = None

    @property
    def identity(self) -> str:
        return f"{self.category.value}:{_slugify(self.name)}"


class ResourceComponent(BaseModel):
    """A versioned data resource (annotation DB, known-sites VCF, transcript
    set). Versioned the same way as software so it diffs uniformly, but its
    'version' is typically a release tag or date string."""

    model_config = _BASE_CONFIG

    category: ComponentCategory
    name: NonEmptyStr
    version: NonEmptyStr
    source: str | None = Field(default=None, description="Provider / URL / DOI.")
    genome_build: ReferenceGenomeBuild | None = None
    checksum: Checksum | None = None
    file: FileResource | None = None
    description: str | None = None

    @property
    def identity(self) -> str:
        return f"{self.category.value}:{_slugify(self.name)}"


class GenomeReference(BaseModel):
    """The reference genome assembly the pipeline is built against."""

    model_config = _BASE_CONFIG

    build: ReferenceGenomeBuild
    version: NonEmptyStr = Field(
        description=(
            "Specific assembly/patch identifier, e.g. 'GRCh38.p14' "
            "or an analysis-set tag."
        )
    )
    source: str | None = None
    checksum: Checksum | None = None

    @property
    def category(self) -> ComponentCategory:
        return ComponentCategory.REFERENCE_GENOME

    @property
    def identity(self) -> str:
        return (
            f"{ComponentCategory.REFERENCE_GENOME.value}:"
            f"{_slugify(self.build.value)}"
        )