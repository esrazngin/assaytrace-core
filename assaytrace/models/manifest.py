"""The root manifest model — the canonical identity card of a clinical assay
pipeline, and the object every downstream module consumes.

Two design points worth highlighting:

1. Envelope vs. content. Fields like `manifest_id`, `generated_at`, and
   `status` describe *the document*; they must NOT influence the assay's
   identity. `content_hash()` therefore hashes only the substantive sections,
   so two manifests generated at different times with identical configuration
   produce the same hash. The change-detection engine compares content hashes.

2. Generic traversability. `iter_components()` / `component_identities()` give
   later modules one uniform way to walk every versioned thing, so the change
   engine never needs per-field special-casing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..validators.integrity import run_all_integrity_checks
from .assay import AssayMetadata
from .claims import AssayClaim
from .common import NonEmptyStr
from .enums import ComponentCategory, ManifestStatus
from .pipeline import (
    AssayScope,
    CoreAnalysisComponents,
    Environment,
    PipelineMetadata,
    ReferenceResources,
)
from .qc import QCConfiguration

# The version of *this schema specification*. Bump on breaking changes so
# future loaders can migrate older manifests deterministically.
MANIFEST_SCHEMA_VERSION = "1.0.0"

# Sections that constitute the assay's technical identity (used for hashing).
_CONTENT_SECTIONS = (
    "assay",
    "pipeline",
    "reference_resources",
    "analysis_components",
    "assay_scope",
    "qc",
    "environment",
    "claims",
)


class AssayManifest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=False,
    )

    # --- Document envelope (provenance of the manifest itself) ---------------
    manifest_schema_version: str = Field(default=MANIFEST_SCHEMA_VERSION)
    manifest_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    generated_by: str | None = None
    status: ManifestStatus = ManifestStatus.DRAFT
    supersedes: UUID | None = Field(
        default=None,
        description="manifest_id of the previously validated manifest this "
        "one replaces; establishes change-control lineage.",
    )
    change_reason: str | None = None
    tags: tuple[str, ...] = Field(default=())

    # --- Assay technical identity (content) ----------------------------------
    assay: AssayMetadata
    pipeline: PipelineMetadata
    reference_resources: ReferenceResources
    analysis_components: CoreAnalysisComponents
    assay_scope: AssayScope
    qc: QCConfiguration
    environment: Environment
    claims: tuple[AssayClaim, ...] = Field(default=())

    notes: str | None = None

    # --- Validation ----------------------------------------------------------
    @model_validator(mode="after")
    def _generated_at_is_tz_aware(self) -> "AssayManifest":
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")
        return self

    @model_validator(mode="after")
    def _referential_integrity(self) -> "AssayManifest":
        errors = run_all_integrity_checks(self)
        if errors:
            raise ValueError(
                "manifest integrity errors:\n  - " + "\n  - ".join(errors)
            )
        return self

    # --- Generic traversal helpers (for Steps 2 & 3) -------------------------
    def iter_components(self) -> list[tuple[str, str]]:
        """Return (identity, version) for every versioned component, uniformly."""
        items: list[tuple[str, str]] = []
        items.append(
            (self.reference_resources.reference_genome.identity,
             self.reference_resources.reference_genome.version)
        )
        for r in self.reference_resources.annotation_resources:
            items.append((r.identity, r.version))
        for c in self.analysis_components.as_tuple():
            items.append((c.identity, c.version))
        return items

    def component_identities(self) -> set[str]:
        return {identity for identity, _ in self.iter_components()}

    def present_categories(self) -> set[ComponentCategory]:
        cats: set[ComponentCategory] = {ComponentCategory.REFERENCE_GENOME}
        for r in self.reference_resources.annotation_resources:
            cats.add(r.category)
        for c in self.analysis_components.as_tuple():
            cats.add(c.category)
        return cats

    # --- Content hashing (for Step 2 change detection) -----------------------
    def content_dict(self) -> dict:
        """Deterministic dict of just the assay's technical identity."""
        return self.model_dump(mode="json", include=set(_CONTENT_SECTIONS))

    def content_hash(self, algorithm: str = "sha256") -> str:
        canonical = json.dumps(
            self.content_dict(), sort_keys=True, separators=(",", ":")
        )
        return hashlib.new(algorithm, canonical.encode("utf-8")).hexdigest()

    @property
    def assay_content_sha256(self) -> str:
        return self.content_hash("sha256")
