"""The Assay-Claim Impact Map (Step 4).

``ClaimImpactMapper.map(manifest, changes, impacts)`` returns the set of
(change, claim) matches, deterministically, using ONLY the Step-1 claim
dependency wiring for component changes and the externalized domain-bridge
table for non-component changes. No scoring, no probability, no decisions.
"""

from __future__ import annotations

from ..claims_impact.models import ClaimImpactRecord
from ..diff.models import ChangeRecord, ChangeType
from ..impact.models import ImpactDomain, ImpactRecord
from ..models.claims import AssayClaim
from ..models.manifest import AssayManifest
from . import rules


class ClaimImpactMapper:
    """Stateless, deterministic mapper from changes to affected claims."""

    def map(
        self,
        manifest: AssayManifest,
        changes: list[ChangeRecord],
        impacts: list[ImpactRecord],
    ) -> list[ClaimImpactRecord]:
        domain_by_change: dict[str, ImpactDomain] = {
            i.change_id: i.impact_domain for i in impacts
        }

        records: list[ClaimImpactRecord] = []
        for change in changes:
            domain = domain_by_change.get(change.change_id, ImpactDomain.NONE)
            for claim in manifest.claims:
                match = self._match(change, claim, domain)
                if match is None:
                    continue
                records.append(
                    ClaimImpactRecord(
                        change_id=change.change_id,
                        claim_id=claim.claim_id,
                        claim_type=claim.claim_type,
                        claim_name=claim.title,
                        impact_domain=domain,
                        rationale=match,
                    )
                )

        # Deterministic order; dedupe defensively on (change_id, claim_id).
        seen: set[tuple[str, str]] = set()
        unique: list[ClaimImpactRecord] = []
        for r in sorted(records, key=lambda r: (r.change_id, r.claim_id)):
            key = (r.change_id, r.claim_id)
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    @staticmethod
    def _qc_metric(change: ChangeRecord) -> str:
        """Extract the QC parameter name (e.g. 'minimum_vaf') from a QC change."""
        for value in (change.new_value, change.old_value):
            if isinstance(value, dict) and value.get("metric"):
                return str(value["metric"])
        ident = change.component_identity or ""
        if ":" in ident:
            return ident.split(":", 1)[1].split("[", 1)[0]
        return ""

    @staticmethod
    def _match(
        change: ChangeRecord, claim: AssayClaim, domain: ImpactDomain
    ) -> str | None:
        """Return a rationale string if the change affects the claim, else None."""
        if change.category is not None:
            # Component change: authoritative match via Step-1 dependency wiring.
            if change.component_identity in claim.depends_on_components:
                return (
                    f"matched via depends_on_components "
                    f"('{change.component_identity}')"
                )
            if change.category in claim.depends_on_categories:
                return (
                    f"matched via depends_on_categories "
                    f"('{change.category.value}')"
                )
            return None

        # QC threshold change: deterministic QC-parameter -> performance
        # characteristic -> claim-type mapping (Critical Issue #1). A change to a
        # known QC parameter perturbs the analytical claims tied to the
        # performance characteristic it governs.
        if change.change_type in {
            ChangeType.QC_THRESHOLD_CHANGED,
            ChangeType.QC_THRESHOLD_ADDED,
            ChangeType.QC_THRESHOLD_REMOVED,
        }:
            metric = ClaimImpactMapper._qc_metric(change)
            if claim.claim_type in rules.qc_claim_types_for_parameter(metric):
                characteristic = rules.qc_characteristic_for_parameter(metric)
                return (
                    f"matched via QC-parameter rule "
                    f"('{metric}' -> {characteristic} -> claim_type "
                    f"'{claim.claim_type.value}')"
                )
            # Fall through to the domain bridge for QC_DECISION_STABILITY claims.

        # Non-component change: externalized domain -> claim_type bridge.
        if claim.claim_type in rules.claim_types_for_domain(domain):
            return (
                f"matched via impact-domain rule "
                f"({domain.value} -> claim_type '{claim.claim_type.value}')"
            )
        return None
