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
from ..approval.models import DeviationApproval
from ..models.manifest import AssayManifest
from ..policy.loader import parse_policy
from ..reportable.classification import ReportableVariant
from ..reporting.binder import build_binder
from ..reporting import presentation
from ..reporting.models import AuditBinder
from ..reporting.pdf_export import render_pdf

import copy
from pathlib import Path

from examples.build import build as _build_somatic
from examples.build_germline import build as _build_germline

app = Flask(__name__)

_FIX = Path(__file__).resolve().parents[2] / "examples" / "fixtures"


def _bump_caller(manifest, version, reason):
    """Return a candidate manifest with the variant-caller version bumped.

    Used only to seed the read-only demo dataset; does not touch analysis logic.
    """
    d = copy.deepcopy(manifest.model_dump(mode="json"))
    d["analysis_components"]["variant_caller"]["version"] = version
    d["change_reason"] = reason
    return AssayManifest.model_validate(d)


def _release_candidate(manifest):
    """A realistic clinical release with five simultaneous changes.

    Mirrors what labs actually ship together: caller upgrade, annotation DB
    refresh, reference-genome point release, a QC threshold relaxation, and a
    container image rebuild. Built by editing the validated baseline dump and
    re-validating, so the candidate is always schema-valid.
    """
    import copy as _copy

    d = _copy.deepcopy(manifest.model_dump(mode="json"))
    # 1) Variant caller minor upgrade.
    d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"
    # 2) ClinVar annotation database refresh.
    for r in d["reference_resources"]["annotation_resources"]:
        if r.get("name") == "ClinVar":
            r["version"] = "2026-03-01"
    # 3) Reference genome point release.
    d["reference_resources"]["reference_genome"]["version"] = "GRCh38.p15-analysis-set"
    # 4) QC threshold relaxation (intentional, will be an approved deviation).
    for t in d["qc"]["thresholds"]:
        if t["metric"] == "minimum_vaf":
            t["threshold"] = 0.03
    # 5) Container image rebuild (new digest).
    d["environment"]["image_digest"]["value"] = "e" * 64
    d["change_reason"] = (
        "Q1 release: Mutect2 4.6, ClinVar 2026-03, GRCh38.p15, VAF floor 0.05->0.03 "
        "(approved), container rebuild."
    )
    return AssayManifest.model_validate(d)


def _demo_approvals(changes) -> list[dict]:
    """A governance-rich approval set built from the real detected changes.

    Demonstrates the full workflow: distinct dispositions across decisions and a
    multi-step history (Pending Review -> Approved With Conditions -> Approved).
    Approval ids are deterministic (SHA-1 of the change id), so the same demo
    always yields the same audit identifiers.
    """
    import hashlib

    def base_id(cid: str) -> str:
        return "APR-" + hashlib.sha1(cid.encode("utf-8")).hexdigest()[:8].upper()

    def appr(cid, status, reviewer, date, history, conditions=None, rationale=None):
        bid = base_id(cid)
        events = [
            {
                "approval_id": f"{bid}-{i + 1}",
                "status": st, "reviewer": rv, "date": dt,
                "conditions": cond, "rationale": rat,
            }
            for i, (st, rv, dt, cond, rat) in enumerate(history)
        ]
        latest = events[-1]
        return {
            "change_id": cid,
            "approval_id": latest["approval_id"],
            "status": status,
            "reviewer": reviewer,
            "approval_date": date,
            "conditions": conditions,
            "rationale": rationale or latest["rationale"],
            "history": events,
        }

    out: list[dict] = []
    for c in changes:
        cid = c.change_id
        cat = c.category.value if c.category else None
        ct = c.change_type.value
        if cat == "variant_caller":
            out.append(appr(cid, "approved", "Lab Director", "2026-02-03",
                            [("pending", "QA Analyst", "2026-02-01", None, "Initial triage of caller upgrade."),
                             ("approved", "Lab Director", "2026-02-03", None, "Validated against GIAB HG002.")]))
        elif cat == "annotation":
            out.append(appr(cid, "approved", "Variant Scientist", "2026-02-04",
                            [("approved", "Variant Scientist", "2026-02-04", None, "ClinVar delta reviewed; no reportable reclassifications.")]))
        elif cat == "reference_genome":
            out.append(appr(cid, "approved_with_conditions", "Lab Director", "2026-02-05",
                            [("pending", "QA Analyst", "2026-02-01", None, "Awaiting SV benchmark."),
                             ("approved_with_conditions", "Lab Director", "2026-02-05",
                              "Re-run HG002 SV truth set within 30 days.", "Conditional approval pending SV re-run.")],
                            conditions="Re-run HG002 SV truth set within 30 days."))
        elif ct == "qc_threshold_changed":
            out.append(appr(cid, "approved", "Lab Director", "2026-02-06",
                            [("pending", "QA Analyst", "2026-02-01", None, "Flagged VAF relaxation for review."),
                             ("approved_with_conditions", "Medical Director", "2026-02-04",
                              "Limit to ctDNA assays.", "Conditional pending control data."),
                             ("approved", "Lab Director", "2026-02-06", None, "Control data validated per SOP-19.")]))
        elif ct == "environment_changed":
            out.append(appr(cid, "pending", "QA Analyst", "2026-02-01",
                            [("pending", "QA Analyst", "2026-02-01", None, "Container rebuild noted; verification scheduled.")]))
    return out


