"""The Transparent Revalidation Decision Engine (Step 6).

Consumes change records, impact records, and claim-impact records and produces
one fully explainable ``DecisionRecord`` per change. Every decision names its
revalidation type, rationale, affected claims, and required evidence, and is
derived purely from the externalized rule tables — no black-box logic.
"""

from __future__ import annotations

from ..claims_impact.models import ClaimImpactRecord
from ..diff.models import ChangeRecord
from ..impact.models import ImpactDomain, ImpactRecord
from . import rules
from .models import DecisionRecord, RevalidationType


class RevalidationDecisionEngine:
    """Stateless, deterministic, rule-driven decision engine."""

    def decide(
        self,
        changes: list[ChangeRecord],
        impacts: list[ImpactRecord],
        claim_impacts: list[ClaimImpactRecord],
    ) -> list[DecisionRecord]:
        domain_by_change: dict[str, ImpactDomain] = {
            i.change_id: i.impact_domain for i in impacts
        }
        claims_by_change: dict[str, set[str]] = {}
        for ci in claim_impacts:
            claims_by_change.setdefault(ci.change_id, set()).add(ci.claim_id)

        decisions: list[DecisionRecord] = []
        for change in changes:
            decision_type, rationale = self._resolve(change)
            domain = domain_by_change.get(change.change_id, ImpactDomain.NONE)
            affected = tuple(sorted(claims_by_change.get(change.change_id, set())))
            evidence = rules.REQUIRED_EVIDENCE.get(decision_type, ())
            decisions.append(
                DecisionRecord(
                    decision_id=f"decision|{change.change_id}",
                    change_id=change.change_id,
                    decision_type=decision_type,
                    impact_domain=domain,
                    rationale=rationale,
                    affected_claims=affected,
                    required_evidence=evidence,
                )
            )
        return sorted(decisions, key=lambda d: d.decision_id)

    @staticmethod
    def _resolve(change: ChangeRecord) -> tuple[RevalidationType, str]:
        if change.category is not None:
            decision_type = rules.REVALIDATION_BY_CATEGORY.get(
                change.category, rules.DEFAULT_COMPONENT_REVALIDATION
            )
            rationale = rules.RATIONALE_BY_CATEGORY.get(
                change.category, change.description
            )
            if change.category not in rules.REVALIDATION_BY_CATEGORY:
                rationale = (
                    f"{change.description} Component category "
                    f"'{change.category.value}' has no explicit rule; default "
                    f"'{decision_type.value}' applied."
                )
        else:
            decision_type = rules.REVALIDATION_BY_CHANGE_TYPE.get(
                change.change_type, RevalidationType.NONE
            )
            rationale = rules.RATIONALE_BY_CHANGE_TYPE.get(
                change.change_type, change.description
            )
        return decision_type, rationale