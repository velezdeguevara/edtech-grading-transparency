"""Stdlib-only CLI demo of the human-in-the-loop review flow.

Foundational, dependency-free interface for understanding the concept: it walks the
WWI fixtures through the Track A interpretable grader, shows the proposed grade and
the escalation reason, simulates a teacher decision on escalated items, and writes an
audit record. No web framework, no GPU, no model — runs anywhere Python runs.

Run from the repo root:
    python -m ui.review_cli

This is a *demo* interface. A production teacher dashboard belongs in a separate
product repository, not here.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from src.common.grading.schema import CriterionOutcome
from src.common.human_review.audit_log import AuditLog, summarize_override_rate
from src.common.human_review.pipeline import process_review
from src.common.human_review.review import (
    ReviewRequest,
    ReviewRoute,
    approve,
    override,
)
from src.common.rubrics.loader import load_fixtures, load_rubric
from src.track_a_interpretable.grader import InterpretableGrader

RUBRIC_ID = "ss-wwi-causes-v1"


def _short(text: str, n: int = 90) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _simulate_teacher(request: ReviewRequest, rubric):
    """A stand-in for a real teacher, for demo purposes only.

    Rule of thumb: if the grade was escalated for spurious reliance, the 'teacher'
    corrects the most over-credited criterion down to not_met, illustrating an
    override; otherwise they approve. Real deployments replace this with a human.
    """
    proposed_map = {a.criterion_id: a.outcome for a in request.proposed.assessments}
    met = [cid for cid, o in proposed_map.items() if o is CriterionOutcome.MET]
    if met:
        return override(
            request.proposed,
            teacher_id="demo-teacher",
            changes={met[0]: CriterionOutcome.NOT_MET},
            comment="demo override: escalated for spurious reliance; corrected on review",
        )
    return approve(request.proposed, teacher_id="demo-teacher", comment="demo approve")


def main() -> None:
    rubric = load_rubric(RUBRIC_ID)
    examples = load_fixtures(RUBRIC_ID)
    grader = InterpretableGrader()  # Mode 1 artifact backend by default

    # Use a temporary audit log for the demo so repeated runs stay clean.
    tmp = Path(tempfile.gettempdir()) / "edtech_grading_demo_audit.jsonl"
    tmp.unlink(missing_ok=True)
    audit = AuditLog(path=tmp)

    print("=== Human-in-the-loop review demo ===")
    print(f"Rubric: {rubric.question}\n")
    print(f"(interp backend: {grader.backend.mode})\n")

    for ex in examples:
        graded, decision_signal = grader.grade_example(rubric, ex.id, ex.answer_text)
        request = ReviewRequest(
            rubric_id=rubric.id,
            example_id=ex.id,
            answer_text=ex.answer_text,
            proposed=graded,
            escalation=decision_signal,
        )
        taken = None
        if request.proposed.spurious_reliance_flag or decision_signal.escalate:
            teacher = _simulate_teacher(request, rubric)
            taken = process_review(request, rubric, audit, decision=teacher)
        else:
            taken = process_review(request, rubric, audit, decision=None)

        proposed_total = graded.total_points(rubric)
        line = (
            f"- {ex.id:32s} proposed={proposed_total:4.1f}/{rubric.max_total:.0f}  "
            f"route={taken.value}"
        )
        if taken is ReviewRoute.ESCALATE_TO_HUMAN:
            line += f"  reason=({request.escalate_reason()})"
        print(line)
        print(f"    answer: {_short(ex.answer_text)}")

    print("\n=== Audit summary (override rate — feeds H4) ===")
    print(summarize_override_rate(audit.read_all()).summary())
    print(f"\nAudit log written to: {audit.path}")


if __name__ == "__main__":
    main()
