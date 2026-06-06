"""Assay-level identity and regulatory context."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from .common import NonEmptyStr
from .enums import AssayType, IntendedUse, RegulatoryContext

_BASE_CONFIG = ConfigDict(
    frozen=True, extra="forbid", str_strip_whitespace=True, use_enum_values=False
)

# Permissive version token: accepts semver and common lab schemes (v1, 1.2-rc1).
VersionStr = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._\-+]*$")]


class AssayMetadata(BaseModel):
    model_config = _BASE_CONFIG

    assay_name: NonEmptyStr
    assay_version: VersionStr
    assay_type: AssayType
    intended_use: IntendedUse
    laboratory_name: NonEmptyStr
    laboratory_id: NonEmptyStr = Field(
        description="Internal lab identifier; for CLIA labs typically the CLIA number."
    )
    regulatory_contexts: tuple[RegulatoryContext, ...] = Field(
        default=(),
        description="Quality frameworks under which this assay operates (US/EU).",
    )
    specimen_types: tuple[str, ...] = Field(
        default=(),
        description="Validated specimen types, e.g. 'FFPE', 'whole_blood'. "
        "Materially affects somatic VAF claims.",
    )
