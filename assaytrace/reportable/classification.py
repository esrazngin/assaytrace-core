"""Classification-aware reportable variant delta (Part 3).

Richer than the Step-10 detected/missing model: a reportable variant carries an
ACMG-style classification, and the differ detects ADDED, REMOVED, and
CLASSIFICATION_CHANGED between two reportable-variant sets, each with a
human-readable explanation. Deterministic; no VCF parsing, no annotation logic.

Added alongside the existing observation-based viewer for backward
compatibility; new flows (PDF, web) use this classification model.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VariantClassification(str, Enum):
    BENIGN = "Benign"
    LIKELY_BENIGN = "Likely benign"
    VUS = "VUS"
    LIKELY_PATHOGENIC = "Likely pathogenic"
    PATHOGENIC = "Pathogenic"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class ReportableDeltaType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    CLASSIFICATION_CHANGED = "classification_changed"
    UNCHANGED = "unchanged"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class ReportableVariant(BaseModel):
    """A reportable variant with its clinical classification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gene: str
    variant: str = Field(description="HGVS or other variant designation.")
    classification: VariantClassification
    transcript: str | None = None

    @property
    def key(self) -> str:
        return f"{self.gene}|{self.variant}"


class VariantClassificationDelta(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gene: str
    variant: str
    change_type: ReportableDeltaType
    old_classification: VariantClassification | None = None
    new_classification: VariantClassification | None = None
    explanation: str


class ReportableVariantDiffer:
    """Deterministic differ over classification-bearing reportable variants."""

    def diff(
        self,
        old: list[ReportableVariant],
        new: list[ReportableVariant],
        *,
        include_unchanged: bool = False,
    ) -> list[VariantClassificationDelta]:
        old_map = {v.key: v for v in old}
        new_map = {v.key: v for v in new}
        deltas: list[VariantClassificationDelta] = []

        for key in sorted(old_map.keys() | new_map.keys()):
            o = old_map.get(key)
            n = new_map.get(key)
            if o is None and n is not None:
                deltas.append(self._added(n))
            elif o is not None and n is None:
                deltas.append(self._removed(o))
            elif o is not None and n is not None:
                if o.classification != n.classification:
                    deltas.append(self._reclassified(o, n))
                elif include_unchanged:
                    deltas.append(self._unchanged(n))
        return deltas

    @staticmethod
    def _added(v: ReportableVariant) -> VariantClassificationDelta:
        return VariantClassificationDelta(
            gene=v.gene, variant=v.variant,
            change_type=ReportableDeltaType.ADDED,
            new_classification=v.classification,
            explanation=(
                f"New reportable variant {v.gene} {v.variant} introduced "
                f"({v.classification.value})."
            ),
        )

    @staticmethod
    def _removed(v: ReportableVariant) -> VariantClassificationDelta:
        return VariantClassificationDelta(
            gene=v.gene, variant=v.variant,
            change_type=ReportableDeltaType.REMOVED,
            old_classification=v.classification,
            explanation=(
                f"Reportable variant {v.gene} {v.variant} "
                f"({v.classification.value}) is no longer reported."
            ),
        )

    @staticmethod
    def _reclassified(
        o: ReportableVariant, n: ReportableVariant
    ) -> VariantClassificationDelta:
        return VariantClassificationDelta(
            gene=n.gene, variant=n.variant,
            change_type=ReportableDeltaType.CLASSIFICATION_CHANGED,
            old_classification=o.classification,
            new_classification=n.classification,
            explanation=(
                f"Variant classification changed from {o.classification.value} "
                f"to {n.classification.value}."
            ),
        )

    @staticmethod
    def _unchanged(v: ReportableVariant) -> VariantClassificationDelta:
        return VariantClassificationDelta(
            gene=v.gene, variant=v.variant,
            change_type=ReportableDeltaType.UNCHANGED,
            old_classification=v.classification,
            new_classification=v.classification,
            explanation=f"{v.gene} {v.variant} unchanged ({v.classification.value}).",
        )


def parse_reportable_variants(data: list[dict[str, Any]]) -> list[ReportableVariant]:
    return [ReportableVariant.model_validate(item) for item in data]


def load_reportable_variants(path: str | Path) -> list[ReportableVariant]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_reportable_variants(raw)