"""Configurable revalidation policy (lab-defined SOP rules).

A ``RevalidationPolicy`` is an ordered set of rules a laboratory can supply
(typically from YAML) to override the built-in revalidation defaults. A rule
matches a detected change on any combination of component identity, category,
change type, and version magnitude; the engine selects the *most specific*
matching rule deterministically and records which rule fired. When no rule
matches, the engine falls back to the built-in tables — so a partial policy is
always safe.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict

from ..diff.models import ChangeRecord, ChangeType
from ..decision.models import RevalidationType
from ..models.enums import AssayType, ComponentCategory
from ..severity.models import VersionMagnitude


class PolicyMatch(BaseModel):
    """Selector for a policy rule. Unspecified fields are wildcards."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    component: str | None = None          # full identity or slug, e.g. 'variant_caller:mutect2' or 'mutect2'
    category: ComponentCategory | None = None
    change_type: ChangeType | None = None
    magnitude: VersionMagnitude | None = None  # None = any magnitude

    def matches(self, change: ChangeRecord, magnitude: VersionMagnitude) -> bool:
        if self.component is not None:
            ident = change.component_identity
            if ident != self.component and not ident.endswith(f":{self.component}"):
                return False
        if self.category is not None and change.category is not self.category:
            return False
        if self.change_type is not None and change.change_type is not self.change_type:
            return False
        if self.magnitude is not None and magnitude is not self.magnitude:
            return False
        # A rule with no selector at all is invalid (would match everything).
        return any(
            v is not None
            for v in (self.component, self.category, self.change_type, self.magnitude)
        )

    @property
    def specificity(self) -> int:
        return (
            (8 if self.component is not None else 0)
            + (4 if self.category is not None else 0)
            + (2 if self.change_type is not None else 0)
            + (1 if self.magnitude is not None else 0)
        )


class PolicyRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    match: PolicyMatch
    action: RevalidationType
    rationale: str | None = None


class RevalidationPolicy(BaseModel):
    """An ordered, named set of laboratory revalidation rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = "custom-policy"
    version: str = "v1"
    status: str = "active"        # active | draft | retired
    assay_type: AssayType | None = None
    rules: tuple[PolicyRule, ...] = ()

    def content_hash(self) -> str:
        """Deterministic SHA-256 over the policy's rule content.

        Stable across runs and independent of Python object identity, so the
        same SOP always hashes to the same value and can be cited in an audit.
        """
        payload = {
            "name": self.name,
            "version": self.version,
            "assay_type": self.assay_type.value if self.assay_type else None,
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "match": r.match.model_dump(mode="json"),
                    "action": r.action.value,
                    "rationale": r.rationale,
                }
                for r in self.rules
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def policy_id(self) -> str:
        """Human/audit identifier, e.g. 'somatic-sop-v1'."""
        return self.name if self.name.endswith(self.version) else f"{self.name}-{self.version}"

    def match(
        self, change: ChangeRecord, magnitude: VersionMagnitude
    ) -> PolicyRule | None:
        """Return the most specific matching rule, or None.

        Deterministic: highest specificity wins; ties are broken by declaration
        order (earliest rule wins).
        """
        best: PolicyRule | None = None
        best_key: tuple[int, int] | None = None
        for idx, rule in enumerate(self.rules):
            if rule.match.matches(change, magnitude):
                key = (rule.match.specificity, -idx)  # higher specificity, then earlier
                if best_key is None or key > best_key:
                    best, best_key = rule, key
        return best
