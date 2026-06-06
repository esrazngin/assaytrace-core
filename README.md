# AssayTrace — Manifest Schema (Step 1)

The **manifest** is the canonical identity card of a clinical NGS assay
pipeline. Every later AssayTrace module consumes it:

1. **Change Detection Engine** — diff two manifests.
2. **Change Impact Graph** — propagate changes through component dependencies.
3. **Assay Claim Impact Mapping** — find which validated claims a change can perturb.
4. **Revalidation Decision Engine** — decide *whether* and *at what scope* revalidation is required.
5. **Audit Report Generator** — emit the change-control record.

This package implements only the schema (Step 1), but is designed so the four
downstream modules need **no schema changes** to be built on top of it.

> **Scope / disclaimer.** This is decision-support tooling for laboratory
> quality processes. It is **not** a medical device and does **not** make
> clinical determinations or constitute CLIA/CAP/IVDR certification. Final
> validation decisions rest with the laboratory director.

## Install

```bash
pip install -e .          # or: pip install pydantic pyyaml
pip install -e ".[dev]"   # for pytest / mypy
```

## Quickstart

```python
from assaytrace import load_manifest

m = load_manifest("examples/manifest.json")
print(m.content_hash())          # stable assay-identity hash
print(m.iter_components())       # uniform (identity, version) list
```

Run the demonstrations and tests:

```bash
python -m examples.build   # regenerate examples/manifest.{json,yaml}
python -m examples.demo    # end-to-end walkthrough
pytest -q                  # 24 tests
```

## Layout

```
assaytrace/
├── models/
│   ├── enums.py       # controlled vocabularies (string enums)
│   ├── common.py      # Checksum, FileResource, Software/ResourceComponent, GenomeReference
│   ├── qc.py          # QCThreshold / QCConfiguration (arbitrary metrics, typed)
│   ├── claims.py      # AssayClaim, PerformanceMetric (+ dependency wiring)
│   ├── pipeline.py    # Pipeline/Reference/Components/Scope/Environment sections
│   ├── assay.py       # AssayMetadata
│   └── manifest.py    # AssayManifest root (+ content hash, traversal)
├── validators/
│   └── integrity.py   # cross-model referential-integrity rules
├── io/
│   └── loader.py      # JSON/YAML load, dump, canonical serialization
examples/              # build.py, demo.py, manifest.json, manifest.yaml
tests/                 # pytest suite
```

## Key design decisions

- **Uniform component shape.** Everything versioned (`SoftwareComponent`,
  `ResourceComponent`, `GenomeReference`) exposes a stable `identity`
  (`category:slug`). The change engine walks manifests generically instead of
  field-by-field.
- **Structured claims with explicit dependencies.** Claims declare
  `depends_on_categories` and `depends_on_components`; this is the seam the
  impact graph traverses. Referential integrity is enforced at load time.
- **Envelope vs. content.** Document metadata (`manifest_id`, `generated_at`,
  `status`, …) is excluded from `content_hash()`, so identical configurations
  hash identically regardless of when they were generated.
- **Immutability + strictness.** All models are `frozen` with `extra="forbid"`:
  a manifest is a tamper-resistant record, and unknown fields are rejected.
- **Extensible QC without schema churn.** QC is a list of typed `QCThreshold`s,
  so new metrics need no model changes.
- **Aggregated, explicit validation.** Cross-model rules (claim/component
  coherence, somatic-VAF requirement) raise one combined error listing every
  problem.
