"""Production PDF export for the audit binder (Part 4).

Renders a real, multi-page PDF (not a placeholder) from the existing
``AuditBinder`` model using fpdf2 — pure Python, no system libraries, works on
Windows. Layout uses the AssayTrace brand palette. Output is deterministic
given the binder (the document creation date is pinned to the binder's
``generated_at``).
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from .models import AuditBinder

# Brand palette (RGB)
_NAVY = (15, 23, 42)       # #0F172A
_CYAN = (6, 182, 212)      # #06B6D4
_VIOLET = (124, 58, 237)   # #7C3AED
_RED = (239, 68, 68)       # #EF4444
_GREEN = (16, 185, 129)    # #10B981
_AMBER = (245, 158, 11)    # #F59E0B
_GREY = (100, 116, 139)
_LIGHT = (241, 245, 249)


def _s(text: object) -> str:
    """Sanitize text for the latin-1 core PDF fonts (no Unicode font dep)."""
    return (
        str(text)
        .replace("\u2022", "-").replace("\u0394", "d").replace("\u2026", "...")
        .replace("\u2265", ">=").replace("\u2264", "<=")
        .replace("\u2013", "-").replace("\u2014", "-")
        .encode("latin-1", "replace").decode("latin-1")
    )


class _Report(FPDF):
    title_text = "AssayTrace — Change-Control & Revalidation Binder"
    watermark: str | None = None

    def header(self) -> None:
        self.set_fill_color(*_NAVY)
        self.rect(0, 0, self.w, 22, style="F")
        self.set_xy(12, 6)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 6, "AssayTrace")
        self.set_xy(12, 13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_CYAN)
        self.cell(0, 4, "www.assaytrace.com  ·  Change-Control & Revalidation Binder")
        self.set_y(28)
        self.set_text_color(*_NAVY)
        if self.watermark:
            self._draw_watermark(self.watermark)

    def _draw_watermark(self, text: str) -> None:
        # Large, light, diagonal stamp behind content (DRAFT / UNDER REVIEW).
        self.set_font("Helvetica", "B", 60)
        self.set_text_color(232, 196, 196)
        with self.rotation(45, self.w / 2, self.h / 2):
            self.text(
                self.w / 2 - len(text) * 9, self.h / 2 + 10, text
            )
        self.set_text_color(*_NAVY)
        self.set_y(28)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*_GREY)
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="C")


def _h2(pdf: _Report, text: str) -> None:
    if pdf.get_y() > pdf.h - 40:
        pdf.add_page()
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_VIOLET)
    pdf.cell(0, 7, _s(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*_CYAN)
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(2)
    pdf.set_text_color(*_NAVY)


def _paragraph(pdf: _Report, text: str) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_NAVY)
    pdf.multi_cell(0, 5, _s(text))
    pdf.ln(1)


def _empty(pdf: _Report, text: str) -> None:
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*_GREY)
    pdf.multi_cell(0, 5, text)
    pdf.ln(1)
    pdf.set_text_color(*_NAVY)


def _table(pdf: _Report, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    epw = pdf.w - pdf.l_margin - pdf.r_margin
    widths = [w / sum(widths) * epw for w in widths]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*_NAVY)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, _s(h), border=0, fill=True)
    pdf.ln(6)
    pdf.set_text_color(*_NAVY)
    pdf.set_font("Helvetica", "", 8)
    fill = False
    for row in rows:
        line_h = 4.6
        heights = []
        for text, w in zip(row, widths):
            n = max(1, pdf.multi_cell(w, line_h, _s(text), dry_run=True, output="LINES").__len__())
            heights.append(n * line_h)
        row_h = max(heights)
        if pdf.get_y() + row_h > pdf.h - 16:
            pdf.add_page()
        pdf.set_fill_color(*( _LIGHT if fill else (255, 255, 255)))
        x0, y0 = pdf.get_x(), pdf.get_y()
        for text, w in zip(row, widths):
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(w, line_h, _s(text), border=0, fill=True,
                           max_line_height=line_h, new_x="RIGHT", new_y="TOP")
            pdf.set_xy(x + w, y)
        pdf.set_xy(x0, y0 + row_h)
        fill = not fill
    pdf.ln(2)


def _status_color(status: str):
    s = status.lower()
    if "regression" in s:
        return _RED
    if "improved" in s:
        return _GREEN
    return _GREY


def render_pdf(binder: AuditBinder, path: str | Path | None = None) -> bytes:
    """Render the audit binder to a PDF. Returns the bytes; also writes to
    ``path`` when provided."""
    b = binder
    pdf = _Report(orientation="P", unit="mm", format="A4")
    pdf.set_title("AssayTrace Change-Control Binder")
    pdf.set_creation_date(b.generated_at)
    pdf.set_author("AssayTrace")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    from . import presentation
    lifecycle = presentation.binder_lifecycle(b)
    gate_view = presentation.regression_gate_view(b)
    pdf.watermark = lifecycle["watermark"]
    pdf.add_page()

    # Title block / decision banner
    revalidation_needed = any(
        d.decision_type.value not in {"no_revalidation_required", "documentation_update"}
        for d in b.decisions
    )
    banner = "REVALIDATION REQUIRED" if revalidation_needed else "SAFE TO DEPLOY"
    banner_color = _AMBER if revalidation_needed else _GREEN
    pdf.set_fill_color(*banner_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 11, _s(f"  {banner}"), border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_text_color(*_NAVY)
    pdf.set_font("Helvetica", "", 9)
    for label, value in [
        ("Assay", f"{b.assay_name} v{b.assay_version}"),
        ("Laboratory", f"{b.laboratory_name} ({b.laboratory_id})"),
        ("Generated", b.generated_at.isoformat()),
        ("Old manifest", f"{b.old_manifest_id} [{b.old_content_hash[:16]}]"),
        ("New manifest", f"{b.new_manifest_id} [{b.new_content_hash[:16]}]"),
    ]:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(32, 5, _s(label), new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, _s(value), new_x="LMARGIN", new_y="NEXT")

    sev_by_change = {s.change_id: s for s in b.change_severities}
    appr_by_change = {a.change_id: a for a in b.approvals}

    # Deterministic presentation view (shared with the web UI).
    from . import presentation
    agg = presentation.aggregate(b)
    views = {v["change_id"]: v for v in presentation.decision_views(b)}
    next_step = presentation.recommended_next_step(b)
    meta = presentation.audit_metadata(b)
    gov = presentation.governance_status(b)
    bimpact = presentation.business_impact(b)

    # --- Page 1 priority order (Pilot Readiness): Executive Summary and
    # Business Impact first (what happened / how much work / what next), then
    # the governance approval summary, then Audit Metadata lower on the page. ---
    _h2(pdf, "Executive Summary")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_NAVY)
    pdf.cell(34, 5, _s("Recommended"), new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, _s(next_step), new_x="LMARGIN", new_y="NEXT")
    for label, value in [
        ("Decision", banner),
        ("What changed", agg["changes"] and
            next((c.description for c in b.changes), "-") or "No changes"),
        ("Highest severity", (agg["highest_severity"] or "-").upper()),
        ("Affected claims", ", ".join(agg["affected_claims"]) or "None"),
        ("Policy in effect", b.policy_name or "Built-in defaults"),
        ("Required action", _s(next_step)),
    ]:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(34, 5, _s(label), new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, _s(str(value)), new_x="LMARGIN", new_y="NEXT")

    # Business Impact Summary — operations-first decision-making view.
    _h2(pdf, "Business Impact Summary")
    _table(
        pdf, ["Business Question", "Answer"],
        [
            ["Affected Assays", str(bimpact["affected_assays"])],
            ["Affected Clinical Claims", str(bimpact["affected_claims"])],
            ["Highest Risk", bimpact["highest_risk"]],
            ["Recommended Action", bimpact["recommended_action"]],
            ["Estimated Laboratory Effort", bimpact["estimated_effort"]],
            ["Estimated Review Time", bimpact["estimated_review_time"]],
            ["Required Benchmark Runs", str(bimpact["required_benchmark_runs"])],
            ["Regression Status", bimpact["regression_status"]],
            ["Approval Status", bimpact["approval_status"]],
            ["Finalizable", "Yes" if bimpact["finalizable"] else "No"],
        ],
        [4.5, 5.5],
    )

    # Approval Summary (governance KPI): disposition counts across decisions.
    _h2(pdf, "Approval Summary")
    _table(
        pdf, ["Disposition", "Count"],
        [
            ["Decisions", str(gov["decisions"])],
            ["Not Reviewed", str(gov["not_reviewed"])],
            ["Pending Review", str(gov["pending"])],
            ["Approved", str(gov["approved"])],
            ["Approved With Conditions", str(gov["approved_with_conditions"])],
            ["Rejected", str(gov["rejected"])],
        ],
        [5, 2],
    )

    # Audit Metadata & Governance: kept on page 1 but at lower visual priority,
    # below the executive/business/approval views the QA reader needs first.
    _h2(pdf, "Audit Metadata")
    _table(
        pdf, ["Field", "Value"],
        [
            ["Binder Status", f"{lifecycle['status_label']} "
                              f"({'finalizable' if lifecycle['can_finalize'] else 'not finalizable'})"],
            ["Regression Gate", f"{gate_view['state'].replace('_', ' ').upper()} "
                                f"({gate_view['severity']})"],
            ["Audit Artifact ID", meta["artifact_id"]],
            ["Binder Hash (SHA-256)", meta["binder_hash"]],
            ["Policy", f"{meta['policy_name'] or 'Built-in defaults'} "
                       f"{meta['policy_version'] or ''}".strip()],
            ["Policy Hash (SHA-256)", meta["policy_hash"] or "-"],
            ["Old Manifest Hash", meta["old_manifest_hash"]],
            ["New Manifest Hash", meta["new_manifest_hash"]],
            ["Generation Timestamp", meta["generated_at"]],
            ["Change / Decision Count", f"{meta['change_count']} / {meta['decision_count']}"],
            ["Approval Count", str(meta["approval_count"])],
            ["Approval IDs", ", ".join(meta["approval_ids"]) or "None"],
        ],
        [3.4, 6],
    )
    if lifecycle["status"] != "FINALIZED":
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*_GREY)
        pdf.multi_cell(0, 4.4, _s("Binder not finalizable: " + "; ".join(lifecycle["reasons"])),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_NAVY)
    if gate_view["evaluated"]:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*_GREY)
        pdf.multi_cell(0, 4.4, _s("Regression gate: " + gate_view["rationale"]),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_NAVY)

    # Audit reasoning timeline, promoted to a first-class position (Sprint 3).
    _h2(pdf, "Audit Reasoning Timeline")
    for i, step in enumerate(presentation.timeline(b), start=1):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_NAVY)
        pdf.cell(8, 4.8, _s(f"{i}."), new_x="RIGHT", new_y="TOP")
        pdf.cell(46, 4.8, _s(step["stage"]), new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_GREY)
        pdf.multi_cell(0, 4.8, _s(step["detail"]), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_NAVY)

    # Operational summary: what work the laboratory needs to do (Sprint 1).
    _h2(pdf, "Operational Summary")
    _table(
        pdf, ["Operational Question", "Answer"],
        [
            ["Affected Clinical Claims", str(agg["claims_impacted"])],
            ["Highest Risk Level", (agg["highest_severity"] or "-").upper()],
            ["Recommended Revalidation Scope", agg["recommended_scope"]],
            ["Estimated Laboratory Effort", agg["highest_effort"]],
            ["Estimated Review Time", agg["estimated_review_time"]],
            ["Required Benchmark Runs", str(agg["total_benchmark_runs"])],
            ["Approved Deviations", str(agg["approved_deviations"])],
        ],
        [5, 3],
    )

    # 1. Change Summary
    _h2(pdf, "1. Change Summary")
    if b.changes:
        def _sev_label(cid):
            s = sev_by_change.get(cid)
            if not s:
                return "-"
            mag = s.version_magnitude.value
            return s.severity.value.upper() + ("" if mag in ("none", "") else f" ({mag})")
        _table(pdf, ["Type", "Identity", "Severity", "Old", "New"],
               [[c.change_type.value, c.component_identity, _sev_label(c.change_id),
                 "" if c.old_value is None else str(c.old_value),
                 "" if c.new_value is None else str(c.new_value)] for c in b.changes],
               [2.8, 3.4, 1.8, 1.8, 1.8])
    else:
        _empty(pdf, "No changes detected.")

    # 2. Impact Analysis
    _h2(pdf, "2. Impact Analysis")
    if b.impacts:
        _table(pdf, ["Change ID", "Impact Domain", "Rationale"],
               [[i.change_id, i.impact_domain.value, i.rationale] for i in b.impacts],
               [3, 2, 5])
    else:
        _empty(pdf, "No impacts.")

    # 3. Revalidation Decision
    _h2(pdf, "3. Revalidation Decision")
    if b.decisions:
        _table(pdf, ["Type", "Affected Claims", "Required Evidence"],
               [[d.decision_type.value, ", ".join(d.affected_claims) or "-",
                 "; ".join(d.required_evidence) or "-"] for d in b.decisions],
               [3, 3, 4])
    else:
        _empty(pdf, "No revalidation decisions (no changes).")

    # 4. Decision Chain (the explainable chain, per decision, with approval)
    _h2(pdf, "4. Decision Chain")
    if b.decisions:
        for d in b.decisions:
            v = views.get(d.change_id, {})
            ap = appr_by_change.get(d.change_id)
            mag = (v.get("version_magnitude") or "n/a").upper()
            sev = (v.get("severity") or "-").upper()
            claims = ", ".join(d.affected_claims) or "None"
            op = v.get("operational", {})

            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*_NAVY)
            pdf.multi_cell(0, 5, _s(f"- {v.get('identity', d.change_id)}"),
                           new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*_GREY)
            pdf.multi_cell(
                0, 4.6,
                _s(f"    Magnitude: {mag}   |   Severity: {sev}   |   "
                   f"Rule: {v.get('rule_label', '-')} ({d.triggered_by_rule or '-'})"),
                new_x="LMARGIN", new_y="NEXT",
            )
            for reason in v.get("severity_reasons", []):
                pdf.multi_cell(0, 4.6, _s(f"      - {reason}"),
                               new_x="LMARGIN", new_y="NEXT")
            pol_name = v.get("policy_name")
            if pol_name:
                pdf.multi_cell(
                    0, 4.6,
                    _s(f"    Policy source: {pol_name} {v.get('policy_version') or ''} "
                       f"(hash {v.get('policy_hash') or '-'})"),
                    new_x="LMARGIN", new_y="NEXT",
                )
            pdf.multi_cell(
                0, 4.6,
                _s(f"    Affected claims: {claims}   |   Action: {v.get('action_label', d.decision_type.value)}"),
                new_x="LMARGIN", new_y="NEXT",
            )
            pdf.multi_cell(
                0, 4.6,
                _s(f"    Operational impact: scope {op.get('revalidation_scope', '-')}, "
                   f"{op.get('expected_benchmark_runs', 0)} benchmark run(s), "
                   f"{op.get('estimated_effort', '-')} effort, "
                   f"review {op.get('estimated_review_time', '-')}"),
                new_x="LMARGIN", new_y="NEXT",
            )
            pdf.set_text_color(*_NAVY)
            pdf.multi_cell(0, 4.6, _s(f"    Why: {d.rationale}"), new_x="LMARGIN", new_y="NEXT")
            if d.required_evidence:
                pdf.multi_cell(
                    0, 4.6, _s("    Evidence: " + "; ".join(d.required_evidence)),
                    new_x="LMARGIN", new_y="NEXT",
                )
            appr = v.get("approval", {})
            if ap and ap.status.value != "not_reviewed":
                pdf.set_text_color(*_GREEN)
                pdf.multi_cell(
                    0, 4.6,
                    _s(f"    Approval [{appr.get('approval_id') or '-'}]: "
                       f"{appr.get('status_label', ap.status.value)} - "
                       f"{appr.get('disposition', '-')} - by "
                       f"{ap.reviewer or '-'} on {ap.approval_date or '-'}"
                       + (f" - conditions: {ap.conditions}" if ap.conditions else "")
                       + f" - {ap.rationale or '-'}"),
                    new_x="LMARGIN", new_y="NEXT",
                )
                history = appr.get("history") or []
                if len(history) > 1:
                    trail = " -> ".join(e.get("status_label", e.get("status", "")) for e in history)
                    pdf.set_text_color(*_GREY)
                    pdf.multi_cell(0, 4.6, _s(f"      History: {trail}"),
                                   new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.set_text_color(*_GREY)
                pdf.multi_cell(
                    0, 4.6, _s("    Approval: Not Reviewed"),
                    new_x="LMARGIN", new_y="NEXT",
                )
            pdf.set_text_color(*_NAVY)
            pdf.ln(1.5)
    else:
        _empty(pdf, "Not applicable.")
    for r in b.no_revalidation_records:
        _paragraph(pdf, f"- {r.rationale}")
    if b.orphan_approvals:
        pdf.set_text_color(*_RED)
        _paragraph(pdf, "Warning: the following approvals reference changes "
                        "that were not detected in this comparison: "
                        + ", ".join(b.orphan_approvals))
        pdf.set_text_color(*_NAVY)

    # 5. Benchmark Evidence
    _h2(pdf, "5. Benchmark Evidence")
    pkg = b.current_benchmark_pkg
    if pkg is not None:
        rows = [["sample_id", pkg.sample_id], ["benchmark", f"{pkg.benchmark_name} {pkg.benchmark_version}"],
                ["truthset", pkg.truthset], ["run_date", pkg.run_date.isoformat()]]
        for cls in ("snv", "indel", "cnv"):
            triplet = getattr(pkg, cls)
            if triplet is not None:
                rows.append([f"{cls.upper()} P/R/F1",
                             f"{triplet.precision:.4f} / {triplet.recall:.4f} / {triplet.f1:.4f}"])
        _table(pdf, ["Field", "Value"], rows, [3, 6])
    elif b.current_benchmark is not None:
        cur = b.current_benchmark
        rows = [[k, f"{v:.4f}"] for k, v in cur.as_metric_map().items()]
        rows.append(["sample", cur.sample])
        _table(pdf, ["Field", "Value"], rows, [3, 6])
    else:
        _empty(pdf, "No benchmark evidence provided.")

    # 6. Regression Analysis
    _h2(pdf, "6. Regression Analysis")
    if b.regression:
        _table(pdf, ["Metric", "Old", "New", "Delta", "Status"],
               [[m.metric, f"{m.old_value:.4f}", f"{m.new_value:.4f}",
                 f"{m.delta:+.4f}", m.status.value] for m in b.regression],
               [3, 1.4, 1.4, 1.4, 2.4])
        for m in b.regression:
            pdf.set_text_color(*_status_color(m.status.value))
            _paragraph(pdf, f"• {m.rationale}")
        pdf.set_text_color(*_NAVY)
    else:
        _empty(pdf, "No regression comparison (baseline + current benchmark required).")

    # 7. Reportable Variant Delta
    _h2(pdf, "7. Reportable Variant Delta")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_GREY)
    pdf.multi_cell(
        0, 4.4,
        _s("Scope: AssayTrace compares variant outputs supplied by the laboratory. "
           "It does not call, classify, reinterpret, or clinically interpret variants; "
           "the rows below report differences between two supplied result sets only."),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_text_color(*_NAVY)
    pdf.ln(1)
    if b.variant_classification_deltas:
        _table(pdf, ["Gene", "Variant", "Change", "Old", "New", "Explanation"],
               [[d.gene, d.variant, d.change_type.value,
                 d.old_classification.value if d.old_classification else "-",
                 d.new_classification.value if d.new_classification else "-",
                 d.explanation] for d in b.variant_classification_deltas],
               [1.4, 2.2, 1.8, 1.4, 1.4, 3.2])
    else:
        _empty(pdf, "No reportable-variant comparison provided.")

    # 8. Sign-Off Section
    _h2(pdf, "8. Sign-Off")
    so = b.sign_off
    _paragraph(pdf, so.statement)
    _table(pdf, ["Role", "Name", "Date"],
           [["Prepared by", so.prepared_by or "", so.prepared_date or ""],
            ["Reviewed by", so.reviewed_by or "", so.reviewed_date or ""],
            ["Approved by", so.approved_by or "", so.approved_date or ""]],
           [2, 4, 3])

    # 9. Disclaimer
    _h2(pdf, "9. Disclaimer")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_GREY)
    pdf.multi_cell(0, 4.5, _s(b.disclaimer))
    pdf.set_text_color(*_NAVY)

    out = bytes(pdf.output())
    if path is not None:
        Path(path).write_bytes(out)
    return out
