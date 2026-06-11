"""Deterministic presentation layer.

The single source of the "human-readable" view of an ``AuditBinder``: per-decision
rows (joining change, severity, policy rule, operational impact, and approval),
an aggregate roll-up, a recommended next-step sentence, and an audit timeline.

Both the web API and the PDF renderer import this module, so the Dashboard,
Audit view, and PDF binder are guaranteed consistent. Every value here is
derived from existing binder data via lookups/templates — no AI, no free text.
"""

from __future__ import annotations

from .. import labels, operational
from ..decision.models import RevalidationType

_REVAL_RANK = {
    "no_revalidation_required": 0, "documentation_update": 1,
    "infrastructure_verification": 2, "qc_verification": 3,
    "classification_concordance_review": 4, "targeted_analytical_revalidation": 5,
    "scope_review_and_targeted_validation": 6,
    "full_or_targeted_analytical_revalidation": 7, "full_analytical_revalidation": 8,
}
_SEV_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_NON_REVAL = {"no_revalidation_required", "documentation_update"}


def _by_change(binder):
    sev = {s.change_id: s for s in binder.change_severities}
    appr = {a.change_id: a for a in binder.approvals}
    chg = {c.change_id: c for c in binder.changes}
    return sev, appr, chg


def decision_views(binder) -> list[dict]:
    """One fully-joined, presentation-ready row per decision."""
    sev, appr, chg = _by_change(binder)
    rows: list[dict] = []
    for d in binder.decisions:
        change = chg.get(d.change_id)
        category = change.category if change else None
        s = sev.get(d.change_id)
        magnitude = s.version_magnitude if s else None
        op = operational.estimate(d.change_id, d.decision_type, len(d.affected_claims))
        a = appr.get(d.change_id)
        rows.append({
            "change_id": d.change_id,
            "identity": change.component_identity if change else d.change_id,
            "description": change.description if change else d.change_id,
            "category": category.value if category else None,
            "category_label": labels.category_label(category),
            "version_magnitude": (magnitude.value if magnitude else "none"),
            "magnitude_word": labels.magnitude_word(magnitude),
            "severity": (s.severity.value if s else None),
            "severity_reasons": list(s.reasons) if s else [],
            "impact_domain": d.impact_domain.value,
            "rule_id": d.triggered_by_rule,
            "rule_label": labels.rule_label(
                d.triggered_by_rule, category=category,
                change_type=(change.change_type if change else None),
                magnitude=magnitude,
            ),
            "action": d.decision_type.value,
            "action_label": labels.revalidation_label(d.decision_type),
            "affected_claims": list(d.affected_claims),
            "rationale": d.rationale,
            "required_evidence": list(d.required_evidence),
            "policy_name": binder.policy_name,
            "policy_version": binder.policy_version,
            "policy_hash": (binder.policy_hash[:12] if binder.policy_hash else None),
            "policy_hash_full": binder.policy_hash,
            "operational": {
                "revalidation_scope": op.revalidation_scope,
                "expected_benchmark_runs": op.expected_benchmark_runs,
                "estimated_effort": op.estimated_effort,
                "estimated_review_time": op.estimated_review_time,
                "affected_claims": op.affected_claims,
            },
            "approval": {
                "status": (a.status.value if a else "not_reviewed"),
                "status_label": labels.approval_status_label(a.status.value if a else None),
                "disposition": labels.approval_disposition(a.status.value if a else None),
                "approval_id": (a.approval_id if a else None),
                "reviewer": (a.reviewer if a else None),
                "approval_date": (a.approval_date if a else None),
                "conditions": (a.conditions if a else None),
                "rationale": (a.rationale if a else None),
                "history": [
                    {
                        "approval_id": e.approval_id,
                        "status": e.status.value,
                        "status_label": labels.approval_status_label(e.status.value),
                        "reviewer": e.reviewer,
                        "date": e.date,
                        "conditions": e.conditions,
                        "rationale": e.rationale,
                    }
                    for e in (a.history if a else ())
                ],
            },
        })
    return rows


