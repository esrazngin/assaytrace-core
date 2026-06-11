"""Match laboratory-supplied approvals to detected changes.

Produces one ``DeviationApproval`` per detected change (defaulting to
NOT_REVIEWED), and surfaces any supplied approvals whose ``change_id`` does not
correspond to a detected change — an important integrity signal, since a stale
approval referencing a change that no longer exists must not silently pass.
"""

from __future__ import annotations

from ..diff.models import ChangeRecord
from .models import ApprovalStatus, DeviationApproval


class ApprovalMatcher:
    """Stateless, deterministic approval reconciliation."""

    def match(
        self,
        changes: list[ChangeRecord],
        approvals: list[DeviationApproval] | None,
    ) -> tuple[list[DeviationApproval], list[str]]:
        """Return (per_change_approvals, orphan_change_ids).

        ``per_change_approvals`` is aligned to the set of detected changes,
        sorted by change_id; changes without a supplied approval get a
        NOT_REVIEWED record. ``orphan_change_ids`` lists supplied approvals that
        reference no detected change.
        """
        supplied = {a.change_id: a for a in (approvals or [])}
        change_ids = {c.change_id for c in changes}

        out: list[DeviationApproval] = []
        for change in sorted(changes, key=lambda c: c.change_id):
            out.append(
                supplied.get(
                    change.change_id,
                    DeviationApproval(
                        change_id=change.change_id, status=ApprovalStatus.NOT_REVIEWED
                    ),
                )
            )
        orphans = sorted(cid for cid in supplied if cid not in change_ids)
        return out, orphans
