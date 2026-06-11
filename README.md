# AssayTrace

**Deterministic change-control & revalidation governance for clinical NGS laboratories.**

AssayTrace tells a laboratory *what changed* between two versions of a clinical
next-generation-sequencing (NGS) assay, *which validated claims* the change can
affect, *what revalidation* the laboratory's own SOP requires, and produces an
*audit-ready binder* documenting the decision — all through a transparent,
rule-driven engine with **no AI/LLM in the decision path**.

> AssayTrace is a governance and documentation platform. It does **not** run
> pipelines, call or interpret variants, or make clinical decisions.

---

## 1. What AssayTrace is

A change-control and revalidation decision platform for laboratories running
clinical NGS assays under CLIA / CAP / IVDR. It compares two **assay manifests**
(declarative descriptions of an assay version) and produces a defensible,
fully-traceable revalidation decision plus an audit binder (HTML and PDF).

## 2. The problem it solves

Clinical NGS assays change constantly: a variant caller is bumped a patch
version, a reference genome is updated, an annotation database is refreshed, a QC
threshold is loosened, a container digest changes. Each change *may* require
revalidation — or may not. Today that judgement lives in spreadsheets, email
threads, and senior bioinformaticians' heads. It is slow, inconsistent, and hard
to defend in an audit.

AssayTrace makes that judgement **explicit, deterministic, and auditable**: the
same inputs always produce the same decision, every decision names the rule that
produced it, and the result is captured in a citable binder with content hashes.

## 3. Why revalidation is difficult

- A single change can touch multiple validated claims (e.g. a VAF-threshold
  change affects SNV and INDEL sensitivity and limit of detection).
- Different laboratories legitimately handle the same change differently —
  revalidation scope is a matter of SOP, not universal truth.
- Evidence of "no performance regression" must be tied to the decision, not filed
  separately.
- Auditors need to reconstruct *why* a decision was made months later.

## 4. Core concepts

- **Manifest diffing** — deterministic comparison of two assay manifests into a
  sorted, stable set of typed change records.
- **Claim dependency mapping** — each change is mapped to the validated analytical
  claims it can perturb, via explicit dependency wiring and externalized rule
  tables (including a QC-parameter → performance-characteristic → claim mapping).
- **Impact classification** — every change is classified into a technical impact
  domain with a traceable rationale.
- **Policy engine** — laboratory SOPs (versioned, hashed) drive the revalidation
  decision; the engine consults policy first and falls back to documented
  built-in defaults.
- **Approval workflow** — deviations carry dispositions (approved, approved with
  conditions, rejected, pending) with reviewer, date, conditions, and history.
- **Audit binder** — an HTML/PDF artifact with executive summary, business impact,
  approval summary, audit metadata, decision chain, and content hashes.
- **Regression gate** — benchmark comparisons are turned into a deterministic gate
  (PASS / MANUAL_REVIEW / BLOCKED) that can block finalization.
- **Portfolio governance** — many assays governed at once, each summarized from a
  real binder, with KPIs, risk distribution, and activity.

## 5. Example workflow

```
Manifest A (current validated assay)
        |
        v
Manifest B (proposed new version)
        |
        v
Impact Classification   (what technical domain each change touches)
        |
        v
Claims Mapping          (which validated claims are affected)
        |
        v
Policy Evaluation       (laboratory SOP decides the revalidation scope)
        |
        v
Decision                (per-change revalidation type + rationale + rule id)
        |
        v
Audit Binder            (HTML / PDF, hashed, finalizable when clean)
```

## 6. Architecture overview

A pipeline of small, deterministic, frozen-model layers — each is stateless and
emits sorted, reproducible output:

```
diff -> impact -> claims_impact -> severity -> decision
                                                  |
        policy ------------------------------------/
                                                  |
   approval . regression(gate) . reporting(binder/pdf/presentation) . web
```

- Models are immutable (Pydantic v2, `frozen=True`, `extra="forbid"`).
- Rule tables are externalized data, not code branches.
- The shared `reporting/presentation.py` feeds both the web UI and the PDF, so
  they cannot drift.
- Benchmark packages enforce internal consistency (F1 must match precision/recall).

## 7. Screenshots

Run the app locally (below) and open `http://127.0.0.1:5000`. Key views:

- **Dashboard** — Level 1 KPI strip (Changes, Claims Impacted, Highest Risk,
  Required Action, Effort, Review Time), Level 2 executive summary (business
  impact, recommended next step, regression/approval status), Level 3 detail
  (top impact, timeline, governance, decision chain).
- **Portfolio** — multi-assay table with status / risk / required action / claims
  impacted / policy version, KPIs, filters, risk distribution, and activity.