def aggregate(binder) -> dict:
    """Roll-up answering: what changed, highest risk, claims, actions, approvals.

    Includes an operational summary (recommended scope, effort, review time)
    derived from the dominant revalidation action.
    """
    claims = sorted({c for d in binder.decisions for c in d.affected_claims})
    reval = [d for d in binder.decisions if d.decision_type.value not in _NON_REVAL]
    reval_actions = len(reval)
    approved = sum(
        1 for a in binder.approvals
        if a.status.value in {"approved", "approved_with_conditions"}
    )
    highest = max(
        (s.severity.value for s in binder.change_severities),
        key=lambda v: _SEV_RANK[v], default=None,
    )
    ops = [
        operational.estimate(d.change_id, d.decision_type, len(d.affected_claims))
        for d in binder.decisions
    ]
    total_runs = sum(o.expected_benchmark_runs for o in ops)
    highest_effort = max(
        (o.estimated_effort for o in ops),
        key=lambda e: operational.EFFORT_RANK.get(e, 0), default="None",
    )
    # Dominant revalidation action drives the recommended scope / review time.
    strongest = max(
        reval, key=lambda d: _REVAL_RANK.get(d.decision_type.value, 0), default=None
    )
    recommended_scope = (
        labels.revalidation_label(strongest.decision_type) if strongest else "None"
    )
    estimated_review_time = "None"
    if strongest is not None:
        estimated_review_time = operational.estimate(
            strongest.change_id, strongest.decision_type,
            len(strongest.affected_claims),
        ).estimated_review_time
    return {
        "changes": len(binder.changes),
        "claims_impacted": len(claims),
        "affected_claims": claims,
        "revalidation_actions": reval_actions,
        "approved_deviations": approved,
        "highest_severity": highest,
        "total_benchmark_runs": total_runs,
        "highest_effort": highest_effort,
        "recommended_scope": recommended_scope,
        "estimated_review_time": estimated_review_time,
        "policy_name": binder.policy_name,
    }


def top_impact_changes(binder, limit: int = 3) -> list[dict]:
    """Highest-priority changes for the Dashboard preview (Sprint 2).

    Sorted by severity, then revalidation weight, then change id. Titles reuse
    the same human ``rule_label`` shown on the Audit page so the Dashboard
    previews exactly what the reviewer will open next.
    """
    rows = decision_views(binder)
    rows.sort(
        key=lambda r: (
            -_SEV_RANK.get(r["severity"] or "low", 0),
            -_REVAL_RANK.get(r["action"], 0),
            r["change_id"],
        )
    )
    return [
        {
            "title": r["rule_label"],
            "identity": r["identity"],
            "severity": r["severity"],
            "action_label": r["action_label"],
            "affected_claims": r["affected_claims"],
        }
        for r in rows[: max(0, limit)]
    ]


def recommended_next_step(binder) -> str:
    """Action-oriented sentence built from the strongest decision + its claims.

    The Regression Gate (Critical Issue #2) overrides the recommendation: a
    BLOCKED gate cannot be auto-approved, and a MANUAL_REVIEW gate is surfaced.
    """
    gate = binder.regression_gate
    if gate is not None and gate.state.value == "blocked":
        return (
            "Revalidation BLOCKED by the regression gate: "
            f"{', '.join(gate.blocking_metrics)} regressed beyond the major "
            "threshold. Resolve the regression before this binder can be approved."
        )

    reval = [
        d for d in binder.decisions if d.decision_type.value not in _NON_REVAL
    ]
    gate_suffix = ""
    if gate is not None and gate.state.value == "manual_review":
        gate_suffix = (
            " Manual review of the minor performance regression is also required."
        )

    if not reval:
        if binder.changes:
            return (
                "No analytical revalidation required. Record the documentation / "
                "infrastructure changes and proceed to release." + gate_suffix
            )
        return "No changes detected between the two manifests."
    strongest = max(reval, key=lambda d: _REVAL_RANK.get(d.decision_type.value, 0))
    action = labels.revalidation_label(strongest.decision_type)
    claims = sorted({c for d in reval for c in d.affected_claims})
    if claims:
        if len(claims) == 1:
            who = claims[0]
        elif len(claims) == 2:
            who = f"{claims[0]} and {claims[1]}"
        else:
            who = ", ".join(claims[:-1]) + f", and {claims[-1]}"
        return f"Run {action.lower()} for {who} before production release." + gate_suffix
    return f"Run {action.lower()} before production release." + gate_suffix


