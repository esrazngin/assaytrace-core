from __future__ import annotations

import json
from pathlib import Path

from assaytrace.reportable import (
    ReportableDeltaType,
    ReportableVariant,
    ReportableVariantDiffer,
    VariantClassification,
    parse_reportable_variants,
)

FIX = Path(__file__).resolve().parent.parent / "examples" / "fixtures"


def _fix(name):
    return parse_reportable_variants(json.loads((FIX / name).read_text()))


def test_detects_added_removed_reclassified():
    old = _fix("variants_old.json")
    new = _fix("variants_new.json")
    deltas = {(d.gene, d.change_type): d for d in ReportableVariantDiffer().diff(old, new)}

    # BRCA1 VUS -> Pathogenic
    rc = deltas[("BRCA1", ReportableDeltaType.CLASSIFICATION_CHANGED)]
    assert rc.old_classification is VariantClassification.VUS
    assert rc.new_classification is VariantClassification.PATHOGENIC
    assert rc.explanation == "Variant classification changed from VUS to Pathogenic."

    # TP53 removed, EGFR added
    assert ("TP53", ReportableDeltaType.REMOVED) in deltas
    assert ("EGFR", ReportableDeltaType.ADDED) in deltas
    # KRAS unchanged -> not emitted by default
    assert all(g != "KRAS" for (g, _t) in deltas)


def test_added_removed_explanations():
    differ = ReportableVariantDiffer()
    added = differ.diff([], [ReportableVariant(gene="EGFR", variant="c.2369C>T",
                                               classification=VariantClassification.LIKELY_PATHOGENIC)])
    assert added[0].change_type is ReportableDeltaType.ADDED
    assert "introduced" in added[0].explanation
    removed = differ.diff([ReportableVariant(gene="TP53", variant="c.524G>A",
                                             classification=VariantClassification.PATHOGENIC)], [])
    assert removed[0].change_type is ReportableDeltaType.REMOVED
    assert "no longer reported" in removed[0].explanation


def test_include_unchanged_option_and_determinism():
    old = _fix("variants_old.json")
    new = _fix("variants_new.json")
    deltas = ReportableVariantDiffer().diff(old, new, include_unchanged=True)
    assert any(d.change_type is ReportableDeltaType.UNCHANGED and d.gene == "KRAS" for d in deltas)
    keys = [(d.gene, d.variant) for d in deltas]
    assert keys == sorted(keys)