def _demo_context() -> dict:
    """Assemble a real, model-valid demo dataset for the auto-run experience and
    the Sample Manifest Library. Pure data; no new endpoints, no engine changes."""
    som_old = _build_somatic()
    som_new = _release_candidate(som_old)
    germ_old = _build_germline()
    germ_new = _bump_caller(
        germ_old, "4.6.0.0",
        "Upgrade HaplotypeCaller 4.5.0.0 -> 4.6.0.0.",
    )

    from .._policy_demo import (
        demo_policy_dict, demo_germline_policy_dict, demo_policy_registry,
    )
    from ..diff.detector import ChangeDetector

    def _read(name):
        return json.loads((_FIX / name).read_text(encoding="utf-8"))

    som_changes = ChangeDetector().compare(som_old, som_new)

    return {
        "somatic_old": som_old.model_dump(mode="json"),
        "somatic_new": som_new.model_dump(mode="json"),
        "germline_old": germ_old.model_dump(mode="json"),
        "germline_new": germ_new.model_dump(mode="json"),
        "benchmark_baseline": _read("benchmark_baseline.json"),
        "benchmark_current": _read("benchmark_current.json"),
        "variants_old": _read("variants_old.json"),
        "variants_new": _read("variants_new.json"),
        "policy": demo_policy_dict(),
        "approvals": _demo_approvals(som_changes),
        "policy_registry": demo_policy_registry(),
        "policy_specs": {
            "somatic-sop": demo_policy_dict(),
            "germline-sop": demo_germline_policy_dict(),
        },
        "policy_versions": _policy_versions(),
    }


def _policy_versions() -> dict:
    """Per-family version specs so the comparison view shows real rule diffs."""
    from .._policy_demo import demo_policy_dict, demo_germline_policy_dict
    import copy as _copy
    som_v3 = demo_policy_dict()
    som_v4 = _copy.deepcopy(som_v3)
    som_v4["version"] = "v4"
    # v4 tightens the minor caller rule and adds an annotation rule.
    som_v4["mutect2"]["minor_version"]["action"] = "full_revalidation"
    som_v4["annotation_update"] = {"any": {"action": "classification_concordance_review",
                                           "rationale": "Annotation DB refresh."}}
    germ = demo_germline_policy_dict()
    return {
        "Somatic SOP": {"v3": som_v3, "v4": som_v4},
        "Germline SOP": {"v1": germ, "v2": germ},
    }

_NO_REVAL = {"no_revalidation_required", "documentation_update"}

_REVAL_RANK = {
    "no_revalidation_required": 0, "documentation_update": 1,
    "infrastructure_verification": 2, "qc_verification": 3,
    "classification_concordance_review": 4, "targeted_analytical_revalidation": 5,
    "scope_review_and_targeted_validation": 6,
    "full_or_targeted_analytical_revalidation": 7, "full_analytical_revalidation": 8,
}
_SEV_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_REVAL_LABEL = {
    "no_revalidation_required": "No revalidation required",
    "documentation_update": "Documentation update",
    "infrastructure_verification": "Infrastructure verification",
    "qc_verification": "QC verification",
    "classification_concordance_review": "Classification concordance review",
    "targeted_analytical_revalidation": "Targeted analytical revalidation",
    "scope_review_and_targeted_validation": "Scope review and targeted validation",
    "full_or_targeted_analytical_revalidation": "Full or targeted analytical revalidation",
    "full_analytical_revalidation": "Full analytical revalidation",
}


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


def _policy(file_storage):
    if file_storage is None or not file_storage.filename:
        return None
    return parse_policy(json.loads(file_storage.read().decode("utf-8")))


def _approvals(file_storage):
    if file_storage is None or not file_storage.filename:
        return None
    raw = json.loads(file_storage.read().decode("utf-8"))
    return [DeviationApproval.model_validate(a) for a in raw]