def timeline(binder) -> list[dict]:
    """Interactive audit-reasoning timeline.

    Each stage carries both a one-line ``detail`` and an ``items`` list — the
    evidence behind that stage — so the UI can expand a stage to replay the
    reasoning. Deterministic; explanation layer, not a workflow engine.
    """
    policy_matched = sum(
        1 for d in binder.decisions if (d.triggered_by_rule or "").startswith("policy:")
    )
    reval_actions = sum(
        1 for d in binder.decisions if d.decision_type.value not in _NON_REVAL
    )
    reviewed = sum(1 for a in binder.approvals if a.status.value != "not_reviewed")
    sev = {s.change_id: s for s in binder.change_severities}
    meta = audit_metadata(binder)

    detected = [
        f"{c.description} [{(sev.get(c.change_id).severity.value.upper() if sev.get(c.change_id) else '-')}]"
        for c in binder.changes
    ]
    classified = [f"{i.change_id}: {i.impact_domain.value}" for i in binder.impacts]
    matched = [
        f"{labels.rule_label(d.triggered_by_rule)} ({d.triggered_by_rule})"
        for d in binder.decisions if (d.triggered_by_rule or "")
    ]
    assigned = [
        f"{(chg.component_identity if (chg := next((c for c in binder.changes if c.change_id == d.change_id), None)) else d.change_id)}"
        f" -> {labels.revalidation_label(d.decision_type)}"
        for d in binder.decisions
    ]
    approvals_ev = [
        f"{a.change_id}: {labels.approval_status_label(a.status.value)}"
        f"{f' (by {a.reviewer})' if a.reviewer else ''}"
        for a in binder.approvals if a.status.value != "not_reviewed"
    ] or ["No deviations reviewed yet."]
    binder_ev = [
        f"Audit artifact id: {meta['artifact_id']}",
        f"Binder hash: {meta['binder_hash'][:16]}",
        f"Policy: {meta['policy_name'] or 'Built-in defaults'} {meta['policy_version'] or ''}".strip(),
        f"Generated: {meta['generated_at']}",
    ]
    return [
        {"stage": "Detected", "detail": f"{len(binder.changes)} change(s) detected", "items": detected},
        {"stage": "Classified", "detail": f"{len(binder.impacts)} impact(s) classified", "items": classified},
        {"stage": "Policy Matched",
         "detail": (f"{policy_matched} matched policy '{binder.policy_name}'"
                    if binder.policy_name else f"{len(binder.decisions)} resolved by built-in rules"),
         "items": matched or ["All decisions resolved by built-in rules."]},
        {"stage": "Decision Assigned", "detail": f"{reval_actions} revalidation action(s) assigned", "items": assigned},
        {"stage": "Approval Reviewed", "detail": f"{reviewed} deviation(s) reviewed", "items": approvals_ev},
        {"stage": "Binder Generated", "detail": binder.generated_at.date().isoformat(), "items": binder_ev},
    ]


# Disposition states that count as a completed laboratory approval.
_APPROVED_STATES = {"approved", "approved_with_conditions"}


_REGRESSION_STATUS_LABEL = {
    "pass": "Pass", "manual_review": "Manual Review Required", "blocked": "Blocked",
}


