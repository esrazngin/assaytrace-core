"""Performance regression detector (Step 9 + Part 2).

Deterministic before/after comparison of two benchmarks' metric maps. Accepts
any object exposing ``as_metric_map()`` (both ``GiabEvidencePackage`` and the
standardized ``BenchmarkPackage`` qualify), so the engine is decoupled from the
concrete benchmark schema. Status is decided purely by comparing the signed
delta against the configured tolerance; a human-readable rationale is attached
to every comparison. No scoring, no inference.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import MetricComparison, RegressionStatus, RegressionThresholds


@runtime_checkable
class SupportsMetricMap(Protocol):
    def as_metric_map(self) -> dict[str, float]: ...


def _pretty(metric: str) -> str:
    cls, _, name = metric.partition("_")
    cls_label = cls.upper() if cls in {"snv", "indel", "cnv"} else cls.capitalize()
    return f"{cls_label} {name}".strip()


class PerformanceRegressionDetector:
    def __init__(self, thresholds: RegressionThresholds | None = None) -> None:
        self.thresholds = thresholds or RegressionThresholds()

    def compare(
        self, old: SupportsMetricMap, new: SupportsMetricMap
    ) -> list[MetricComparison]:
        old_metrics = old.as_metric_map()
        new_metrics = new.as_metric_map()
        results: list[MetricComparison] = []
        for metric in sorted(old_metrics.keys() & new_metrics.keys()):
            old_value = old_metrics[metric]
            new_value = new_metrics[metric]
            delta = round(new_value - old_value, 6)
            tolerance = self.thresholds.tolerance_for(metric)
            if delta < -tolerance:
                status = RegressionStatus.REGRESSION_DETECTED
            elif delta > tolerance:
                status = RegressionStatus.IMPROVED
            else:
                status = RegressionStatus.WITHIN_TOLERANCE
            results.append(
                MetricComparison(
                    metric=metric,
                    old_value=old_value,
                    new_value=new_value,
                    delta=delta,
                    status=status,
                    rationale=self._rationale(metric, delta, status, tolerance),
                )
            )
        return results

    @staticmethod
    def _rationale(
        metric: str, delta: float, status: RegressionStatus, tolerance: float
    ) -> str:
        pretty = _pretty(metric)
        pct = abs(delta) * 100.0
        tol_pct = tolerance * 100.0
        if status is RegressionStatus.REGRESSION_DETECTED:
            return (
                f"{pretty} decreased by {pct:.1f}% (Δ={delta:+.3f}), exceeding the "
                f"configured regression threshold of {tol_pct:.1f}%."
            )
        if status is RegressionStatus.IMPROVED:
            return (
                f"{pretty} increased by {pct:.1f}% (Δ={delta:+.3f}), exceeding the "
                f"configured threshold of {tol_pct:.1f}%."
            )
        return (
            f"{pretty} changed by {pct:.1f}% (Δ={delta:+.3f}), within the configured "
            f"tolerance of {tol_pct:.1f}%."
        )