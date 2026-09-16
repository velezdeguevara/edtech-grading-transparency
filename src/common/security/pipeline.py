"""Security pipeline integration.

Ties the two security layers to the grading + human-review flow. On a detected
injection, we do NOT crash and do NOT let the model finalise the grade: we produce a
conservative proposed grade (all criteria not_met) flagged ``security_violation=True``,
which the human-review router escalates to a teacher. The human decides — the classifier
verdict is advisory, never final (EU-AI-Act-consistent human oversight).

Layer 1 (sanitize/spotlight) is always applied inside the grader's prompt. This module
adds the optional Layer 2 (classifier) check that runs BEFORE grading.
"""

from __future__ import annotations

from src.common.grading.schema import (
    CriterionAssessment,
    CriterionOutcome,
    ProposedGrade,
    Rubric,
)


def security_violation_grade(rubric: Rubric, note: str = "") -> ProposedGrade:
    """A conservative proposed grade for a detected attack: all criteria not_met.

    Flagged ``security_violation=True`` so the human-review router escalates it. It is a
    *proposal* pending human review, not a final grade — a human may still override if
    the detection was a false positive.
    """
    assessments = tuple(
        CriterionAssessment(
            criterion_id=c.id,
            outcome=CriterionOutcome.NOT_MET,
            evidence_span="",
            confidence=0.0,
        )
        for c in rubric.criteria
    )
    return ProposedGrade(
        rubric_id=rubric.id,
        assessments=assessments,
        security_violation=True,
        notes=note or "security: likely prompt injection detected; escalated to human",
    )