def business_impact(binder) -> dict:
    """Executive, operations-first summary (Productization Sprint 2).

    Answers "what does this mean for the laboratory" before any technical
    detail: affected assays/claims, risk, action, effort, review time, benchmark
    runs, and the regression / approval / finalization posture. Pure roll-up of
    existing deterministic objects.
    """
    agg = aggregate(binder)
    lc = binder_lifecycle(binder)
    gate = binder.regression_gate
    gate_state = gate.state.value if gate is not None else "pass"
    return {
        "affected_assays": 1,  # one assay per binder; portfolio aggregates these
        "assay_name": binder.assay_name,
        "affected_claims": agg["claims_impacted"],
        "highest_risk": (agg["highest_severity"] or "none").upper(),
        "recommended_action": agg["recommended_scope"],
        "estimated_effort": agg["highest_effort"],
        "estimated_review_time": agg["estimated_review_time"],
        "required_benchmark_runs": agg["total_benchmark_runs"],
        "regression_status": _REGRESSION_STATUS_LABEL.get(gate_state, "Pass"),
        "approval_status": lc["status_label"],
        "finalizable": lc["can_finalize"],
    }


def portfolio_status(binder) -> str:
    """High-level assay status for the portfolio view (deterministic)."""
    gate = binder.regression_gate
    if gate is not None and gate.state.value == "blocked":
        return "Blocked"
    lc = binder_lifecycle(binder)
    if lc["status"] in {"FINALIZED", "APPROVED"}:
        return "Approved"
    if lc["status"] == "UNDER_REVIEW":
        return "Under Review"
    # Only true analytical revalidation drives "Revalidation Required"; pure
    # verification actions (infrastructure / QC / documentation) leave it Draft.
    analytical = {
        "targeted_analytical_revalidation", "full_analytical_revalidation",
        "full_or_targeted_analytical_revalidation",
        "scope_review_and_targeted_validation", "classification_concordance_review",
    }
    needs_reval = any(d.decision_type.value in analytical for d in binder.decisions)
    if lc["status"] == "DRAFT" and needs_reval:
        return "Revalidation Required"
    return "Draft"


def regression_gate_view(binder) -> dict:
    """Serialized regression gate (Critical Issue #2)."""
    g = binder.regression_gate
    if g is None:
        return {"state": "pass", "severity": "none", "evaluated": False,
                "rationale": "No regression gate evaluated.",
                "blocking_metrics": [], "review_metrics": []}
    return {
        "state": g.state.value,
        "severity": g.severity,
        "evaluated": g.evaluated,
        "rationale": g.rationale,
        "blocking_metrics": list(g.blocking_metrics),
        "review_metrics": list(g.review_metrics),
    }


def binder_lifecycle(binder) -> dict:
    """Deterministic binder lifecycle state (Critical Issue #3).

    States: DRAFT, UNDER_REVIEW, APPROVED, FINALIZED. The binder cannot be
    FINALIZED while any approval is Pending Review, any decision is Rejected, or
    the Regression Gate is BLOCKED — so an unresolved or failing assessment can
    never present as a finished audit artifact.
    """
    appr = {a.change_id: a.status.value for a in binder.approvals}
    statuses = [appr.get(d.change_id, "not_reviewed") for d in binder.decisions]

    gate = binder.regression_gate
    gate_blocked = gate is not None and gate.state.value == "blocked"
    gate_review = gate is not None and gate.state.value == "manual_review"

    any_rejected = any(s == "rejected" for s in statuses)
    any_pending = any(s == "pending" for s in statuses)
    any_unreviewed = any(s == "not_reviewed" for s in statuses)
    reviewed_any = any(s != "not_reviewed" for s in statuses)
    has_decisions = bool(statuses)
    approved_all = has_decisions and all(s in _APPROVED_STATES for s in statuses)
    conditional = any(s == "approved_with_conditions" for s in statuses)

    reasons: list[str] = []
    if gate_blocked:
        reasons.append("Regression gate is BLOCKED (major performance regression).")
    if any_rejected:
        reasons.append("At least one decision is Rejected.")
    if any_pending:
        reasons.append("At least one approval is Pending Review.")
    if any_unreviewed and reviewed_any:
        reasons.append("At least one decision is Not Reviewed.")
    if not reviewed_any and has_decisions and not (gate_blocked or any_rejected):
        reasons.append("No decisions have been reviewed yet.")
    if gate_review and not (gate_blocked or any_rejected):
        reasons.append("Regression gate requires manual review.")
    if conditional and not (gate_blocked or any_rejected or any_pending or any_unreviewed):
        reasons.append("Approval(s) granted With Conditions.")

    if gate_blocked or any_rejected:
        status = "DRAFT"
    elif not reviewed_any:
        status = "DRAFT"            # untouched: nothing reviewed yet
    elif any_pending or any_unreviewed:
        status = "UNDER_REVIEW"     # review in progress
    elif approved_all:
        status = "FINALIZED" if (not conditional and not gate_review) else "APPROVED"
    else:
        status = "DRAFT"

    watermark = {"DRAFT": "DRAFT", "UNDER_REVIEW": "UNDER REVIEW"}.get(status)
    return {
        "status": status,
        "status_label": status.replace("_", " ").title(),
        "can_finalize": status == "FINALIZED",
        "watermark": watermark,
        "reasons": reasons or ["All decisions approved; gate clear."],
        "regression_gate": regression_gate_view(binder),
    }


