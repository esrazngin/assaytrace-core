"""Reportable variant delta viewer (Step 10).

Deterministic comparison of two sets of reportable-variant observations,
keyed by variant identifier. A variant absent from a pipeline's observations
is treated as MISSING for that pipeline.
"""

from __future__ import annotations

from .models import (
    DeltaType,
    ReportableVariantDelta,
    ReportableVariantObservation,
    VariantStatus,
)


class ReportableVariantDeltaViewer:
    def compare(
        self,
        old: list[ReportableVariantObservation],
        new: list[ReportableVariantObservation],
    ) -> list[ReportableVariantDelta]:
        old_map = {o.variant: o.status for o in old}
        new_map = {o.variant: o.status for o in new}
        deltas: list[ReportableVariantDelta] = []
        for variant in sorted(old_map.keys() | new_map.keys()):
            old_status = old_map.get(variant, VariantStatus.MISSING)
            new_status = new_map.get(variant, VariantStatus.MISSING)
            deltas.append(
                ReportableVariantDelta(
                    variant=variant,
                    old_status=old_status,
                    new_status=new_status,
                    delta_type=self._delta_type(old_status, new_status),
                )
            )
        return deltas

    @staticmethod
    def _delta_type(old: VariantStatus, new: VariantStatus) -> DeltaType:
        if old == new:
            return DeltaType.UNCHANGED
        if old == VariantStatus.DETECTED and new == VariantStatus.MISSING:
            return DeltaType.LOST
        if old == VariantStatus.MISSING and new == VariantStatus.DETECTED:
            return DeltaType.GAINED
        return DeltaType.STATUS_CHANGED