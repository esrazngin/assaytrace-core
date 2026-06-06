from __future__ import annotations

import json
from datetime import date

from assaytrace.cli.main import main
from assaytrace.evidence import GiabEvidencePackage
from examples.build import build


def _write_manifests(tmp_path):
    old = build()
    old_p = tmp_path / "old.json"
    old_p.write_text(json.dumps(old.model_dump(mode="json")), encoding="utf-8")
    d = old.model_dump(mode="json")
    d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"
    new_p = tmp_path / "new.json"
    new_p.write_text(json.dumps(d), encoding="utf-8")
    return old_p, new_p


def test_cli_impact(tmp_path, capsys):
    old_p, new_p = _write_manifests(tmp_path)
    rc = main(["impact", "--old", str(old_p), "--new", str(new_p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Detected Changes" in out
    assert "variant_caller:mutect2" in out
    assert "analytical" in out


def test_cli_decision(tmp_path, capsys):
    old_p, new_p = _write_manifests(tmp_path)
    rc = main(["decision", "--old", str(old_p), "--new", str(new_p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "targeted_analytical_revalidation" in out
    assert "CLAIM-SNV-001" in out


def test_cli_audit_writes_html(tmp_path):
    old_p, new_p = _write_manifests(tmp_path)
    ev = tmp_path / "ev.json"
    ev.write_text(json.dumps(GiabEvidencePackage(
        snv_precision=0.999, snv_recall=0.995, indel_precision=0.985,
        indel_recall=0.947, comparison_date=date(2026, 1, 15),
        evidence_source="src").model_dump(mode="json")), encoding="utf-8")
    out = tmp_path / "report.html"
    rc = main(["audit", "--old", str(old_p), "--new", str(new_p),
               "--evidence", str(ev), "--out", str(out)])
    assert rc == 0
    html = out.read_text(encoding="utf-8")
    assert "Revalidation Binder" in html
    assert "indel_recall" in html


def test_cli_report_json(tmp_path, capsys):
    old_p, new_p = _write_manifests(tmp_path)
    out = tmp_path / "binder.json"
    rc = main(["report", "--old", str(old_p), "--new", str(new_p), "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["assay_name"] == "SolidTumor500"
    assert len(payload["decisions"]) == 1