def governance_status(binder) -> dict:
    """Approval KPI across all decisions (Sprint A first-class governance view)."""
    appr = {a.change_id: a.status.value for a in binder.approvals}
    counts = {
        "not_reviewed": 0, "pending": 0, "approved": 0,
        "approved_with_conditions": 0, "rejected": 0,
    }
    for d in binder.decisions:
        counts[appr.get(d.change_id, "not_reviewed")] += 1
    return {
        "decisions": len(binder.decisions),
        "not_reviewed": counts["not_reviewed"],
        "pending": counts["pending"],
        "approved": counts["approved"],
        "approved_with_conditions": counts["approved_with_conditions"],
        "rejected": counts["rejected"],
        "reviewed": sum(v for k, v in counts.items() if k != "not_reviewed"),
    }


def audit_metadata(binder) -> dict:
    """Deterministic governance metadata for the audit artifact.

    ``binder_hash`` is a SHA-256 over the binder's content (manifest hashes,
    changes, decisions, severities, approvals, and policy identity) — stable
    across runs and independent of the generation timestamp, so the same
    analysis always yields the same artifact id. ``artifact_id`` derives from it.
    """
    import hashlib
    import json

    content = {
        "old_content_hash": binder.old_content_hash,
        "new_content_hash": binder.new_content_hash,
        "policy_name": binder.policy_name,
        "policy_version": binder.policy_version,
        "policy_hash": binder.policy_hash,
        "changes": sorted(c.change_id for c in binder.changes),
        "decisions": sorted(
            f"{d.change_id}|{d.decision_type.value}|{d.triggered_by_rule}"
            for d in binder.decisions
        ),
        "severities": sorted(
            f"{s.change_id}|{s.severity.value}" for s in binder.change_severities
        ),
        "approvals": sorted(
            f"{a.change_id}|{a.status.value}|{a.approval_id or ''}"
            for a in binder.approvals
        ),
    }
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    binder_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    artifact_id = "AT-" + binder_hash[:12].upper()
    reviewed = [a for a in binder.approvals if a.status.value != "not_reviewed"]
    return {
        "artifact_id": artifact_id,
        "binder_hash": binder_hash,
        "policy_name": binder.policy_name,
        "policy_version": binder.policy_version,
        "policy_hash": binder.policy_hash,
        "old_manifest_hash": binder.old_content_hash,
        "new_manifest_hash": binder.new_content_hash,
        "generated_at": binder.generated_at.isoformat(),
        "change_count": len(binder.changes),
        "decision_count": len(binder.decisions),
        "approval_count": len(reviewed),
        "approval_ids": sorted(a.approval_id for a in reviewed if a.approval_id),
    }
