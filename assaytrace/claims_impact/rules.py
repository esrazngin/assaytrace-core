"""Externalized rules for claim-impact matching.

Component changes are matched to claims purely through the Step-1 dependency
wiring (``depends_on_components`` / ``depends_on_categories``) — that is the
authoritative mechanism and lives in the mapper.

Non-component changes (QC thresholds, etc.) carry no component identity or
category, so they cannot be matched through the wiring. For those, this table
provides a transparent, deterministic bridge from the change's impact domain to
the claim types it can affect. The table is data, not logic: edit it to change
policy. It is intentionally minimal and conservative — only mappings that are
clearly defensible are included, to avoid false "claim affected" flags.
"""

from __future__ import annotations

from ..impact.models import ImpactDomain
from ..models.enums import ClaimType

# Domain -> claim types it can affect, used ONLY for non-component changes.
DOMAIN_CLAIM_TYPES: dict[ImpactDomain, frozenset[ClaimType]] = {
    ImpactDomain.QUALITY: frozenset({ClaimType.QC_DECISION_STABILITY}),
    # ANALYTICAL / INTERPRETIVE non-component changes (e.g., panel edits) are
    # intentionally NOT bridged here: region-coverage impact is not expressible
    # via the Step-1 dependency wiring, so inferring it would be speculation.
    # INFRASTRUCTURE / DOCUMENTATION / NONE map to no claim types by design.
}


def claim_types_for_domain(domain: ImpactDomain) -> frozenset[ClaimType]:
    return DOMAIN_CLAIM_TYPES.get(domain, frozenset())