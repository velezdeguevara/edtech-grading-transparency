"""Track A grader: grading + interpretability-driven escalation.

Track A pairs a base grader (any ``Grader``) with an ``InterpBackend`` and the
escalation policy. When the interpretability signal shows the grade relies on
spurious features, the resulting ``ProposedGrade`` is flagged
(``spurious_reliance_flag=True``) so the human-review layer escalates it.

This is what makes interpretability *functional* in Track A: it changes the
runtime trust decision. In Mode 1 the interp signal comes from precomputed
artifacts; in Modes 2/3 from a live model — the grader code is identical.

Note: ``grade`` requires an example_id to look up the interp signal, so Track A is
scored through :meth:`grade_example`, which the evals harness can call. The base
``Grader.grade`` is kept for interface compatibility (no interp, no escalation).
"""

from __future__ import annotations

from dataclasses import replace

from src.common.grading.keyword_baseline import KeywordBaselineGrader
from src.common.grading.schema import Grader, ProposedGrade, Rubric
from src.track_a_interpretable.backend import InterpBackend
from src.track_a_interpretable.capability import get_backend
from src.track_a_interpretable.escalation import EscalationDecision, EscalationPolicy


class InterpretableGrader(Grader):
    name = "track-a-interpretable"

    def __init__(
        self,
        base_grader: Grader | None = None,
        backend: InterpBackend | None = None,
        policy: EscalationPolicy | None = None,
    ) -> None:
        # Base grader is pluggable; defaults to the keyword baseline so Track A runs
        # end-to-end offline. A real open-weight model grader slots in here later.
        self.base_grader = base_grader or KeywordBaselineGrader()
        self.backend = backend or get_backend()
        self.policy = policy or EscalationPolicy()
        self.name = f"track-a-interpretable[{self.backend.mode}]"

    def grade(self, rubric: Rubric, answer_text: str) -> ProposedGrade:
        # Interface-compatible path: no example_id, so no interp lookup/escalation.
        return self.base_grader.grade(rubric, answer_text)

    def grade_example(
        self, rubric: Rubric, example_id: str, answer_text: str
    ) -> tuple[ProposedGrade, EscalationDecision]:
        """Grade with interpretability-driven escalation.

        Returns the (possibly flagged) grade and the escalation decision, so reports
        and the human-review layer can act on and audit it.
        """
        base = self.base_grader.grade(rubric, answer_text)
        signal = self.backend.signal_for(rubric.id, example_id, answer_text)
        decision = self.policy.decide(signal)
        graded = replace(base, spurious_reliance_flag=decision.escalate)
        return graded, decision
