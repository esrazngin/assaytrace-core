"""The Transparent Revalidation Decision Engine (Step 6 + Intelligence sprint).

Consumes change records, impact records, and claim-impact records and produces
one fully explainable ``DecisionRecord`` per change. Every decision names its
revalidation type, rationale, affected claims, required evidence, the severity
and version magnitude of the change, and — crucially for auditability — the
identifier of the rule that produced it.

A laboratory ``RevalidationPolicy`` (optional) is consulted first; the most
specific matching rule wins. When no policy is supplied, or no rule matches a
given change, the engine falls back to the built-in externalized tables,
reproducing the original default behavior exactly. There is no black-box logic.
"""

from __future__ import annotations

from ..claims_impact.models import ClaimImpactRecord
from ..diff.models import ChangeRecord
from ..impact.models import ImpactDomain, ImpactRecord
from ..severity.models import ChangeSeverity, Severity, VersionMagnitude
from . import rules
from .models import DecisionRecord, RevalidationType


class RevalidationDecisionEngine:
    """Stateless, deterministic, rule-driven decision engine."""

    def decide(
        self,
        changes: list[ChangeRecord],
        impacts: list[ImpactRecord],
        claim_impacts: list[ClaimImpactRecord],
        *,
        policy=None,
        severities: list[ChangeSeverity] | None = None,
    ) -> list[DecisionRecord]:
        domain_by_change: dict[str, ImpactDomain] = {
            i.change_id: i.impact_domain for i in impacts
        }
        claims_by_change: dict[str, set[str]] = {}
        for ci in claim_impacts:
            claims_by_change.setdefault(ci.change_id, set()).add(ci.claim_id)
        severity_by_change: dict[str, ChangeSeverity] = {
            s.change_id: s for s in (severities or [])
        }

        decisions: list[DecisionRecord] = []
        for change in changes:
            sev = severity_by_change.get(change.change_id)
            magnitude = sev.version_magnitude if sev else VersionMagnitude.NONE

            decision_type, rationale, triggered = self._resolve(
                change, magnitude, policy
            )
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
                    severity=sev.severity if sev else None,
                    version_magnitude=magnitude if sev else None,
                    triggered_by_rule=triggered,
                )
            )
        return sorted(decisions, key=lambda d: d.decision_id)

    # ------------------------------------------------------------------ #
    def _resolve(
        self, change: ChangeRecord, magnitude: VersionMagnitude, policy
    ) -> tuple[RevalidationType, str, str]:
        # 1) Laboratory policy takes precedence when it matches.
        if policy is not None:
            rule = policy.match(change, magnitude)
            if rule is not None:
                rationale = rule.rationale or (
                    f"{change.description} Laboratory policy '{policy.name}' "
                    f"rule '{rule.rule_id}' applies "
                    f"({rule.action.value})."
                )
                return rule.action, rationale, f"policy:{rule.rule_id}"

        # 2) Built-in fallback (unchanged default behavior).
        if change.category is not None:
            decision_type = rules.REVALIDATION_BY_CATEGORY.get(
                change.category, rules.DEFAULT_COMPONENT_REVALIDATION
            )
            rationale = rules.RATIONALE_BY_CATEGORY.get(change.category, change.description)
            if change.category not in rules.REVALIDATION_BY_CATEGORY:
                rationale = (
                    f"{change.description} Component category "
                    f"'{change.category.value}' has no explicit rule; default "
                    f"'{decision_type.value}' applied."
                )
            triggered = f"builtin:category:{change.category.value}"
        else:
            decision_type = rules.REVALIDATION_BY_CHANGE_TYPE.get(
                change.change_type, RevalidationType.NONE
            )
            rationale = rules.RATIONALE_BY_CHANGE_TYPE.get(
                change.change_type, change.description
            )
            triggered = f"builtin:change_type:{change.change_type.value}"
        return decision_type, rationale, triggered
