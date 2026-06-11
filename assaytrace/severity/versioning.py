"""Deterministic version-magnitude detection.

Parses version strings into integer components and classifies the difference
between two versions as PATCH / MINOR / MAJOR (or NONE / UNKNOWN). Tolerant of
common forms: 'v2.2.1', '4.5.0.0' (4-part GATK), '111', '2025-12-01'. When a
string is not numerically comparable the magnitude is UNKNOWN — never guessed.
"""

from __future__ import annotations

import re

from .models import VersionMagnitude

_LEADING_INT = re.compile(r"^(\d+)")


def parse_version(value: object) -> tuple[int, ...]:
    """Return the numeric dotted components of a version string.

    'v4.5.0.0' -> (4, 5, 0, 0); '111' -> (111,); 'GRCh38.p14' -> (38, 14) is
    avoided — only purely numeric leading segments count, so 'GRCh38' yields ().
    Returns () when no leading numeric component exists.
    """
    if value is None:
        return ()
    text = str(value).strip().lstrip("vV")
    parts: list[int] = []
    for raw in text.split("."):
        m = _LEADING_INT.match(raw)
        if not m:
            break
        parts.append(int(m.group(1)))
    return tuple(parts)


def version_magnitude(old: object, new: object) -> VersionMagnitude:
    """Classify the magnitude of a version change deterministically."""
    a, b = parse_version(old), parse_version(new)
    if not a or not b:
        return VersionMagnitude.UNKNOWN
    width = max(len(a), len(b))
    a += (0,) * (width - len(a))
    b += (0,) * (width - len(b))
    if a == b:
        return VersionMagnitude.NONE
    if a[0] != b[0]:
        return VersionMagnitude.MAJOR
    if len(a) > 1 and a[1] != b[1]:
        return VersionMagnitude.MINOR
    return VersionMagnitude.PATCH
