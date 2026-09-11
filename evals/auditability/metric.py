"""Escalation eval: does interpretability-based escalation beat confidence-only? (H3)

For each example we know (from the fixtures' ``probe`` annotations and teacher
grades) whether a grade *should* be escalated to a human — specifically, the
spurious-feature probe ex04 (long/confident/empty) SHOULD escalate, while a
content-driven answer such as ex05 (short/correct) should NOT.

This eval runs the Track A interpretable grader and compares:
  - interp-based escalation (uses the InterpSignal), vs.
  - a confidence-only baseline (uses only the grader's own confidence).

against the ground-truth "should_escalate" labels, reporting precision/recall so H3
can be evaluated. Model-agnostic: works with any InterpBackend (artifact/local/cloud).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.common.grading.schema import GradedExample, Rubric
from src.track_a_interpretable.escalation import confidence_only_decision
from src.track_a_interpretable.grader import InterpretableGrader

# Ground-truth escalation labels for the WWI fixtures. True = a human SHOULD review,
# because the correct grade depends on judgement the automated grader is at risk of
# getting for the wrong reasons (the spurious-feature probes).
SHOULD_ESCALATE: dict[str, bool] = {
    "ex01-strong": False,
    "ex02-partial-no-economic": False,
    "ex03-weak-assertion": True,  # borderline/assertive -> worth a human look
    "ex04-long-but-confident-empty": True,  # spurious length/tone -> must escalate
    "ex05-short-but-correct": False,  # content-driven -> should NOT be escalated
    "ex06-economic-focus": False,
}


@dataclass
class _Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    def add(self, predicted: bool, truth: bool) -> None:
        if predicted and truth:
            self.tp += 1
        elif predicted and not truth:
            self.fp += 1
        elif not predicted and truth:
            self.fn += 1
        else:
            self.tn += 1

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def accuracy(self) -> float:
        d = self.tp + self.fp + self.fn + self.tn
        return (self.tp + self.tn) / d if d else 0.0


@dataclass
class EscalationEvalResult:
    grader_name: str
    rubric_id: str
    interp: _Counts = field(default_factory=_Counts)
    confidence_only: _Counts = field(default_factory=_Counts)

    def summary(self) -> str:
        return (
            f"[{self.grader_name} on {self.rubric_id}] escalation (H3)\n"
            f"  interp-based    : precision={self.interp.precision:.2f} "
            f"recall={self.interp.recall:.2f} acc={self.interp.accuracy:.2f}\n"
            f"  confidence-only : precision={self.confidence_only.precision:.2f} "
            f"recall={self.confidence_only.recall:.2f} acc={self.confidence_only.accuracy:.2f}"
        )


def evaluate_escalation(
    grader: InterpretableGrader,
    rubric: Rubric,
    examples: list[GradedExample],
    confidence_threshold: float = 0.6,
) -> EscalationEvalResult:
    result = EscalationEvalResult(grader_name=grader.name, rubric_id=rubric.id)
    for ex in examples:
        truth = SHOULD_ESCALATE.get(ex.id, False)

        graded, decision = grader.grade_example(rubric, ex.id, ex.answer_text)
        result.interp.add(decision.escalate, truth)

        conf_decision = confidence_only_decision(
            graded.min_confidence(), threshold=confidence_threshold
        )
        result.confidence_only.add(conf_decision.escalate, truth)

    return result
