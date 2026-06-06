"""The Change Impact Graph (Step 3).

``ChangeImpactGraph.evaluate(changes)`` classifies each ``ChangeRecord`` into
one ``ImpactDomain`` using the externalized rule tables. It performs no risk
assessment and makes no revalidation decision — it only states which technical
domain a change touches, with a traceable rationale.

Classification is a two-line decision:
  * component change (has a category)  -> CATEGORY_IMPACT table
  * everything else                    -> CHANGE_TYPE_IMPACT table
"""

from __future__ import annotations

from ..diff.models import ChangeRecord
from . import rules
from .models import ImpactDomain, ImpactRecord


class ChangeImpactGraph:
    """Stateless, deterministic impact classifier."""

    def evaluate(self, changes: list[ChangeRecord]) -> list[ImpactRecord]:
        records = [self._classify(change) for change in changes]
        return sorted(records, key=lambda r: r.change_id)

    @staticmethod
    def _classify(change: ChangeRecord) -> ImpactRecord:
        if change.category is not None:
            domain = rules.CATEGORY_IMPACT.get(change.category)
            if domain is None:
                domain = rules.DEFAULT_COMPONENT_DOMAIN
                rationale = (
                    f"Component category '{change.category.value}' has no explicit "
                    f"rule; default '{domain.value}' applied (CATEGORY_IMPACT default)."
                )
            else:
                rationale = (
                    f"Component category '{change.category.value}' maps to "
                    f"'{domain.value}' (CATEGORY_IMPACT rule)."
                )
        else:
            domain = rules.CHANGE_TYPE_IMPACT.get(change.change_type, ImpactDomain.NONE)
            if domain is ImpactDomain.NONE:
                rationale = (
                    f"Change type '{change.change_type.value}' has no impact rule; "
                    f"classified as 'none'."
                )
            else:
                rationale = (
                    f"Change type '{change.change_type.value}' maps to "
                    f"'{domain.value}' (CHANGE_TYPE_IMPACT rule)."
                )
        return ImpactRecord(
            change_id=change.change_id,
            impact_domain=domain,
            rationale=rationale,
        )