from __future__ import annotations

import copy
from datetime import date, datetime, timezone
from pathlib import Path

from assaytrace import AssayManifest
from assaytrace.evidence import load_benchmark_package
from assaytrace.reportable import parse_reportable_variants
from assaytrace.reporting import build_binder, render_pdf
from examples.build import build

import json
FIX = Path(__file__).resolve().parent.parent / "examples" / "fixtures"
_FIXED = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)


def _binder():
    old = build()
    d = copy.deepcopy(old.model_dump(mode="json"))
    d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"
    new = AssayManifest.model_validate(d)
    return build_binder(
        old, new,
        baseline_benchmark=load_benchmark_package(FIX / "benchmark_baseline.json"),
        current_benchmark=load_benchmark_package(FIX / "benchmark_current.json"),
        old_variants=parse_reportable_variants(json.loads((FIX / "variants_old.json").read_text())),
        new_variants=parse_reportable_variants(json.loads((FIX / "variants_new.json").read_text())),
        generated_at=_FIXED,
    )


def test_render_pdf_returns_real_pdf_bytes():
    pdf = render_pdf(_binder())
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 2000
    assert pdf.count(b"/Type /Page") >= 2  # multi-page


def test_render_pdf_writes_file(tmp_path):
    out = tmp_path / "report.pdf"
    render_pdf(_binder(), out)
    assert out.exists() and out.read_bytes()[:5] == b"%PDF-"


def test_pdf_handles_empty_noop_binder():
    old = build()
    pdf = render_pdf(build_binder(old, old, generated_at=_FIXED))
    assert pdf[:5] == b"%PDF-"
