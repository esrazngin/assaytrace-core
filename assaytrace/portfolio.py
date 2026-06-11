"""Laboratory portfolio layer (Productization Sprint 3).

Builds a deterministic, multi-assay demo portfolio by running several assay
scenarios through the *existing* engine (``build_binder``) and summarizing the
resulting binders. Nothing here is mocked: every status, risk level, and count
is derived from a real ``AuditBinder``. This is what lets AssayTrace answer
"can it manage a whole laboratory?" without abandoning determinism.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from assaytrace import AssayManifest
from assaytrace.approval.models import ApprovalStatus, DeviationApproval
from assaytrace.evidence.benchmark import BenchmarkPackage, MetricTriplet
from assaytrace.policy import parse_policy
from assaytrace.reporting import build_binder, presentation
from assaytrace._policy_demo import demo_policy_dict, demo_germline_policy_dict
from examples.build import build
from examples.build_germline import build as build_germline

_GEN_AT = datetime(2026, 6, 4, tzinfo=timezone.utc)

_SEV_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _rename(d: dict, name: str, assay_type: str | None = None) -> dict:
    d = copy.deepcopy(d)
    d["assay"]["assay_name"] = name
    if assay_type:
        d["assay"]["assay_type"] = assay_type
    return d


def _approvals_for(binder, mode: str) -> list[DeviationApproval]:
    """Build approval events for a binder's decisions deterministically."""
    ids = [d.change_id for d in binder.decisions]
    if mode == "none" or not ids:
        return []
    out: list[DeviationApproval] = []
    for i, cid in enumerate(ids):
        status = ApprovalStatus.APPROVED
        if mode == "pending_one" and i == len(ids) - 1:
            status = ApprovalStatus.PENDING
        out.append(DeviationApproval(
            change_id=cid, status=status, reviewer="Lab Director",
            approval_date="2026-06-03",
            approval_id=f"APR-{abs(hash(cid)) % 10000:04d}",
        ))
    return out


def _benchmarks(major_drop: bool):
    import glob
    import json
    base_path = glob.glob("**/benchmark_baseline.json", recursive=True)[0]
    base = BenchmarkPackage.model_validate(json.load(open(base_path)))
    cur = base.model_dump(mode="json")
    # Degrade one metric AND recompute its f1 so the package stays internally
    # consistent (f1 must equal the harmonic mean of precision/recall).
    if major_drop:
        cur["snv"]["recall"] = round(base.as_metric_map()["snv_recall"] - 0.20, 4)
        cur["snv"]["f1"] = MetricTriplet.f1_for(
            cur["snv"]["precision"], cur["snv"]["recall"])
    else:
        cur["indel"]["recall"] = round(base.as_metric_map()["indel_recall"] - 0.05, 4)
        cur["indel"]["f1"] = MetricTriplet.f1_for(
            cur["indel"]["precision"], cur["indel"]["recall"])
    return base, BenchmarkPackage.model_validate(cur)


def _scenario(name, base_dump, mutate, policy_spec, approve, *, benchmarks=None,
              review_date="2026-05-20"):
    new_dump = copy.deepcopy(base_dump)
    mutate(new_dump)
    old = AssayManifest.model_validate(base_dump)
    new = AssayManifest.model_validate(new_dump)
    policy = parse_policy(policy_spec) if policy_spec else None
    bench = _benchmarks(benchmarks == "major") if benchmarks else (None, None)
    # First pass: discover decisions so approvals can target real change ids.
    first = build_binder(old, new, policy=policy, generated_at=_GEN_AT,
                         baseline_benchmark=bench[0], current_benchmark=bench[1])
    approvals = _approvals_for(first, approve)
    binder = build_binder(old, new, policy=policy, approvals=approvals,
                          generated_at=_GEN_AT,
                          baseline_benchmark=bench[0], current_benchmark=bench[1])
    return name, binder, policy_spec, review_date


