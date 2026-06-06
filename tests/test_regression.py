from __future__ import annotations

from datetime import date

from assaytrace.evidence import GiabEvidencePackage
from assaytrace.regression import (
    PerformanceRegressionDetector,
    RegressionStatus,
    RegressionThresholds,
)


def _pkg(**overrides) -> GiabEvidencePackage:
    base = dict(
        sample="HG002",
        snv_precision=0.999,
        snv_recall=0.995,
        indel_precision=0.985,
        indel_recall=0.961,
        comparison_date=date(2026, 1, 15),
        evidence_source="src",
    )
    base.update(overrides)
    return GiabEvidencePackage(**base)


def test_regression_detected_indel_recall():
    old = _pkg()
    new = _pkg(indel_recall=0.947)  # -0.014 with default tolerance 0.01
    results = {r.metric: r for r in PerformanceRegressionDetector().compare(old, new)}
    r = results["indel_recall"]
    assert r.old_value == 0.961
    assert r.new_value == 0.947
    assert r.delta == -0.014
    assert r.status is RegressionStatus.REGRESSION_DETECTED


def test_improvement_detected():
    old = _pkg(snv_recall=0.95)
    new = _pkg(snv_recall=0.99)
    results = {r.metric: r for r in PerformanceRegressionDetector().compare(old, new)}
    assert results["snv_recall"].status is RegressionStatus.IMPROVED


def test_within_tolerance():
    old = _pkg(snv_precision=0.999)
    new = _pkg(snv_precision=0.998)  # -0.001, within default 0.01
    results = {r.metric: r for r in PerformanceRegressionDetector().compare(old, new)}
    assert results["snv_precision"].status is RegressionStatus.WITHIN_TOLERANCE


def test_thresholds_are_configurable():
    old = _pkg(indel_recall=0.961)
    new = _pkg(indel_recall=0.947)  # -0.014
    lenient = PerformanceRegressionDetector(
        RegressionThresholds(per_metric={"indel_recall": 0.02})
    )
    results = {r.metric: r for r in lenient.compare(old, new)}
    # now within the per-metric tolerance of 0.02
    assert results["indel_recall"].status is RegressionStatus.WITHIN_TOLERANCE