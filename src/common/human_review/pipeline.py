"""Orchestration: route a review request, apply the human decision, and audit it.

A single clean entry point used by the CLI demo (``ui/review_cli.py``) and tests.
Keeps the flow explicit: route -> (human decides if escalated) -> record.
"""

from __future__ import annotations

from src.common.grading.schema import Rubric
from src.common.human_review.audit_log import AuditLog, build_record
from src.common.human_review.review import (
    ReviewRequest,
    ReviewRoute,
    TeacherDecision,
    route,
)


def process_review(
    request: ReviewRequest,
    rubric: Rubric,
    audit_log: AuditLog,
    decision: TeacherDecision | None = None,
) -> ReviewRoute:
    """Route the request, record an audit entry, and return the route taken.

    - AUTO_ACCEPT: ``decision`` may be None; recorded as auto-accepted.
    - ESCALATE_TO_HUMAN: a ``decision`` is REQUIRED (the human must decide). Passing
      None for an escalated request raises, enforcing "the teacher decides".
    """
    taken = route(request)
    if taken is ReviewRoute.ESCALATE_TO_HUMAN and decision is None:
        raise ValueError(
            "Escalated grade requires a TeacherDecision; the tool must not finalise "
            "an escalated grade on its own."
        )
    record = build_record(request, taken, rubric, decision)
    audit_log.append(record)
    return taken
