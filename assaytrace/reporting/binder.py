"""Audit binder builder (Step 12).

Single orchestration point for the full analysis pipeline, reused by the CLI
and web demo so logic is never duplicated. It calls the existing engines
(Steps 2-11) and assembles a deterministic ``AuditBinder``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..claims_impact.mapper import ClaimImpactMapper
from ..decision.engine import RevalidationDecisionEngine
from ..decision.no_revalidation import NoRevalidationDeterminer
from ..diff.detector import ChangeDetector
from ..evidence.benchmark import BenchmarkPackage
from ..evidence.models import GiabEvidencePackage
from ..impact.graph import ChangeImpactGraph
from ..models.manifest import AssayManifest
from ..approval.matcher import ApprovalMatcher
from ..approval.models import DeviationApproval
from ..regression.detector import PerformanceRegressionDetector
from ..severity.scorer import SeverityScorer
from ..regression.gate import evaluate_gate, RegressionGateThresholds
from ..regression.models import RegressionThresholds
from ..reportable.classification import ReportableVariant, ReportableVariantDiffer
from ..reportable.models import ReportableVariantObservation
from ..reportable.viewer import ReportableVariantDeltaViewer
from .models import AuditBinder, SignOffSection


def build_binder(
    old_manifest: AssayManifest,
    new_manifest: AssayManifest,
    *,
    current_evidence: GiabEvidencePackage | None = None,
    baseline_evidence: GiabEvidencePackage | None = None,
    current_benchmark: BenchmarkPackage | None = None,
    baseline_benchmark: BenchmarkPackage | None = None,
    old_variants: list[ReportableVariant] | None = None,
    new_variants: list[ReportableVariant] | None = None,
    old_reportable: list[ReportableVariantObservation] | None = None,
    new_reportable: list[ReportableVariantObservation] | None = None,
    sign_off: SignOffSection | None = None,
    regression_thresholds: RegressionThresholds | None = None,
    regression_gate_thresholds: RegressionGateThresholds | None = None,
    policy=None,
    approvals: list[DeviationApproval] | None = None,
    generated_at: datetime | None = None,
) -> AuditBinder:
    changes = ChangeDetector().compare(old_manifest, new_manifest)
    impacts = ChangeImpactGraph().evaluate(changes)
    claim_impacts = ClaimImpactMapper().map(
        manifest=new_manifest, changes=changes, impacts=impacts
    )
    severities = SeverityScorer().score(changes)
    decisions = RevalidationDecisionEngine().decide(
        changes, impacts, claim_impacts, policy=policy, severities=severities
    )
    no_reval = NoRevalidationDeterminer().determine(decisions)
    approval_records, orphan_approvals = ApprovalMatcher().match(changes, approvals)

    regression = ()
    detector = PerformanceRegressionDetector(regression_thresholds)
    if current_benchmark is not None and baseline_benchmark is not None:
        regression = tuple(detector.compare(baseline_benchmark, current_benchmark))
    elif current_evidence is not None and baseline_evidence is not None:
        regression = tuple(detector.compare(baseline_evidence, current_evidence))

    # Regression Gate (Critical Issue #2): turn regression evidence into a
    # deterministic control that influences the downstream binder lifecycle.
    regression_gate = evaluate_gate(regression, regression_gate_thresholds)

    reportable_deltas = ()
    if old_reportable is not None or new_reportable is not None:
        reportable_deltas = tuple(
            ReportableVariantDeltaViewer().compare(
                old_reportable or [], new_reportable or []
            )
        )

    classification_deltas = ()
    if old_variants is not None or new_variants is not None:
        classification_deltas = tuple(
            ReportableVariantDiffer().diff(old_variants or [], new_variants or [])
        )

    return AuditBinder(
        generated_at=generated_at or datetime.now(timezone.utc),
        assay_name=new_manifest.assay.assay_name,
        assay_version=new_manifest.assay.assay_version,
        laboratory_name=new_manifest.assay.laboratory_name,
        laboratory_id=new_manifest.assay.laboratory_id,
        old_manifest_id=str(old_manifest.manifest_id),
        new_manifest_id=str(new_manifest.manifest_id),
        old_content_hash=old_manifest.content_hash(),
        new_content_hash=new_manifest.content_hash(),
        changes=tuple(changes),
        impacts=tuple(impacts),
        claim_impacts=tuple(claim_impacts),
        decisions=tuple(decisions),
        no_revalidation_records=tuple(no_reval),
        change_severities=tuple(severities),
        approvals=tuple(approval_records),
        orphan_approvals=tuple(orphan_approvals),
        policy_name=(policy.name if policy is not None else None),
        policy_version=(getattr(policy, "version", None) if policy is not None else None),
        policy_hash=(policy.content_hash() if policy is not None else None),
        baseline_benchmark=baseline_evidence,
        current_benchmark=current_evidence,
        baseline_benchmark_pkg=baseline_benchmark,
        current_benchmark_pkg=current_benchmark,
        regression=regression,
        regression_gate=regression_gate,
        reportable_deltas=reportable_deltas,
        variant_classification_deltas=classification_deltas,
        sign_off=sign_off or SignOffSection(),
    )
