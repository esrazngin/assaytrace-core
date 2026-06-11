"""Deterministic registry that dispatches payloads to ingestion adapters."""

from __future__ import annotations

from .base import IngestionError, ManifestSourceAdapter
from .models import IngestionResult, SourceType


class AdapterRegistry:
    """An ordered, deterministic collection of ingestion adapters."""

    def __init__(self) -> None:
        self._adapters: list[ManifestSourceAdapter] = []

    def register(self, adapter: ManifestSourceAdapter) -> "AdapterRegistry":
        self._adapters.append(adapter)
        return self

    def available(self) -> list[SourceType]:
        """The source types this registry can route, in registration order."""
        return [a.source_type for a in self._adapters]

    def adapter_for(self, payload: dict) -> ManifestSourceAdapter | None:
        for adapter in self._adapters:
            if adapter.can_handle(payload):
                return adapter
        return None

    def ingest(self, payload: dict) -> IngestionResult:
        adapter = self.adapter_for(payload)
        if adapter is None:
            raise IngestionError(
                "No registered ingestion adapter can handle this payload "
                f"(source_type={payload.get('source_type')!r})."
            )
        return adapter.ingest(payload)


def default_registry() -> AdapterRegistry:
    """A registry seeded with the example adapter and the roadmap stubs."""
    from .adapters import (
        GenericManifestAdapter, roadmap_adapters,
    )

    registry = AdapterRegistry()
    registry.register(GenericManifestAdapter())
    for adapter in roadmap_adapters():
        registry.register(adapter)
    return registry
