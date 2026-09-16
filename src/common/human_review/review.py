"""Human-in-the-loop review — core types and routing (pure logic, no UI).

Reference implementation of the project's central non-negotiable: **the tool
proposes, the teacher decides.** This is foundational/offline (standard library
only); it is NOT the product's teacher dashboard — that belongs in a separate
product repository. Here we model the *concept* end-to-end so it can be studied,
tested, and audited. Presentation lives in ``ui/`` (e.g. ``ui/review_cli.py``).

Flow:
    ProposedGrade (+ optional EscalationDecision)
        -> ReviewRequest
        -> route(): AUTO_ACCEPT or ESCALATE_TO_HUMAN
        -> TeacherDecision (approve / override) — the human decision is authoritative
        -> audit record (see audit_log.py)

Stakeholder relevance (see README):
    teacher/tutor  -> makes the decision
    content author -> override + escalation reasons feed rubric optimisation
    auditor        -> every decision is logged with its rationale
    product owner  -> override rate over time (hypothesis H4)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.common.grading.schema import CriterionOutcome, ProposedGrade, Rubric
from src.track_a_interpretable.escalation import EscalationDecision


class ReviewRoute(str, Enum):
    AUTO_ACCEPT = "auto_accept"
    ESCALATE_TO_HUMAN = "escalate_to_human"


class DecisionKind(str, Enum):
    APPROVED = "approved"          # human accepted the proposed grade as-is
    OVERRIDDEN = "overridden"      # human changed one or more criterion outcomes


@dataclass(frozen=True)
class ReviewRequest:
    """A proposed grade awaiting a routing decision (and possibly a human)."""

    rubric_id: str
    example_id: str
    answer_text: str
    proposed: ProposedGrade
    escalation: EscalationDecision | None = None

    def escalate_reason(self) -> str:
        if self.proposed.security_violation:
            return "security violation (likely prompt injection) detected"
        if self.escalation is not None:
            return self.escalation.reason
        if self.proposed.spurious_reliance_flag:
            return "spurious_reliance_flag set"
        return ""


@dataclass(frozen=True)
class TeacherDecision:
    """The human decision. Authoritative: it overrides the proposed grade.

    ``final_outcomes`` maps criterion_id -> the teacher's final CriterionOutcome.
    For an approval it equals the proposed outcomes; for an override it differs on
    at least one criterion.
    """

    kind: DecisionKind
    teacher_id: str
    final_outcomes: dict[str, CriterionOutcome] = field(default_factory=dict)
    comment: str = ""

    def final_total(self, rubric: Rubric) -> float:
        by_id = {c.id: c for c in rubric.criteria}
        return sum(
            by_id[cid].points_for(outcome)
            for cid, outcome in self.final_outcomes.items()
            if cid in by_id
        )


def route(request: ReviewRequest) -> ReviewRoute:
    """Decide whether a proposed grade can be auto-accepted or needs a human.

    A grade is escalated if the interpretability layer flagged spurious reliance
    (``spurious_reliance_flag``) or an EscalationDecision says so. Everything else is
    eligible for auto-accept. This is deliberately conservative for a high-stakes
    grading context; a deployment may require human review of *all* grades, which is
    achievable by forcing escalation (see ``route_all_to_human``).
    """
    if request.proposed.spurious_reliance_flag:
        return ReviewRoute.ESCALATE_TO_HUMAN
    if request.proposed.security_violation:
        return ReviewRoute.ESCALATE_TO_HUMAN
    if request.escalation is not None and request.escalation.escalate:
        return ReviewRoute.ESCALATE_TO_HUMAN
    return ReviewRoute.AUTO_ACCEPT


def route_all_to_human(request: ReviewRequest) -> ReviewRoute:
    """Strictest policy: every grade requires human approval (never auto-accept)."""
    return ReviewRoute.ESCALATE_TO_HUMAN


def approve(
    proposed: ProposedGrade, teacher_id: str, comment: str = ""
) -> TeacherDecision:
    """Convenience: teacher approves the proposed grade unchanged."""
    return TeacherDecision(
        kind=DecisionKind.APPROVED,
        teacher_id=teacher_id,
        final_outcomes={a.criterion_id: a.outcome for a in proposed.assessments},
        comment=comment,
    )


def override(
    proposed: ProposedGrade,
    teacher_id: str,
    changes: dict[str, CriterionOutcome],
    comment: str = "",
) -> TeacherDecision:
    """Convenience: teacher overrides one or more criterion outcomes.

    ``changes`` maps criterion_id -> new outcome; unspecified criteria keep the
    proposed outcome. Marked APPROVED if the changes happen to match the proposal.
    """
    final = {a.criterion_id: a.outcome for a in proposed.assessments}
    final.update(changes)
    proposed_map = {a.criterion_id: a.outcome for a in proposed.assessments}
    kind = DecisionKind.APPROVED if final == proposed_map else DecisionKind.OVERRIDDEN
    return TeacherDecision(
        kind=kind, teacher_id=teacher_id, final_outcomes=final, comment=comment
    )
