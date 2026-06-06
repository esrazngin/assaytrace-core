from __future__ import annotations

from pathlib import Path

from assaytrace.evidence import load_benchmark_package
from assaytrace.regression import (
    PerformanceRegressionDetector,
    RegressionStatus,
    RegressionThresholds,
)

FIX = Path(__file__).resolve().parent.parent / "examples" / "fixtures"


def _pair():
    return (load_benchmark_package(FIX / "benchmark_baseline.json"),
            load_benchmark_package(FIX / "benchmark_current.json"))


def test_snv_recall_regression_at_tight_threshold():
    base, cur = _pair()
    det = PerformanceRegressionDetector(RegressionThresholds(default_tolerance=0.005))
    res = {m.metric: m for m in det.compare(base, cur)}
    r = res["snv_recall"]
    assert r.old_value == 0.981
    assert r.new_value == 0.974
    assert r.delta == -0.007
    assert r.status is RegressionStatus.REGRESSION_DETECTED
    assert "SNV recall decreased by 0.7%" in r.rationale
    assert "0.5%" in r.rationale  # threshold disclosed


def test_threshold_configurability():
    base, cur = _pair()
    # at 0.01 tolerance the 0.7% SNV recall drop is within tolerance
    res = {m.metric: m for m in
           PerformanceRegressionDetector(RegressionThresholds(default_tolerance=0.01)).compare(base, cur)}
    assert res["snv_recall"].status is RegressionStatus.WITHIN_TOLERANCE
    # per-metric override can re-tighten just that metric
    res2 = {m.metric: m for m in PerformanceRegressionDetector(
        RegressionThresholds(default_tolerance=0.02, per_metric={"snv_recall": 0.005})
    ).compare(base, cur)}
    assert res2["snv_recall"].status is RegressionStatus.REGRESSION_DETECTED


def test_legacy_evidence_still_supported():
    from datetime import date
    from assaytrace.evidence import GiabEvidencePackage
    old = GiabEvidencePackage(snv_precision=0.99, snv_recall=0.98, indel_precision=0.97,
                              indel_recall=0.961, comparison_date=date(2026, 1, 1), evidence_source="s")
    new = GiabEvidencePackage(snv_precision=0.99, snv_recall=0.98, indel_precision=0.97,
                              indel_recall=0.947, comparison_date=date(2026, 1, 2), evidence_source="s")
    res = {m.metric: m for m in PerformanceRegressionDetector().compare(old, new)}
    assert res["indel_recall"].status is RegressionStatus.REGRESSION_DETECTED
