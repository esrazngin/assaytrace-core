from __future__ import annotations

import copy
import io
import json
from pathlib import Path

import pytest

flask = pytest.importorskip("flask")

from assaytrace.web.app import app  # noqa: E402
from examples.build import build  # noqa: E402

FIX = Path(__file__).resolve().parent.parent / "examples" / "fixtures"


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def _manifests():
    old = build()
    old_b = json.dumps(old.model_dump(mode="json")).encode()
    d = old.model_dump(mode="json")
    d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"
    return old_b, json.dumps(d).encode()


def test_index_branding(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"AssayTrace" in resp.data
    assert b"esra.zengiinn@gmail.com" in resp.data
    assert b"www.assaytrace.com" in resp.data
    assert b"Try Demo" in resp.data


def test_analyze_returns_decision_and_binder(client):
    old_b, new_b = _manifests()
    data = {
        "old_manifest": (io.BytesIO(old_b), "old.json"),
        "new_manifest": (io.BytesIO(new_b), "new.json"),
        "baseline_benchmark": (io.BytesIO((FIX / "benchmark_baseline.json").read_bytes()), "b.json"),
        "current_benchmark": (io.BytesIO((FIX / "benchmark_current.json").read_bytes()), "c.json"),
        "old_variants": (io.BytesIO((FIX / "variants_old.json").read_bytes()), "vo.json"),
        "new_variants": (io.BytesIO((FIX / "variants_new.json").read_bytes()), "vn.json"),
    }
    resp = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["decision"] == "REVALIDATION_REQUIRED"
    assert body["summary"]["regressions"] >= 1
    assert body["summary"]["variant_changes"] >= 1
    assert "binder" in body


def test_analyze_requires_manifests(client):
    resp = client.post("/api/analyze", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_demo_runs_real_engine(client):
    resp = client.post("/demo")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["decision"] == "REVALIDATION_REQUIRED"
    assert body["summary"]["changes"] >= 1
    assert body["summary"]["decisions"] >= 1
    assert body["summary"]["regressions"] >= 1
    assert body["summary"]["variant_changes"] >= 1
    binder = body["binder"]
    assert binder["changes"]
    assert binder["impacts"]
    assert binder["decisions"]
    assert binder["regression"]
    assert binder["variant_classification_deltas"]


def test_export_pdf_roundtrip(client):
    old_b, new_b = _manifests()
    data = {
        "old_manifest": (io.BytesIO(old_b), "old.json"),
        "new_manifest": (io.BytesIO(new_b), "new.json"),
    }
    analyze = client.post("/api/analyze", data=data, content_type="multipart/form-data").get_json()
    resp = client.post("/api/export-pdf", json=analyze["binder"])
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data[:5] == b"%PDF-"
