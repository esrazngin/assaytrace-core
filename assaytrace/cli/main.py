"""AssayTrace command-line interface (Step 13).

Commands: impact, decision, audit, report. All logic is delegated to the
existing modules and the shared binder builder — the CLI only parses arguments,
loads inputs, and formats output. No business logic is duplicated here.

  python -m assaytrace impact   --old old.json --new new.json
  python -m assaytrace decision --old old.json --new new.json
  python -m assaytrace audit     --old old.json --new new.json [--evidence cur.json] \
                                 [--baseline-evidence base.json] --out report.html
  python -m assaytrace report   --old old.json --new new.json [--out binder.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ..claims_impact.mapper import ClaimImpactMapper
from ..decision.engine import RevalidationDecisionEngine
from ..decision.no_revalidation import NoRevalidationDeterminer
from ..diff.detector import ChangeDetector
from ..evidence.parsers import load_evidence_package
from ..impact.graph import ChangeImpactGraph
from ..io.loader import load_manifest
from ..reportable.models import ReportableVariantObservation
from ..reporting.binder import build_binder
from ..reporting.html import render_html


def _load_reportable(path: str | None) -> list[ReportableVariantObservation] | None:
    if path is None:
        return None
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [ReportableVariantObservation.model_validate(item) for item in raw]


def _cmd_impact(args: argparse.Namespace) -> int:
    old = load_manifest(args.old)
    new = load_manifest(args.new)
    changes = ChangeDetector().compare(old, new)
    impacts = {i.change_id: i for i in ChangeImpactGraph().evaluate(changes)}
    print("## Detected Changes")
    for c in changes:
        print(f"  {c.component_identity}: {c.old_value} -> {c.new_value} "
              f"[{c.change_type.value}]")
    print("\n## Impact Domains")
    for c in changes:
        print(f"  {c.component_identity:<34} {impacts[c.change_id].impact_domain.value}")
    if not changes:
        print("  (no changes)")
    return 0


def _cmd_decision(args: argparse.Namespace) -> int:
    old = load_manifest(args.old)
    new = load_manifest(args.new)
    changes = ChangeDetector().compare(old, new)
    impacts = ChangeImpactGraph().evaluate(changes)
    claim_impacts = ClaimImpactMapper().map(manifest=new, changes=changes, impacts=impacts)
    decisions = RevalidationDecisionEngine().decide(changes, impacts, claim_impacts)
    no_reval = NoRevalidationDeterminer().determine(decisions)
    print("## Revalidation Decisions")
    for d in decisions:
        print(f"  [{d.decision_type.value}] {d.change_id}")
        print(f"      rationale: {d.rationale}")
        print(f"      affected_claims: {', '.join(d.affected_claims) or '—'}")
        print(f"      required_evidence: {'; '.join(d.required_evidence) or '—'}")
    if not decisions:
        print("  (no revalidation required — no changes detected)")
    print("\n## Defensible No-Revalidation Records")
    for r in no_reval:
        print(f"  {r.decision_id}: {r.rationale}")
    if not no_reval:
        print("  (none)")
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    old = load_manifest(args.old)
    new = load_manifest(args.new)
    current = load_evidence_package(args.evidence) if args.evidence else None
    baseline = load_evidence_package(args.baseline_evidence) if args.baseline_evidence else None
    binder = build_binder(
        old, new,
        current_evidence=current,
        baseline_evidence=baseline,
        old_reportable=_load_reportable(args.reportable_old),
        new_reportable=_load_reportable(args.reportable_new),
    )
    html = render_html(binder)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"Wrote audit binder: {args.out}")
    print(f"  changes={len(binder.changes)} decisions={len(binder.decisions)} "
          f"no_revalidation={len(binder.no_revalidation_records)} "
          f"regression={len(binder.regression)}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    old = load_manifest(args.old)
    new = load_manifest(args.new)
    current = load_evidence_package(args.evidence) if args.evidence else None
    baseline = load_evidence_package(args.baseline_evidence) if args.baseline_evidence else None
    binder = build_binder(
        old, new, current_evidence=current, baseline_evidence=baseline,
    )
    payload = json.dumps(binder.model_dump(mode="json"), indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"Wrote binder model: {args.out}")
    else:
        print(payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="assaytrace")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--old", required=True, help="Old manifest (JSON/YAML).")
        p.add_argument("--new", required=True, help="New manifest (JSON/YAML).")

    p_impact = sub.add_parser("impact", help="Detect changes and classify impact domains.")
    add_common(p_impact)
    p_impact.set_defaults(func=_cmd_impact)

    p_decision = sub.add_parser("decision", help="Produce revalidation decisions.")
    add_common(p_decision)
    p_decision.set_defaults(func=_cmd_decision)

    p_audit = sub.add_parser("audit", help="Build the audit binder and render HTML.")
    add_common(p_audit)
    p_audit.add_argument("--evidence", help="Current GIAB evidence package (JSON).")
    p_audit.add_argument("--baseline-evidence", help="Baseline GIAB evidence package (JSON).")
    p_audit.add_argument("--reportable-old", help="Old reportable variants (JSON list).")
    p_audit.add_argument("--reportable-new", help="New reportable variants (JSON list).")
    p_audit.add_argument("--out", required=True, help="Output HTML path.")
    p_audit.set_defaults(func=_cmd_audit)

    p_report = sub.add_parser("report", help="Emit the structured (PDF-ready) binder model as JSON.")
    add_common(p_report)
    p_report.add_argument("--evidence", help="Current GIAB evidence package (JSON).")
    p_report.add_argument("--baseline-evidence", help="Baseline GIAB evidence package (JSON).")
    p_report.add_argument("--out", help="Output JSON path (stdout if omitted).")
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())