"""Quality-control configuration.

Rather than hard-coding `minimum_coverage`, `minimum_vaf`, etc. as fixed
fields, QC is modeled as a list of structured `QCThreshold` objects. This is
the key extensibility decision for QC: a lab can declare arbitrary present and
future metrics without a schema change, while each threshold remains strongly
typed (comparator, value, severity, scope). The change-impact engine can then
detect "a QC threshold tightened/loosened" generically.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import NonEmptyStr
from .enums import Comparator, QCSeverity, VariantType

_BASE_CONFIG = ConfigDict(
    frozen=True, extra="forbid", str_strip_whitespace=True, use_enum_values=False
)

# Canonical, recommended metric keys. Not an enum: labs may define custom keys,
# but using these promotes cross-lab comparability.
WELL_KNOWN_QC_METRICS: frozenset[str] = frozenset(
    {
        "minimum_coverage",
        "mean_coverage",
        "percent_target_bases_20x",
        "minimum_mapping_quality",
        "minimum_base_quality",
        "minimum_vaf",
        "maximum_contamination",
        "minimum_callable_fraction",
        "duplicate_rate",
        "ts_tv_ratio",
    }
)

MetricKey = Annotated[str, Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")]


class QCThreshold(BaseModel):
    """A single acceptance criterion, e.g. `minimum_coverage >= 100 x`."""

    model_config = _BASE_CONFIG

    metric: MetricKey = Field(
        description="Snake_case metric key. Prefer WELL_KNOWN_QC_METRICS where applicable."
    )
    comparator: Comparator
    threshold: float
    unit: str | None = None
    severity: QCSeverity = QCSeverity.BLOCKING
    applies_to: tuple[VariantType, ...] = Field(
        default=(),
        description="Variant types this threshold scopes to; empty = run/sample level.",
    )
    description: str | None = None

    @property
    def is_well_known(self) -> bool:
        return self.metric in WELL_KNOWN_QC_METRICS


class QCConfiguration(BaseModel):
    model_config = _BASE_CONFIG

    thresholds: tuple[QCThreshold, ...] = Field(default=())

    @field_validator("thresholds")
    @classmethod
    def _unique_metric_scope(cls, v: tuple[QCThreshold, ...]) -> tuple[QCThreshold, ...]:
        seen: set[tuple[str, tuple[VariantType, ...]]] = set()
        for t in v:
            key = (t.metric, t.applies_to)
            if key in seen:
                raise ValueError(
                    f"duplicate QC threshold for metric '{t.metric}' and scope {t.applies_to}"
                )
            seen.add(key)
        return v

    def has_metric(self, metric: str) -> bool:
        return any(t.metric == metric for t in self.thresholds)
