from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from assaytrace.evidence import (
    BenchmarkPackage,
    MetricTriplet,
    load_benchmark_package,
    parse_benchmark_package,
)

FIX = Path(__file__).resolve().parent.parent / "examples" / "fixtures"


def test_parse_benchmark_fixture():
    pkg = parse_benchmark_package(json.loads((FIX / "benchmark_current.json").read_text()))
    assert pkg.sample_id == "HG002"
    assert pkg.benchmark_name == "GIAB"
    assert pkg.run_date == date(2026, 1, 15)
    assert pkg.snv.recall == 0.974


def test_load_benchmark_file():
    pkg = load_benchmark_package(FIX / "benchmark_baseline.json")
    assert pkg.snv.recall == 0.981


def test_metric_map_includes_cnv_when_present():
    pkg = load_benchmark_package(FIX / "benchmark_current.json")
    m = pkg.as_metric_map()
    assert set(m) == {
        "snv_precision", "snv_recall", "snv_f1",
        "indel_precision", "indel_recall", "indel_f1",
        "cnv_precision", "cnv_recall", "cnv_f1",
    }


def test_metric_map_omits_cnv_when_absent():
    pkg = BenchmarkPackage(
        sample_id="HG002", benchmark_name="GIAB", benchmark_version="v4.2.1",
        truthset="t", run_date=date(2026, 1, 1),
        snv=MetricTriplet(precision=0.99, recall=0.98, f1=0.985),
        indel=MetricTriplet(precision=0.97, recall=0.95, f1=0.96),
    )
    assert "cnv_recall" not in pkg.as_metric_map()


def test_proportion_bounds_enforced():
    with pytest.raises(ValidationError):
        MetricTriplet(precision=1.2, recall=0.9, f1=0.9)


def test_f1_cannot_exceed_max_precision_recall():
    with pytest.raises(ValidationError):
        MetricTriplet(precision=0.80, recall=0.80, f1=0.99)
