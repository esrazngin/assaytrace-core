from __future__ import annotations

import json
from datetime import date

import pytest
from pydantic import ValidationError

from assaytrace.evidence import (
    GiabEvidencePackage,
    load_evidence_package,
    parse_evidence_package,
)

_DATA = {
    "sample": "HG002",
    "snv_precision": 0.999,
    "snv_recall": 0.995,
    "indel_precision": 0.985,
    "indel_recall": 0.961,
    "comparison_date": "2026-01-15",
    "evidence_source": "hap.py v0.3.15 (structured MVP entry)",
}


def test_parse_evidence_package():
    pkg = parse_evidence_package(_DATA)
    assert pkg.sample == "HG002"
    assert pkg.comparison_date == date(2026, 1, 15)
    assert pkg.as_metric_map()["indel_recall"] == 0.961


def test_load_evidence_package(tmp_path):
    p = tmp_path / "evidence.json"
    p.write_text(json.dumps(_DATA), encoding="utf-8")
    pkg = load_evidence_package(p)
    assert pkg.snv_precision == 0.999


def test_metrics_must_be_proportions():
    bad = dict(_DATA, snv_recall=1.5)
    with pytest.raises(ValidationError):
        parse_evidence_package(bad)


def test_metric_map_keys():
    pkg = parse_evidence_package(_DATA)
    assert set(pkg.as_metric_map()) == {
        "snv_precision",
        "snv_recall",
        "indel_precision",
        "indel_recall",
    }