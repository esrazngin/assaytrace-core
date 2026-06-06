from __future__ import annotations

import copy
from datetime import datetime, timezone

from assaytrace import AssayManifest
from assaytrace.evidence import GiabEvidencePackage
from assaytrace.reportable import ReportableVariantObservation, VariantStatus
from assaytrace.reporting import AuditBinder, SignOffSection, build_binder, render_html
from examples.build import build

_FIXED = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)


def _ev(**ov):
    base = dict(sample="HG002", snv_precision=0.999, snv_recall=0.995,
                indel_precision=0.985, indel_recall=0.961,
                comparison_date="2026-01-15", evidence_source="src")
    base.update(ov)
    return GiabEvidencePackage.model_validate(base)


def test_build_binder_full():
    old = build()
    d = copy.deepcopy(old.model_dump(mode="json"))
    d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"
    new = AssayManifest.model_validate(d)

    binder = build_binder(
        old, new,
        current_evidence=_ev(indel_recall=0.947),
        baseline_evidence=_ev(indel_recall=0.961),
        old_reportable=[ReportableVariantObservation(variant="BRCA1 c.68_69delAG")],
        new_reportable=[ReportableVariantObservation(
            variant="BRCA1 c.68_69delAG", status=VariantStatus.MISSING)],
        sign_off=SignOffSection(prepared_by="A. Tech"),
        generated_at=_FIXED,
    )
    assert isinstance(binder, AuditBinder)
    assert len(binder.changes) == 1
    assert len(binder.decisions) == 1
    assert len(binder.regression) == 4
    assert any(d.delta_type.value == "lost" for d in binder.reportable_deltas)
    assert binder.sign_off.prepared_by == "A. Tech"
    assert "laboratory director" in binder.disclaimer


def test_render_html_deterministic():
    old = build()
    d = copy.deepcopy(old.model_dump(mode="json"))
    d["analysis_components"]["aligner"]["version"] = "2.2.2"
    new = AssayManifest.model_validate(d)
    binder = build_binder(old, new, generated_at=_FIXED)
    html_a = render_html(binder)
    html_b = render_html(binder)
    assert html_a == html_b
    assert "<html" in html_a and "Revalidation Binder" in html_a
    assert "aligner:bwa-mem2" in html_a


def test_binder_model_is_serializable():
    old = build()
    binder = build_binder(old, old, generated_at=_FIXED)  # no-op
    payload = binder.model_dump(mode="json")
    assert payload["changes"] == []
    assert payload["decisions"] == []