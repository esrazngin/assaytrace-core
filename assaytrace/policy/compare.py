"""Deterministic policy comparison (Productization Sprint 1).

Side-by-side diff of two policies for audit review: which rules were added,
removed, or modified, and how (action / severity-floor / rationale). Pure set
and field comparison keyed by ``rule_id`` — no inference.
"""

from __future__ import annotations

from .models import RevalidationPolicy


def _rule_map(policy: RevalidationPolicy) -> dict[str, object]:
    return {r.rule_id: r for r in policy.rules}


def compare_policies(a: RevalidationPolicy, b: RevalidationPolicy) -> dict:
    """Return a deterministic diff of policy ``a`` (base) vs ``b`` (candidate)."""
    ma, mb = _rule_map(a), _rule_map(b)
    added, removed, modified = [], [], []

    for rid in sorted(mb.keys() - ma.keys()):
        r = mb[rid]
        added.append({"rule_id": rid, "action": r.action.value,
                      "rationale": r.rationale or ""})
    for rid in sorted(ma.keys() - mb.keys()):
        r = ma[rid]
        removed.append({"rule_id": rid, "action": r.action.value,
                        "rationale": r.rationale or ""})
    for rid in sorted(ma.keys() & mb.keys()):
        ra, rb = ma[rid], mb[rid]
        changes = []
        if ra.action != rb.action:
            changes.append({"field": "action",
                            "from": ra.action.value, "to": rb.action.value})
        if (ra.rationale or "") != (rb.rationale or ""):
            changes.append({"field": "rationale",
                            "from": ra.rationale or "", "to": rb.rationale or ""})
        if changes:
            modified.append({"rule_id": rid, "changes": changes})

    return {
        "base": {"name": a.name, "version": a.version, "hash": a.content_hash()},
        "candidate": {"name": b.name, "version": b.version, "hash": b.content_hash()},
        "added_rules": added,
        "removed_rules": removed,
        "modified_rules": modified,
        "identical": not (added or removed or modified),
        # Decision-logic change is any add/remove/modify of an action.
        "decision_logic_changed": bool(added or removed or any(
            any(c["field"] == "action" for c in m["changes"]) for m in modified
        )),
    }