- **Policies** — SOP library with version history, lifecycle actions, SOP detail
  (rule inventory, lineage, governed assays, hash), and version comparison.
- **Audit & Decision** — binder lifecycle banner, reasoning timeline, decision
  chain, audit metadata.
- **PDF binder** — `sample_audit_binder.pdf` (executive summary -> business impact
  -> approval summary -> audit metadata; DRAFT/UNDER REVIEW watermark).

## 8. Quick start

```bash
pip install -e .            # or: pip install pydantic pyyaml flask fpdf2 pypdf pytest
python -m assaytrace.web.app
# open http://127.0.0.1:5000  (the demo auto-runs an analysis on load)
```

## 9. Running locally

The web app loads a built-in somatic demo automatically (it POSTs to
`/api/analyze`). Endpoints include `/api/analyze`, `/api/portfolio`,
`/api/policy`, and `/api/policy-compare`. To generate a binder programmatically:

```python
from examples.build import build
from assaytrace.reporting import build_binder, render_pdf
binder = build_binder(build(), build())          # old, new manifests
render_pdf(binder, "binder.pdf")
```

## 10. Running tests

```bash
python -m pytest -q
```

## 11. Project structure

```
assaytrace/
  diff/           manifest change detection
  impact/         change impact classification
  claims_impact/  change -> validated-claim mapping (incl. QC parameter rules)
  severity/       severity & version-magnitude scoring
  decision/       revalidation decision engine
  policy/         SOP policy engine, loader, comparison
  approval/       deviation approval workflow
  regression/     benchmark regression detector + regression gate
  reporting/      audit binder, PDF export, shared presentation layer
  ingestion/      extensible manifest-ingestion adapter framework
  portfolio.py    multi-assay portfolio summaries
  web/            Flask app + single-page UI
examples/         manifest builders + benchmark fixtures
tests/            full deterministic test suite
```

## 12. Regulatory positioning

AssayTrace supports a laboratory's existing change-control and revalidation SOPs.
It is a documentation and governance tool.

**AssayTrace does NOT:**

- run sequencing pipelines or execute workflows
- call variants
- interpret or reclassify variants
- make clinical decisions or issue diagnostic results

It **does** provide deterministic, rule-driven, auditable change-control and
revalidation **governance**: manifest diffing, claim-impact mapping, policy-driven
decisions, approval workflow, regression gating, and audit binders. The laboratory
remains responsible for its SOPs, its validation, and its clinical determinations.

## 13. Competitive positioning

The point below is not that other tools are bad — they are excellent at what
they do. It is that **none of them occupy AssayTrace's category**: deterministic,
SOP-driven change-control and revalidation governance for clinical NGS assays.

| Capability                        | Excel   | Jira    | Benchling | Illumina BaseSpace | AssayTrace |
| --------------------------------- | ------- | ------- | --------- | ------------------ | ---------- |
| Change tracking                   | Partial | Partial | Partial   | Partial            | Yes        |
| Claim impact mapping              | No      | No      | No        | No                 | Yes        |
| SOP-driven revalidation decisions | No      | No      | No        | No                 | Yes        |
| Approval workflow                 | Manual  | Generic | Partial   | Partial            | Yes        |
| Regression gating                 | No      | No      | No        | Partial            | Yes        |
| Audit binder generation           | No      | No      | No        | No                 | Yes        |
| Clinical NGS change governance    | No      | No      | No        | No                 | Yes        |

AssayTrace is **not** a LIMS, an ELN, a pipeline orchestrator, or a variant
interpretation platform. It occupies a dedicated **governance layer between assay
change management and regulatory revalidation documentation** — the step that
today is handled manually and is hardest to defend in an audit. It complements
these systems rather than replacing them: a laboratory can keep its LIMS, ELN,
and pipeline tooling and use AssayTrace to make the revalidation decision
deterministic, traceable, and audit-ready.

## 14. Roadmap

- Manifest ingestion connectors (Nextflow, nf-core, DRAGEN, Docker, Git, CWL,
  WDL) on top of the existing adapter framework.
- Persistent portfolio storage and per-assay drill-through.
- Policy comparison extended to severity-floor and claim-mapping deltas.
- Optional decision-step severity floor (CRITICAL forcing full revalidation).
- Multi-user authentication and role-based approval routing.

## 15. License

Proprietary -- (c) Esra Zengin. Contact for pilot and evaluation terms.

## 16. Contact

- **Email:** esra.zengiinn@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/esra-zengin-
- **GitHub:** https://github.com/esrazngin

For pilot discussions, feedback, or evaluation access, please reach out.
