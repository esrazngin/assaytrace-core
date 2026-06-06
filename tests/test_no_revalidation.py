from __future__ import annotations

import copy

import pytest

from assaytrace import AssayManifest
from assaytrace.claims_impact import ClaimImpactMapper
from assaytrace.decision import RevalidationDecisionEngine, RevalidationType
from assaytrace.decision.no_revalidation import NoRevalidationDeterminer
from assaytrace.diff import ChangeDetector
from assaytrace.impact import ChangeImpactGraph


def _decisions(old, new):
    changes = ChangeDetector().compare(old, new)
    impacts = ChangeImpactGraph().evaluate(changes)
    claim_impacts = ClaimImpactMapper().map(manifest=new, changes=changes, impacts=impacts)
    return RevalidationDecisionEngine().decide(changes, impacts, claim_impacts)


def test_documentation_change_yields_no_revalidation_record(valid_dict):
    old = AssayManifest.model_validate(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["claims"][0]["description"] = "Clarified wording only."
    new = AssayManifest.model_validate(new_d)

    decisions = _decisions(old, new)
    records = NoRevalidationDeterminer().determine(decisions)
    assert len(records) == 1
    r = records[0]
    assert r.decision_type is RevalidationType.DOCUMENTATION_UPDATE
    assert "documentation-only change" in r.rationale
    assert r.change_id and r.decision_id


def test_analytical_change_yields_no_no_revalidation_record(valid_dict):
    old = AssayManifest.model_validate(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["analysis_components"]["variant_caller"]["version"] = "4.6.0.0"
    new = AssayManifest.model_validate(new_d)

    decisions = _decisions(old, new)
    records = NoRevalidationDeterminer().determine(decisions)
    assert records == []  # analytical revalidation is required, so no NR record


def test_records_are_frozen_and_sorted(valid_dict):
    old = AssayManifest.model_validate(valid_dict)
    new_d = copy.deepcopy(valid_dict)
    new_d["claims"][0]["description"] = "x"
    new_d["claims"][1]["description"] = "y"
    new = AssayManifest.model_validate(new_d)
    records = NoRevalidationDeterminer().determine(_decisions(old, new))
    assert [r.decision_id for r in records] == sorted(r.decision_id for r in records)
    with pytest.raises(Exception):
        records[0].rationale = "tampered"