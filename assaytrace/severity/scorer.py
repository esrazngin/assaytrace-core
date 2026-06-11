"""The Severity Scoring Engine.

Turns each descriptive ``ChangeRecord`` into an explainable ``ChangeSeverity``.
Deterministic and rule-table driven: magnitude is computed from version strings,
the base severity comes from the rule tables, category floors and replacement
escalation are applied as bounded, disclosed adjustments, and QC relaxations are
measured numerically.

Every assessment carries both a one-line ``rationale`` and a list of discrete
``reasons`` (the individual factors that produced the score), so the UI and PDF
can show *why* a severity was assigned without any free text or AI.
"""

from __future__ import annotations

from ..diff.models import ChangeRecord, ChangeType
from . import rules
from .models import ChangeSeverity, Severity, VersionMagnitude, max_severity
from .versioning import version_magnitude


def _category_phrase(change: ChangeRecord) -> str:
    if change.category is None:
        return "Non-component change"
    return change.category.value.replace("_", " ").title()


class SeverityScorer:
    """Stateless, deterministic severity assignment over change records."""

    def score(self, changes: list[ChangeRecord]) -> list[ChangeSeverity]:
        return sorted(
            (self._score_one(c) for c in changes), key=lambda s: s.change_id
        )

    def _score_one(self, change: ChangeRecord) -> ChangeSeverity:
        if change.change_type is ChangeType.COMPONENT_VERSION_CHANGED:
            return self._version_change(change)
        if change.change_type is ChangeType.QC_THRESHOLD_CHANGED:
            return self._qc_change(change)
        return self._generic_change(change)

    def _finalize(self, change, severity, magnitude, reasons):
        return ChangeSeverity(
            change_id=change.change_id,
            severity=severity,
            version_magnitude=magnitude,
            rationale=" ".join(reasons),
            reasons=tuple(reasons),
        )

    # -- version changes (the headline case) ------------------------------- #
    def _version_change(self, change: ChangeRecord) -> ChangeSeverity:
        magnitude = version_magnitude(change.old_value, change.new_value)
        severity = rules.SEVERITY_BY_MAGNITUDE[magnitude]
        reasons = [
            f"{rules.MAGNITUDE_PHRASE[magnitude]} ({change.old_value} -> {change.new_value}).",
            f"{_category_phrase(change)} category affected.",
        ]
        floor = self._floor(change)
        if floor and floor.rank > severity.rank:
            severity = floor
            reasons.append(
                f"Severity raised to {severity.value.upper()} because "
                f"'{change.category.value}' is a foundational component."
            )
        if (
            change.category in rules.CRITICAL_ON_REPLACEMENT
            and magnitude is VersionMagnitude.MAJOR
        ):
            severity = Severity.CRITICAL
            reasons.append("Major change to the reference genome is treated as CRITICAL.")
        return self._finalize(change, severity, magnitude, reasons)

    # -- QC threshold changes (measure relaxation) ------------------------- #
    def _qc_change(self, change: ChangeRecord) -> ChangeSeverity:
        severity = rules.SEVERITY_BY_CHANGE_TYPE[ChangeType.QC_THRESHOLD_CHANGED]
        old, new = change.old_value, change.new_value
        reasons = ["QC threshold changed."]
        if isinstance(old, dict) and isinstance(new, dict):
            relaxed, rel = self._relaxation(old, new)
            if old.get("severity") != new.get("severity"):
                severity = Severity.HIGH
                reasons = [
                    f"QC threshold severity changed "
                    f"({old.get('severity')} -> {new.get('severity')})."
                ]
            elif relaxed and rel >= rules.QC_SUBSTANTIAL_RELAXATION:
                severity = Severity.HIGH
                reasons = [
                    f"QC threshold substantially relaxed "
                    f"({old.get('threshold')} -> {new.get('threshold')}, "
                    f"{rel * 100:.0f}% looser), increasing acceptance risk."
                ]
            elif relaxed:
                severity = Severity.MEDIUM
                reasons = [
                    f"QC threshold relaxed "
                    f"({old.get('threshold')} -> {new.get('threshold')})."
                ]
            else:
                severity = Severity.LOW
                reasons = [
                    f"QC threshold tightened "
                    f"({old.get('threshold')} -> {new.get('threshold')}); "
                    f"acceptance risk not increased."
                ]
        return self._finalize(change, severity, VersionMagnitude.NONE, reasons)

    @staticmethod
    def _relaxation(old: dict, new: dict) -> tuple[bool, float]:
        try:
            o = float(old["threshold"])
            n = float(new["threshold"])
        except (KeyError, TypeError, ValueError):
            return (False, 0.0)
        comparator = str(old.get("comparator", ""))
        rel = abs(n - o) / abs(o) if o else 0.0
        if comparator in {">=", ">"}:
            return (n < o, rel)
        if comparator in {"<=", "<"}:
            return (n > o, rel)
        return (n != o, rel)

    # -- everything else --------------------------------------------------- #
    def _generic_change(self, change: ChangeRecord) -> ChangeSeverity:
        severity = rules.SEVERITY_BY_CHANGE_TYPE.get(change.change_type, Severity.MEDIUM)
        verb = change.change_type.value.replace("_", " ")
        reasons = [f"{_category_phrase(change)}: {verb}."]
        floor = self._floor(change)
        if floor and floor.rank > severity.rank:
            severity = max_severity(severity, floor)
            reasons.append(
                f"Severity raised to {severity.value.upper()} due to component "
                f"category '{change.category.value}'."
            )
        if change.category in rules.CRITICAL_ON_REPLACEMENT and change.change_type in {
            ChangeType.COMPONENT_ADDED,
            ChangeType.COMPONENT_REMOVED,
        }:
            severity = Severity.CRITICAL
            reasons.append("Reference genome added/removed is treated as CRITICAL.")
        return self._finalize(change, severity, VersionMagnitude.NONE, reasons)

    @staticmethod
    def _floor(change: ChangeRecord) -> Severity | None:
        if change.category is None:
            return None
        return rules.CATEGORY_SEVERITY_FLOOR.get(change.category)
