"""Severity scoring layer (change-magnitude intelligence)."""
from .models import ChangeSeverity, Severity, VersionMagnitude
from .versioning import parse_version, version_magnitude
from .scorer import SeverityScorer

__all__ = [
    "ChangeSeverity",
    "Severity",
    "VersionMagnitude",
    "parse_version",
    "version_magnitude",
    "SeverityScorer",
]
