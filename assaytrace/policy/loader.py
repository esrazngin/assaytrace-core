"""Loading and validation for revalidation policies.

Supports an ergonomic YAML form (component/category groups with per-magnitude
actions) and normalizes it into the canonical ``RevalidationPolicy`` model.
Action names accept both the canonical ``RevalidationType`` values and a few
friendly aliases (e.g. ``full_revalidation``). Loading is strict: an unknown
action or malformed rule raises, because a regulated tool should fail loudly
rather than silently mis-apply policy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..decision.models import RevalidationType
from ..models.enums import AssayType, ComponentCategory
from ..severity.models import VersionMagnitude
from .models import PolicyMatch, PolicyRule, RevalidationPolicy

# Friendly aliases -> canonical RevalidationType.
ACTION_ALIASES: dict[str, RevalidationType] = {
    "full_revalidation": RevalidationType.FULL_ANALYTICAL,
    "full_analytical": RevalidationType.FULL_ANALYTICAL,
    "targeted_revalidation": RevalidationType.TARGETED_ANALYTICAL,
    "targeted_analytical": RevalidationType.TARGETED_ANALYTICAL,
    "documentation_review": RevalidationType.DOCUMENTATION_UPDATE,
    "documentation": RevalidationType.DOCUMENTATION_UPDATE,
    "qc_verification": RevalidationType.QC_VERIFICATION,
    "infrastructure_verification": RevalidationType.INFRASTRUCTURE_VERIFICATION,
    "classification_review": RevalidationType.CLASSIFICATION_CONCORDANCE_REVIEW,
    "none": RevalidationType.NONE,
    "no_revalidation": RevalidationType.NONE,
}

_MAGNITUDE_KEYS: dict[str, VersionMagnitude | None] = {
    "major_version": VersionMagnitude.MAJOR,
    "major": VersionMagnitude.MAJOR,
    "minor_version": VersionMagnitude.MINOR,
    "minor": VersionMagnitude.MINOR,
    "patch_version": VersionMagnitude.PATCH,
    "patch": VersionMagnitude.PATCH,
    "any": None,
    "any_version": None,
}


def _resolve_action(value: str) -> RevalidationType:
    raw = str(value).strip().lower()
    try:
        return RevalidationType(raw)
    except ValueError:
        if raw in ACTION_ALIASES:
            return ACTION_ALIASES[raw]
        valid = sorted({a for a in ACTION_ALIASES} | {t.value for t in RevalidationType})
        raise ValueError(f"Unknown policy action '{value}'. Allowed: {valid}")


def _target_to_match(target: str) -> dict[str, Any]:
    """Interpret a friendly target key into PolicyMatch fields."""
    # Friendly aliases for common laboratory-facing concepts (Critical Issue #4):
    # let a policy say 'reference_genome_update' rather than the internal
    # 'category:reference_genome'.
    aliases = {
        "reference_genome": {"category": ComponentCategory.REFERENCE_GENOME},
        "reference_genome_update": {"category": ComponentCategory.REFERENCE_GENOME},
        "annotation_update": {"category": ComponentCategory.ANNOTATION},
        "qc_threshold": {"change_type": _qc_change_type()},
    }
    if target in aliases:
        return dict(aliases[target])
    if target.startswith("category:"):
        return {"category": ComponentCategory(target.split(":", 1)[1])}
    if target.startswith("change_type:"):
        from ..diff.models import ChangeType
        return {"change_type": ChangeType(target.split(":", 1)[1])}
    # Otherwise treat as a component identity or slug.
    return {"component": target}


def _qc_change_type():
    from ..diff.models import ChangeType
    return ChangeType.QC_THRESHOLD_CHANGED


def _derive_version(data: dict[str, Any], name: str) -> str:
    if data.get("version"):
        return str(data["version"])
    # Derive from a trailing '-vN' in the name, else default.
    tail = name.rsplit("-", 1)[-1]
    if tail.startswith("v") and tail[1:].isdigit():
        return tail
    return "v1"


def parse_policy(data: dict[str, Any]) -> RevalidationPolicy:
    """Build and validate a policy from a plain dict (YAML or JSON shape)."""
    name = data.get("name", "custom-policy")
    assay_type = AssayType(data["assay_type"]) if data.get("assay_type") else None
    version = _derive_version(data, name)
    status = str(data.get("status", "active"))

    # Explicit rules list form.
    if "rules" in data and isinstance(data["rules"], list):
        rules = tuple(PolicyRule.model_validate(r) for r in data["rules"])
        return RevalidationPolicy(
            name=name, version=version, status=status,
            assay_type=assay_type, rules=rules,
        )

    # Ergonomic grouped form: {target: {magnitude_key: {action, rationale}}}
    rules_out: list[PolicyRule] = []
    reserved = {"name", "assay_type", "version", "status"}
    for target, spec in data.items():
        if target in reserved:
            continue
        if not isinstance(spec, dict):
            raise ValueError(f"Policy target '{target}' must map to a dict of rules.")
        base_match = _target_to_match(target)
        for mag_key, body in spec.items():
            if mag_key not in _MAGNITUDE_KEYS:
                raise ValueError(
                    f"Unknown magnitude key '{mag_key}' under '{target}'. "
                    f"Allowed: {sorted(_MAGNITUDE_KEYS)}"
                )
            if not isinstance(body, dict) or "action" not in body:
                raise ValueError(f"Rule '{target}.{mag_key}' must define an 'action'.")
            match = PolicyMatch(magnitude=_MAGNITUDE_KEYS[mag_key], **base_match)
            rules_out.append(
                PolicyRule(
                    rule_id=f"{target}:{mag_key}",
                    match=match,
                    action=_resolve_action(body["action"]),
                    rationale=body.get("rationale"),
                )
            )
    return RevalidationPolicy(
        name=name, version=version, status=status,
        assay_type=assay_type, rules=tuple(rules_out),
    )


def load_policy(source: str | Path) -> RevalidationPolicy:
    """Load a policy from a YAML or JSON file."""
    path = Path(source)
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("Policy file must contain a mapping at the top level.")
    return parse_policy(data)


def default_policy() -> RevalidationPolicy:
    """An empty policy. The engine falls back to its built-in tables for every
    change, reproducing default behavior exactly."""
    return RevalidationPolicy(name="builtin-defaults", rules=())
