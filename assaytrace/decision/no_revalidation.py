"""Defensible No-Revalidation Record (Step 11).

Some changes, after rule-driven classification, require no revalidation (e.g., a
documentation-only change). This module produces explicit, structured,
auditable records of those determinations so that "we decided this needs
nothing" is itself a defensible, recorded decision — never silence.

It consumes the existing decision engine's output; it adds no new judgment
beyond an externalized set of revalidation outcomes that mean "no revalidation
required." No AI, no scoring.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ..impact.models import ImpactDomain
from .models import DecisionRecord, RevalidationType

# Externalized policy: which revalidation outcomes constitute "no revalidation
# required." Edit this set to change policy; the logic below does not change.
NO_REVALIDATION_TYPES: frozenset[RevalidationType] = frozenset(
    {
        RevalidationType.NONE,
        RevalidationType.DOCUMENTATION_UPDATE,
    }
)


class NoRevalidationRecord(BaseModel):
    """An explicit, auditable record that a change requires no revalidation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str
    decision_id: str
    decision_type: RevalidationType
    impact_domain: ImpactDomain
    rationale: str


class NoRevalidationDeterminer:
    """Extracts defensible no-revalidation records from decision records."""

    def determine(self, decisions: list[DecisionRecord]) -> list[NoRevalidationRecord]:
        records: list[NoRevalidationRecord] = []
        for d in decisions:
            if d.decision_type in NO_REVALIDATION_TYPES:
                records.append(
                    NoRevalidationRecord(
                        change_id=d.change_id,
                        decision_id=d.decision_id,
                        decision_type=d.decision_type,
                        impact_domain=d.impact_domain,
                        rationale=self._rationale(d),
                    )
                )
        return sorted(records, key=lambda r: r.decision_id)

    @staticmethod
    def _rationale(d: DecisionRecord) -> str:
        if d.decision_type is RevalidationType.DOCUMENTATION_UPDATE:
            return "No revalidation required: documentation-only change."
        return (
            "No revalidation required: change carries no revalidation-relevant "
            f"impact (impact domain '{d.impact_domain.value}')."
        )