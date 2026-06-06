from __future__ import annotations

from assaytrace.reportable import (
    DeltaType,
    ReportableVariantDeltaViewer,
    ReportableVariantObservation,
    VariantStatus,
)


def _obs(variant, status=VariantStatus.DETECTED):
    return ReportableVariantObservation(variant=variant, status=status)


def test_lost_variant():
    old = [_obs("BRCA1 c.68_69delAG")]
    new = []  # absent in new -> MISSING
    [delta] = ReportableVariantDeltaViewer().compare(old, new)
    assert delta.variant == "BRCA1 c.68_69delAG"
    assert delta.old_status is VariantStatus.DETECTED
    assert delta.new_status is VariantStatus.MISSING
    assert delta.delta_type is DeltaType.LOST


def test_gained_variant():
    old = []
    new = [_obs("TP53 c.524G>A")]
    [delta] = ReportableVariantDeltaViewer().compare(old, new)
    assert delta.delta_type is DeltaType.GAINED


def test_unchanged_variant():
    v = [_obs("KRAS c.35G>A")]
    [delta] = ReportableVariantDeltaViewer().compare(v, v)
    assert delta.delta_type is DeltaType.UNCHANGED


def test_explicit_missing_status_status_changed():
    old = [_obs("EGFR c.2369C>T", VariantStatus.MISSING)]
    new = [_obs("EGFR c.2369C>T", VariantStatus.DETECTED)]
    [delta] = ReportableVariantDeltaViewer().compare(old, new)
    assert delta.delta_type is DeltaType.GAINED


def test_deterministic_sorted_output():
    old = [_obs("B"), _obs("A")]
    new = [_obs("A"), _obs("B")]
    deltas = ReportableVariantDeltaViewer().compare(old, new)
    assert [d.variant for d in deltas] == ["A", "B"]