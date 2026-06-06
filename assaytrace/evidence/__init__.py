"""Evidence packages: legacy GIAB MVP model + standardized benchmark schema."""
from .models import GiabEvidencePackage
from .benchmark import BenchmarkPackage, MetricTriplet
from .parsers import (
    parse_evidence_package,
    load_evidence_package,
    parse_benchmark_package,
    load_benchmark_package,
)

__all__ = [
    "GiabEvidencePackage",
    "BenchmarkPackage",
    "MetricTriplet",
    "parse_evidence_package",
    "load_evidence_package",
    "parse_benchmark_package",
    "load_benchmark_package",
]