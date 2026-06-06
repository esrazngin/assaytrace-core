"""Loading, dumping, and canonical serialization of manifests.

Format is inferred from the file extension. YAML is offered because labs and
quality teams hand-edit configuration far more comfortably in YAML than JSON;
JSON is the canonical wire/hash format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..models.manifest import AssayManifest

_YAML_SUFFIXES = {".yaml", ".yml"}
_JSON_SUFFIXES = {".json"}


def _read_raw(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in _YAML_SUFFIXES:
        data = yaml.safe_load(text)
    elif suffix in _JSON_SUFFIXES:
        data = json.loads(text)
    else:
        raise ValueError(
            f"unsupported manifest extension '{suffix}'; use .json, .yaml, or .yml"
        )
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping/object")
    return data


def load_manifest(path: str | Path) -> AssayManifest:
    """Parse and fully validate a manifest from a JSON or YAML file."""
    return AssayManifest.model_validate(_read_raw(Path(path)))


def dump_manifest(
    manifest: AssayManifest, path: str | Path, *, indent: int = 2
) -> None:
    """Serialize a manifest to JSON or YAML, inferring format from extension."""
    p = Path(path)
    payload = manifest.model_dump(mode="json")
    suffix = p.suffix.lower()
    if suffix in _YAML_SUFFIXES:
        p.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    elif suffix in _JSON_SUFFIXES:
        p.write_text(json.dumps(payload, indent=indent), encoding="utf-8")
    else:
        raise ValueError(f"unsupported output extension '{suffix}'")


def to_canonical_json(manifest: AssayManifest) -> str:
    """Stable, sorted JSON of the full manifest (envelope included)."""
    return json.dumps(
        manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
