"""Shared fixtures. We build the canonical valid manifest once, serialize it to
a plain dict, and let each test deep-copy and mutate that dict — exercising the
same `model_validate` path real callers use when loading files."""

from __future__ import annotations

import copy

import pytest

from assaytrace import AssayManifest
from examples.build import build


@pytest.fixture(scope="session")
def valid_manifest() -> AssayManifest:
    return build()


@pytest.fixture()
def valid_dict(valid_manifest: AssayManifest) -> dict:
    return copy.deepcopy(valid_manifest.model_dump(mode="json"))
