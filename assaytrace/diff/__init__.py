"""Change Detection Engine (Step 2): detect-only, deterministic manifest diffing."""
from .models import ChangeRecord, ChangeType
from .detector import ChangeDetector

__all__ = ["ChangeRecord", "ChangeType", "ChangeDetector"]