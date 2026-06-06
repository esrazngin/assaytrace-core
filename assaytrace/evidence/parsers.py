"""Parsers for evidence packages (Step 8 + Part 1).

Today these parse structured dicts / JSON into the evidence models. The same
entry points are where a future real-benchmark parser (e.g., hap.py summary ->
package) would plug in, without changing downstream consumers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .benchmark import BenchmarkPackage
from .models import GiabEvidencePackage


def parse_evidence_package(data: dict[str, Any]) -> GiabEvidencePackage:
    """Build and validate a (legacy MVP) evidence package from a plain dict."""
    return GiabEvidencePackage.model_validate(data)


def load_evidence_package(path: str | Path) -> GiabEvidencePackage:
    """Load and validate a (legacy MVP) evidence package from a JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_evidence_package(raw)


def parse_benchmark_package(data: dict[str, Any]) -> BenchmarkPackage:
    """Build and validate a standardized benchmark package from a plain dict."""
    return BenchmarkPackage.model_validate(data)


def load_benchmark_package(path: str | Path) -> BenchmarkPackage:
    """Load and validate a standardized benchmark package from a JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_benchmark_package(raw)