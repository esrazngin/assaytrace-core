"""Adapter contract and base classes for manifest ingestion."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import IngestionResult, SourceType


class IngestionError(Exception):
    """Raised when a payload cannot be ingested by a chosen adapter."""


class ManifestSourceAdapter(ABC):
    """Contract every ingestion adapter must satisfy.

    An adapter handles exactly one ``source_type``. ``can_handle`` is a cheap,
    deterministic check (e.g. file extension or a marker key); ``ingest`` does
    the extraction and returns a deterministic ``IngestionResult``. Adapters
    must not perform network calls or non-deterministic work at this layer.
    """

    #: The source type this adapter consumes.
    source_type: SourceType

    @abstractmethod
    def can_handle(self, payload: dict) -> bool:
        """Return True if this adapter can ingest ``payload``."""

    @abstractmethod
    def ingest(self, payload: dict) -> IngestionResult:
        """Extract a manifest fragment from ``payload`` deterministically."""


class NotImplementedAdapter(ManifestSourceAdapter):
    """A declared-but-unbuilt connector.

    Lets the framework advertise a roadmap of supported sources while making the
    boundary explicit and honest: calling ``ingest`` fails loudly rather than
    fabricating data. Concrete connectors replace these as they are built.
    """

    def __init__(self, source_type: SourceType, marker: str | None = None) -> None:
        self.source_type = source_type
        self._marker = marker or source_type.value

    def can_handle(self, payload: dict) -> bool:
        return bool(payload) and payload.get("source_type") == self.source_type.value

    def ingest(self, payload: dict) -> IngestionResult:
        raise IngestionError(
            f"The '{self.source_type.value}' ingestion adapter is declared but "
            f"not yet implemented. Supply a manifest directly, or contribute a "
            f"connector implementing ManifestSourceAdapter for this source."
        )
