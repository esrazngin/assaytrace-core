"""Approved-deviation models (intentional, reviewed laboratory changes).

An approval is *input*, not something AssayTrace computes: a laboratory asserts
that a detected change was intentional and reviewed. Approvals reference a
detected change by its deterministic ``change_id`` so the audit trail links
Detected Change -> Approval Status -> Approval Rationale unambiguously.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    PENDING = "pending"
    REJECTED = "rejected"
    NOT_REVIEWED = "not_reviewed"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class ApprovalEvent(BaseModel):
    """A single dated disposition in a change's approval history."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    approval_id: str
    status: ApprovalStatus
    reviewer: str | None = None
    date: str | None = None
    conditions: str | None = None
    rationale: str | None = None


class DeviationApproval(BaseModel):
    """A laboratory's documented disposition of a single detected change.

    ``status`` / ``reviewer`` / ``approval_date`` / ``rationale`` describe the
    *latest* disposition (unchanged, backward compatible). ``history`` optionally
    records the full sequence of dispositions leading to it, so the audit trail
    can show e.g. Pending Review -> Approved With Conditions -> Approved.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str
    status: ApprovalStatus = ApprovalStatus.NOT_REVIEWED
    reviewer: str | None = None
    approval_date: str | None = None
    rationale: str | None = None
    approval_id: str | None = None
    conditions: str | None = None
    history: tuple[ApprovalEvent, ...] = ()