@app.get("/")
def index() -> str:
    return render_template("index.html", demo_json=json.dumps(_demo_context()))


@app.post("/api/analyze")
def analyze():
    try:
        old = _manifest(request.files["old_manifest"])
        new = _manifest(request.files["new_manifest"])
        baseline = _benchmark(request.files.get("baseline_benchmark"))
        current = _benchmark(request.files.get("current_benchmark"))
        old_variants = _variants(request.files.get("old_variants"))
        new_variants = _variants(request.files.get("new_variants"))
        policy = _policy(request.files.get("policy"))
        approvals = _approvals(request.files.get("approvals"))
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
        policy=policy,
        approvals=approvals,
    )
    revalidation_required = any(
        d.decision_type.value not in _NO_REVAL for d in binder.decisions
    )
    payload = binder.model_dump(mode="json")

    sev_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for sv in binder.change_severities:
        sev_counts[sv.severity.value] += 1
    highest_sev = max(
        (sv.severity.value for sv in binder.change_severities),
        key=lambda v: _SEV_RANK[v], default=None,
    )
    recommended = max(
        binder.decisions,
        key=lambda d: _REVAL_RANK.get(d.decision_type.value, 0),
        default=None,
    )
    primary = max(
        binder.change_severities,
        key=lambda s: (_SEV_RANK[s.severity.value], s.change_id),
        default=None,
    )
    primary_desc = None
    if primary is not None:
        primary_desc = next(
            (c.description for c in binder.changes if c.change_id == primary.change_id),
            primary.change_id,
        )
    return jsonify(
        decision="REVALIDATION_REQUIRED" if revalidation_required else "SAFE_TO_DEPLOY",
        summary={
            "changes": len(binder.changes),
            "impacts": len(binder.impacts),
            "decisions": len(binder.decisions),
            "affected_claims": sorted({c for d in binder.decisions for c in d.affected_claims}),
            "regressions": sum(1 for m in binder.regression if m.status.value == "regression_detected"),
            "variant_changes": len(binder.variant_classification_deltas),
            "highest_severity": highest_sev,
            "severity_counts": sev_counts,
            "approved_deviations": sum(1 for a in binder.approvals if a.status.value != "not_reviewed"),
            "policy_name": binder.policy_name,
            "recommended_action": recommended.decision_type.value if recommended else None,
            "recommended_action_label": _REVAL_LABEL.get(recommended.decision_type.value) if recommended else None,
            "recommended_rationale": recommended.rationale if recommended else None,
            "recommended_rule": recommended.triggered_by_rule if recommended else None,
            "primary_change": primary_desc,
            "recommended_next_step": presentation.recommended_next_step(binder),
        },
        view={
            "decisions": presentation.decision_views(binder),
            "aggregate": presentation.aggregate(binder),
            "top_impact": presentation.top_impact_changes(binder, limit=3),
            "timeline": presentation.timeline(binder),
            "governance": presentation.governance_status(binder),
            "business_impact": presentation.business_impact(binder),
            "audit_metadata": presentation.audit_metadata(binder),
            "lifecycle": presentation.binder_lifecycle(binder),
            "regression_gate": presentation.regression_gate_view(binder),
            "recommended_next_step": presentation.recommended_next_step(binder),
        },
        binder=payload,
    )


@app.get("/api/portfolio")
def portfolio() -> Response:
    """Deterministic multi-assay portfolio summary (Productization Sprint 3)."""
    from ..portfolio import demo_portfolio
    return jsonify(demo_portfolio())


@app.post("/api/policy-compare")
def policy_compare() -> Response:
    """Side-by-side diff of two supplied policy specs (Sprint 1)."""
    try:
        body = request.get_json(force=True) or {}
        a = parse_policy(body.get("base", {}))
        b = parse_policy(body.get("candidate", {}))
        from ..policy.compare import compare_policies
        return jsonify(compare_policies(a, b))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/policy")
def derive_policy() -> Response:
    """Return a deterministic descriptor (with real content hash) for a supplied
    policy spec. Backs the Policy Management lifecycle so created / duplicated /
    versioned SOPs carry genuine ``content_hash`` values, never fabricated ones.
    """
    try:
        spec = request.get_json(force=True) or {}
        pol = parse_policy(spec)
        return jsonify({
            "name": pol.name,
            "version": pol.version,
            "assay_type": pol.assay_type.value if pol.assay_type else None,
            "status": pol.status,
            "hash": pol.content_hash(),
            "rule_count": len(pol.rules),
        })
    except Exception as exc:  # malformed spec -> fail loudly, like the loader
        return jsonify({"error": str(exc)}), 400


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
