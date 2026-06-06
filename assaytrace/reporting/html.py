"""Deterministic HTML report generator for the audit binder (Step 12).

Pure-Python string rendering with HTML escaping — no templating dependency, no
network, no nondeterminism beyond the binder's own ``generated_at``. Given the
same ``AuditBinder`` the output bytes are identical.
"""

from __future__ import annotations

from html import escape

from .models import AuditBinder

_STYLE = """
body{font-family:Arial,Helvetica,sans-serif;margin:2rem;color:#1a1a1a;}
h1{font-size:1.5rem;border-bottom:2px solid #333;padding-bottom:.3rem;}
h2{font-size:1.1rem;margin-top:1.6rem;border-bottom:1px solid #ccc;}
table{border-collapse:collapse;width:100%;margin:.5rem 0;font-size:.85rem;}
th,td{border:1px solid #bbb;padding:.35rem .5rem;text-align:left;vertical-align:top;}
th{background:#f0f0f0;}
.meta td{border:none;padding:.15rem .5rem;}
.disclaimer{margin-top:2rem;padding:.8rem;background:#fbfbe6;border:1px solid #d8d8a0;font-size:.8rem;}
.signoff td{height:2.2rem;}
.empty{color:#777;font-style:italic;}
""".strip()


def _table(headers: list[str], rows: list[list[str]], empty: str) -> str:
    if not rows:
        return f'<p class="empty">{escape(empty)}</p>'
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_html(binder: AuditBinder) -> str:
    b = binder
    parts: list[str] = []
    parts.append(f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                 f"<title>AssayTrace Change-Control Binder</title>"
                 f"<style>{_STYLE}</style></head><body>")
    parts.append("<h1>AssayTrace Change-Control &amp; Revalidation Binder</h1>")

    parts.append("<table class='meta'>")
    for label, value in [
        ("Assay", f"{b.assay_name} v{b.assay_version}"),
        ("Laboratory", f"{b.laboratory_name} ({b.laboratory_id})"),
        ("Generated", b.generated_at.isoformat()),
        ("Old manifest", f"{b.old_manifest_id}  [{b.old_content_hash[:16]}…]"),
        ("New manifest", f"{b.new_manifest_id}  [{b.new_content_hash[:16]}…]"),
    ]:
        parts.append(f"<tr><td><b>{escape(label)}</b></td><td>{escape(value)}</td></tr>")
    parts.append("</table>")

    parts.append("<h2>1. Detected Changes</h2>")
    parts.append(_table(
        ["Change ID", "Type", "Identity", "Old", "New"],
        [[c.change_id, c.change_type.value, c.component_identity,
          "" if c.old_value is None else c.old_value,
          "" if c.new_value is None else c.new_value] for c in b.changes],
        "No changes detected.",
    ))

    parts.append("<h2>2. Impact Analysis</h2>")
    parts.append(_table(
        ["Change ID", "Impact Domain", "Rationale"],
        [[i.change_id, i.impact_domain.value, i.rationale] for i in b.impacts],
        "No impacts.",
    ))

    parts.append("<h2>3. Affected Assay Claims</h2>")
    parts.append(_table(
        ["Change ID", "Claim", "Type", "Impact", "Matched Via"],
        [[ci.change_id, ci.claim_id, ci.claim_type.value, ci.impact_domain.value,
          ci.rationale] for ci in b.claim_impacts],
        "No claims affected.",
    ))

    parts.append("<h2>4. Revalidation Decisions</h2>")
    parts.append(_table(
        ["Decision", "Type", "Rationale", "Affected Claims", "Required Evidence"],
        [[d.decision_id, d.decision_type.value, d.rationale,
          ", ".join(d.affected_claims) or "—",
          "; ".join(d.required_evidence) or "—"] for d in b.decisions],
        "No decisions.",
    ))

    parts.append("<h2>5. Defensible No-Revalidation Records</h2>")
    parts.append(_table(
        ["Decision", "Type", "Impact", "Rationale"],
        [[r.decision_id, r.decision_type.value, r.impact_domain.value, r.rationale]
         for r in b.no_revalidation_records],
        "No no-revalidation determinations.",
    ))

    parts.append("<h2>6. Benchmark Summary</h2>")
    if b.current_benchmark is not None:
        cur = b.current_benchmark
        rows = [[k, f"{v:.4f}"] for k, v in cur.as_metric_map().items()]
        rows.append(["sample", cur.sample])
        rows.append(["comparison_date", cur.comparison_date.isoformat()])
        rows.append(["evidence_source", cur.evidence_source])
        parts.append(_table(["Field", "Value"], rows, "No benchmark."))
    else:
        parts.append('<p class="empty">No benchmark evidence provided.</p>')

    parts.append("<h2>7. Performance Regression Summary</h2>")
    parts.append(_table(
        ["Metric", "Old", "New", "Delta", "Status"],
        [[m.metric, f"{m.old_value:.4f}", f"{m.new_value:.4f}",
          f"{m.delta:+.4f}", m.status.value] for m in b.regression],
        "No regression comparison (baseline + current benchmark required).",
    ))

    parts.append("<h2>8. Reportable Variant Deltas</h2>")
    parts.append(_table(
        ["Variant", "Old Status", "New Status", "Delta"],
        [[d.variant, d.old_status.value, d.new_status.value, d.delta_type.value]
         for d in b.reportable_deltas],
        "No reportable-variant comparison provided.",
    ))

    so = b.sign_off
    parts.append("<h2>9. Sign-Off</h2>")
    parts.append(f"<p>{escape(so.statement)}</p>")
    parts.append(_table(
        ["Role", "Name", "Date"],
        [
            ["Prepared by", so.prepared_by or "", so.prepared_date or ""],
            ["Reviewed by", so.reviewed_by or "", so.reviewed_date or ""],
            ["Approved by", so.approved_by or "", so.approved_date or ""],
        ],
        "",
    ).replace("<tbody>", "<tbody class='signoff'>"))

    parts.append(f"<div class='disclaimer'>{escape(b.disclaimer)}</div>")
    parts.append("</body></html>")
    return "".join(parts)