def _build_scenarios():
    som = build().model_dump(mode="json")
    germ = build_germline().model_dump(mode="json")

    def m_caller(ver):
        def f(d): d["analysis_components"]["variant_caller"]["version"] = ver
        return f

    def m_refgenome(d):
        d["reference_resources"]["reference_genome"]["version"] = "GRCh38.p15-analysis-set"

    def m_annotation(d):
        for r in d["reference_resources"]["annotation_resources"]:
            if r.get("name") == "ClinVar":
                r["version"] = "2026-03-01"

    def m_env(d):
        d["environment"]["image_digest"]["value"] = "f" * 64

    def m_multi(d):
        m_caller("4.6.0.0")(d); m_annotation(d); m_refgenome(d)
        for t in d["qc"]["thresholds"]:
            if t["metric"] == "minimum_vaf":
                t["threshold"] = 0.03
        m_env(d)

    return [
        _scenario("SolidTumor500", _rename(som, "SolidTumor500", "somatic"),
                  m_multi, demo_policy_dict(), "pending_one", review_date="2026-05-28"),
        _scenario("BRCA Germline", _rename(germ, "BRCA Germline", "germline"),
                  m_caller("4.6.0.0"), demo_germline_policy_dict(), "all",
                  review_date="2026-05-30"),
        _scenario("Myeloid Panel", _rename(som, "Myeloid Panel", "somatic"),
                  m_annotation, demo_policy_dict(), "all", review_date="2026-05-22"),
        _scenario("RNA Fusion", _rename(som, "RNA Fusion", "somatic"),
                  m_caller("5.0.0.0"), demo_policy_dict(), "none", review_date="2026-06-01"),
        _scenario("Liquid Biopsy", _rename(som, "Liquid Biopsy", "somatic"),
                  m_env, demo_policy_dict(), "none", review_date="2026-05-18"),
        _scenario("Colon Panel", _rename(som, "Colon Panel", "somatic"),
                  m_caller("4.6.0.0"), demo_policy_dict(), "all",
                  benchmarks="major", review_date="2026-05-25"),
    ]


def _assay_row(name, binder, policy_spec, review_date) -> dict:
    agg = presentation.aggregate(binder)
    gate = presentation.regression_gate_view(binder)
    pending = sum(1 for a in binder.approvals if a.status.value == "pending")
    policy_name = "Built-in defaults"
    policy_version = "—"
    if policy_spec:
        pol = parse_policy(policy_spec)
        policy_name = pol.name
        # Reflect the active SOP version from the registry (deterministic), so the
        # portfolio is consistent with the Policy Management tab.
        from assaytrace._policy_demo import demo_policy_registry
        atype = (policy_spec.get("assay_type") or "").lower()
        active = [d for d in demo_policy_registry()
                  if d["status"] == "active" and (d["assay_type"] or "") == atype]
        policy_version = active[0]["version"] if active else pol.version
    return {
        "assay": name,
        "status": presentation.portfolio_status(binder),
        "risk": (agg["highest_severity"] or "none").upper(),
        "policy": policy_name,
        "policy_version": policy_version,
        "last_review": review_date,
        "required_action": agg["recommended_scope"],
        "pending_approvals": pending,
        "decision_count": len(binder.decisions),
        "regression_status": gate["state"].replace("_", " ").title(),
        "claims_impacted": agg["claims_impacted"],
    }


def demo_portfolio() -> dict:
    """Assemble the deterministic portfolio dashboard payload."""
    rows = [_assay_row(*s) for s in _build_scenarios()]

    def count(status):
        return sum(1 for r in rows if r["status"] == status)

    kpis = {
        "total_assays": len(rows),
        "approved": count("Approved"),
        "under_review": count("Under Review"),
        "draft": count("Draft"),
        "blocked": count("Blocked"),
        "revalidation_required": count("Revalidation Required"),
        "pending_approvals": sum(r["pending_approvals"] for r in rows),
        "open_revalidations": sum(
            1 for r in rows if r["status"] in {"Revalidation Required", "Under Review", "Blocked"}
        ),
        "high_risk": sum(1 for r in rows if r["risk"] in {"HIGH", "CRITICAL"}),
    }
    risk = {level: sum(1 for r in rows if r["risk"] == level)
            for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE")}
    risk = {k: v for k, v in risk.items() if v or k in ("HIGH", "MEDIUM", "LOW")}

    timeline = [
        {"date": "2026-06-01", "event": "BRCA Germline SOP v3 activated"},
        {"date": "2026-06-02", "event": "RNA Fusion workflow updated (caller 5.0.0.0)"},
        {"date": "2026-06-03", "event": "Reference-genome review completed (SolidTumor500)"},
        {"date": "2026-06-04", "event": "Colon Panel benchmark regression flagged (BLOCKED)"},
    ]
    return {"assays": rows, "kpis": kpis, "risk_distribution": risk, "timeline": timeline}
