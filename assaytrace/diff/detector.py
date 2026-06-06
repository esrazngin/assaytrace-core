"""The Change Detection Engine (Step 2).

``ChangeDetector.compare(old, new)`` returns a deterministic, sorted list of
``ChangeRecord``s describing exactly what differs. It is intentionally and
strictly *descriptive*: no risk, no impact, no recommendation. Determinism is
guaranteed — records are sorted by ``change_id`` and ids are derived purely
from content.
"""

from __future__ import annotations

from typing import Any

from ..models.manifest import AssayManifest
from . import rules
from .models import ChangeRecord, ChangeType


def _added_removed_changed(
    old: dict[str, Any], new: dict[str, Any]
) -> tuple[set[str], set[str], set[str]]:
    old_keys, new_keys = set(old), set(new)
    added = new_keys - old_keys
    removed = old_keys - new_keys
    changed = {k for k in old_keys & new_keys if old[k] != new[k]}
    return added, removed, changed


class ChangeDetector:
    """Stateless, deterministic differ between two validated manifests."""

    def compare(
        self, old_manifest: AssayManifest, new_manifest: AssayManifest
    ) -> list[ChangeRecord]:
        records: list[ChangeRecord] = []
        records += self._diff_components(old_manifest, new_manifest)
        records += self._diff_qc(old_manifest, new_manifest)
        records += self._diff_scope(old_manifest, new_manifest)
        records += self._diff_pipeline(old_manifest, new_manifest)
        records += self._diff_environment(old_manifest, new_manifest)
        records += self._diff_claims(old_manifest, new_manifest)
        # Deterministic ordering for reproducible audit output.
        return sorted(records, key=lambda r: r.change_id)

    # ------------------------------------------------------------------ #
    # Components (software, resources, reference genome — uniform path)  #
    # ------------------------------------------------------------------ #
    def _diff_components(
        self, old: AssayManifest, new: AssayManifest
    ) -> list[ChangeRecord]:
        old_map = rules.component_map(old)
        new_map = rules.component_map(new)
        records: list[ChangeRecord] = []

        for identity in new_map.keys() - old_map.keys():
            comp = new_map[identity]
            records.append(
                ChangeRecord(
                    change_id=ChangeRecord.make_id(ChangeType.COMPONENT_ADDED, identity),
                    change_type=ChangeType.COMPONENT_ADDED,
                    category=comp.category,
                    component_identity=identity,
                    old_value=None,
                    new_value=comp.version,
                    description=f"Component '{identity}' added at version {comp.version}.",
                )
            )

        for identity in old_map.keys() - new_map.keys():
            comp = old_map[identity]
            records.append(
                ChangeRecord(
                    change_id=ChangeRecord.make_id(ChangeType.COMPONENT_REMOVED, identity),
                    change_type=ChangeType.COMPONENT_REMOVED,
                    category=comp.category,
                    component_identity=identity,
                    old_value=comp.version,
                    new_value=None,
                    description=f"Component '{identity}' (version {comp.version}) removed.",
                )
            )

        for identity in old_map.keys() & new_map.keys():
            old_c, new_c = old_map[identity], new_map[identity]
            if old_c.version != new_c.version:
                records.append(
                    ChangeRecord(
                        change_id=ChangeRecord.make_id(
                            ChangeType.COMPONENT_VERSION_CHANGED, identity
                        ),
                        change_type=ChangeType.COMPONENT_VERSION_CHANGED,
                        category=new_c.category,
                        component_identity=identity,
                        old_value=old_c.version,
                        new_value=new_c.version,
                        description=(
                            f"Component '{identity}' version changed "
                            f"{old_c.version} -> {new_c.version}."
                        ),
                    )
                )
            old_params = rules.component_parameters(old_c)
            new_params = rules.component_parameters(new_c)
            if old_params != new_params:
                records.append(
                    ChangeRecord(
                        change_id=ChangeRecord.make_id(
                            ChangeType.COMPONENT_PARAMETERS_CHANGED, identity
                        ),
                        change_type=ChangeType.COMPONENT_PARAMETERS_CHANGED,
                        category=new_c.category,
                        component_identity=identity,
                        old_value=old_params,
                        new_value=new_params,
                        description=f"Component '{identity}' parameters changed.",
                    )
                )
        return records

    # ------------------------------------------------------------------ #
    # Keyed-map sections (QC, scope, pipeline, environment)              #
    # ------------------------------------------------------------------ #
    def _diff_qc(self, old: AssayManifest, new: AssayManifest) -> list[ChangeRecord]:
        old_map, new_map = rules.qc_threshold_map(old), rules.qc_threshold_map(new)
        added, removed, changed = _added_removed_changed(old_map, new_map)
        records: list[ChangeRecord] = []
        for key in added:
            records.append(self._qc_record(ChangeType.QC_THRESHOLD_ADDED, key, None, new_map[key]))
        for key in removed:
            records.append(self._qc_record(ChangeType.QC_THRESHOLD_REMOVED, key, old_map[key], None))
        for key in changed:
            records.append(self._qc_record(ChangeType.QC_THRESHOLD_CHANGED, key, old_map[key], new_map[key]))
        return records

    @staticmethod
    def _qc_record(ct: ChangeType, key: str, old: Any, new: Any) -> ChangeRecord:
        metric = key.split(":", 1)[1]
        verb = {
            ChangeType.QC_THRESHOLD_ADDED: "added",
            ChangeType.QC_THRESHOLD_REMOVED: "removed",
            ChangeType.QC_THRESHOLD_CHANGED: "changed",
        }[ct]
        return ChangeRecord(
            change_id=ChangeRecord.make_id(ct, key),
            change_type=ct,
            category=None,
            component_identity=key,
            old_value=old,
            new_value=new,
            description=f"QC threshold '{metric}' {verb}.",
        )

    def _diff_simple_map(
        self,
        old_map: dict[str, Any],
        new_map: dict[str, Any],
        change_type: ChangeType,
        label: str,
    ) -> list[ChangeRecord]:
        """Generic per-aspect diff for scope/pipeline/environment maps. Both
        maps share keys (fixed aspect set), so only value changes occur."""
        records: list[ChangeRecord] = []
        for key in sorted(old_map.keys() | new_map.keys()):
            o, n = old_map.get(key), new_map.get(key)
            if o != n:
                aspect = key.split(":", 1)[1]
                records.append(
                    ChangeRecord(
                        change_id=ChangeRecord.make_id(change_type, key),
                        change_type=change_type,
                        category=None,
                        component_identity=key,
                        old_value=o,
                        new_value=n,
                        description=f"{label} '{aspect}' changed {o!r} -> {n!r}.",
                    )
                )
        return records

    def _diff_scope(self, old: AssayManifest, new: AssayManifest) -> list[ChangeRecord]:
        return self._diff_simple_map(
            rules.scope_aspect_map(old), rules.scope_aspect_map(new),
            ChangeType.PANEL_CHANGED, "Assay scope",
        )

    def _diff_pipeline(self, old: AssayManifest, new: AssayManifest) -> list[ChangeRecord]:
        return self._diff_simple_map(
            rules.pipeline_aspect_map(old), rules.pipeline_aspect_map(new),
            ChangeType.PIPELINE_CHANGED, "Pipeline",
        )

    def _diff_environment(self, old: AssayManifest, new: AssayManifest) -> list[ChangeRecord]:
        return self._diff_simple_map(
            rules.environment_aspect_map(old), rules.environment_aspect_map(new),
            ChangeType.ENVIRONMENT_CHANGED, "Environment",
        )

    # ------------------------------------------------------------------ #
    # Claims                                                            #
    # ------------------------------------------------------------------ #
    def _diff_claims(self, old: AssayManifest, new: AssayManifest) -> list[ChangeRecord]:
        old_map, new_map = rules.claim_map(old), rules.claim_map(new)
        added, removed, changed = _added_removed_changed(old_map, new_map)
        records: list[ChangeRecord] = []
        for key in added:
            records.append(self._claim_record(ChangeType.CLAIM_ADDED, key, None, new_map[key]))
        for key in removed:
            records.append(self._claim_record(ChangeType.CLAIM_REMOVED, key, old_map[key], None))
        for key in changed:
            records.append(self._claim_record(ChangeType.CLAIM_CHANGED, key, old_map[key], new_map[key]))
        return records

    @staticmethod
    def _claim_record(ct: ChangeType, key: str, old: Any, new: Any) -> ChangeRecord:
        claim_id = key.split(":", 1)[1]
        if ct is ChangeType.CLAIM_CHANGED and isinstance(old, dict) and isinstance(new, dict):
            changed_fields = sorted(
                k for k in set(old) | set(new) if old.get(k) != new.get(k)
            )
            description = (
                f"Claim '{claim_id}' specification changed "
                f"(fields: {', '.join(changed_fields)})."
            )
        else:
            verb = "added" if ct is ChangeType.CLAIM_ADDED else "removed"
            description = f"Claim '{claim_id}' {verb}."
        return ChangeRecord(
            change_id=ChangeRecord.make_id(ct, key),
            change_type=ct,
            category=None,
            component_identity=key,
            old_value=None,  # full claim dicts omitted from the record to keep it compact
            new_value=None,
            description=description,
        )