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

    # 1. Change Summary
    _h2(pdf, "1. Change Summary")
    if b.changes:
        _table(pdf, ["Type", "Identity", "Old", "New"],
               [[c.change_type.value, c.component_identity,
                 "" if c.old_value is None else str(c.old_value),
                 "" if c.new_value is None else str(c.new_value)] for c in b.changes],
               [3, 4, 2, 2])
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

    # 4. Decision Rationale
    _h2(pdf, "4. Decision Rationale")
    if b.decisions:
        for d in b.decisions:
            _paragraph(pdf, f"• [{d.decision_type.value}] {d.rationale}")
    else:
        _empty(pdf, "Not applicable.")
    for r in b.no_revalidation_records:
        _paragraph(pdf, f"• {r.rationale}")

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
