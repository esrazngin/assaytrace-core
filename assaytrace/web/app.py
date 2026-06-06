"""AssayTrace web application (Part 5).

A lightweight, professional SaaS-style interface over the existing engine. No
auth, no database, no persistence: uploads are processed in-memory and the
fully serializable AuditBinder is returned to the client, which posts it back
to export a PDF — so PDF export stays stateless.

Run:  python -m assaytrace.web.app   (requires Flask)
"""

from __future__ import annotations

import json

from flask import Flask, Response, jsonify, render_template, request

from ..evidence.benchmark import BenchmarkPackage
from ..models.manifest import AssayManifest
from ..reportable.classification import ReportableVariant
from ..reporting.binder import build_binder
from ..reporting.models import AuditBinder
from ..reporting.pdf_export import render_pdf

app = Flask(__name__)

_NO_REVAL = {"no_revalidation_required", "documentation_update"}


def _manifest(file_storage) -> AssayManifest:
    return AssayManifest.model_validate(json.loads(file_storage.read().decode("utf-8")))


def _benchmark(file_storage) -> BenchmarkPackage | None:
    if file_storage is None or not file_storage.filename:
        return None
    return BenchmarkPackage.model_validate(json.loads(file_storage.read().decode("utf-8")))


def _variants(file_storage) -> list[ReportableVariant] | None:
    if file_storage is None or not file_storage.filename:
        return None
    raw = json.loads(file_storage.read().decode("utf-8"))
    return [ReportableVariant.model_validate(v) for v in raw]


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.post("/api/analyze")
def analyze():
    try:
        old = _manifest(request.files["old_manifest"])
        new = _manifest(request.files["new_manifest"])
        baseline = _benchmark(request.files.get("baseline_benchmark"))
        current = _benchmark(request.files.get("current_benchmark"))
        old_variants = _variants(request.files.get("old_variants"))
        new_variants = _variants(request.files.get("new_variants"))
    except KeyError:
        return jsonify(error="Both old and new manifests are required."), 400
    except Exception as exc:  # noqa: BLE001 - surface parse/validation errors to UI
        return jsonify(error=f"Input error: {exc}"), 400

    binder = build_binder(
        old, new,
        baseline_benchmark=baseline,
        current_benchmark=current,
        old_variants=old_variants,
        new_variants=new_variants,
    )
    revalidation_required = any(
        d.decision_type.value not in _NO_REVAL for d in binder.decisions
    )
    payload = binder.model_dump(mode="json")
    return jsonify(
        decision="REVALIDATION_REQUIRED" if revalidation_required else "SAFE_TO_DEPLOY",
        summary={
            "changes": len(binder.changes),
            "impacts": len(binder.impacts),
            "decisions": len(binder.decisions),
            "affected_claims": sorted({c for d in binder.decisions for c in d.affected_claims}),
            "regressions": sum(1 for m in binder.regression if m.status.value == "regression_detected"),
            "variant_changes": len(binder.variant_classification_deltas),
        },
        binder=payload,
    )


@app.post("/api/export-pdf")
def export_pdf() -> Response:
    try:
        binder = AuditBinder.model_validate(request.get_json(force=True))
    except Exception as exc:  # noqa: BLE001
        return Response(f"Invalid binder: {exc}", status=400, mimetype="text/plain")
    pdf = render_pdf(binder)
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=assaytrace_binder.pdf"},
    )


if __name__ == "__main__":  # pragma: no cover
    app.run(host="127.0.0.1", port=8000, debug=False)
