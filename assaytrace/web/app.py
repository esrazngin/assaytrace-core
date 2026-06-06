"""AssayTrace web application (Part 5).

A lightweight, professional SaaS-style interface over the existing engine. No
auth, no database, no persistence: uploads are processed in-memory and the
fully serializable AuditBinder is returned to the client, which posts it back
to export a PDF — so PDF export stays stateless.

Run:  python -m assaytrace.web.app   (requires Flask)
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from ..evidence.benchmark import BenchmarkPackage
from ..io.loader import load_manifest
from ..models.manifest import AssayManifest
from ..reportable.classification import ReportableVariant
from ..reporting.binder import build_binder
from ..reporting.models import AuditBinder
from ..reporting.pdf_export import render_pdf
from examples.change_demo import _new_from

app = Flask(__name__)

_NO_REVAL = {"no_revalidation_required", "documentation_update"}
_EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
_FIXTURES = _EXAMPLES / "fixtures"


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


def _analyze(
    old: AssayManifest,
    new: AssayManifest,
    *,
    baseline: BenchmarkPackage | None = None,
    current: BenchmarkPackage | None = None,
    old_variants: list[ReportableVariant] | None = None,
    new_variants: list[ReportableVariant] | None = None,
) -> dict:
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
    return {
        "decision": "REVALIDATION_REQUIRED" if revalidation_required else "SAFE_TO_DEPLOY",
        "summary": {
            "changes": len(binder.changes),
            "impacts": len(binder.impacts),
            "decisions": len(binder.decisions),
            "affected_claims": sorted({c for d in binder.decisions for c in d.affected_claims}),
            "regressions": sum(1 for m in binder.regression if m.status.value == "regression_detected"),
            "variant_changes": len(binder.variant_classification_deltas),
        },
        "binder": payload,
    }


def _load_fixture_json(name: str):
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _run_demo() -> dict:
    old = load_manifest(_EXAMPLES / "manifest.json")
    new = _new_from(old)
    baseline = BenchmarkPackage.model_validate(_load_fixture_json("benchmark_baseline.json"))
    current = BenchmarkPackage.model_validate(_load_fixture_json("benchmark_current.json"))
    old_variants = [ReportableVariant.model_validate(v) for v in _load_fixture_json("variants_old.json")]
    new_variants = [ReportableVariant.model_validate(v) for v in _load_fixture_json("variants_new.json")]
    return _analyze(
        old, new,
        baseline=baseline,
        current=current,
        old_variants=old_variants,
        new_variants=new_variants,
    )


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/about")
def about_page() -> str:
    return render_template("about.html", active_page="about")


@app.get("/docs")
def docs_page() -> str:
    return render_template("docs.html", active_page="docs")


@app.post("/demo")
def demo():
    try:
        return jsonify(_run_demo())
    except Exception as exc:  # noqa: BLE001 - surface fixture/load errors to UI
        return jsonify(error=f"Demo error: {exc}"), 500


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

    return jsonify(_analyze(
        old, new,
        baseline=baseline,
        current=current,
        old_variants=old_variants,
        new_variants=new_variants,
    ))


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
    import os

    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
