"""Shared, model-agnostic data models for the grading study.

These types define the contract that BOTH tracks (interpretable open-weight and
explainable frontier) must satisfy, so the ``evals`` harness can score them
identically. Nothing here depends on a specific model or vendor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CriterionOutcome(str, Enum):
    """Whether a single rubric criterion was satisfied by an answer."""

    MET = "met"
    PARTIAL = "partial"
    NOT_MET = "not_met"


@dataclass(frozen=True)
class RubricCriterion:
    """One scorable criterion within a rubric.

    ``max_points`` is awarded for MET, half (rounded) for PARTIAL, zero for NOT_MET.
    """

    id: str
    description: str
    max_points: int

    def points_for(self, outcome: CriterionOutcome) -> float:
        if outcome is CriterionOutcome.MET:
            return float(self.max_points)
        if outcome is CriterionOutcome.PARTIAL:
            return self.max_points / 2.0
        return 0.0


@dataclass(frozen=True)
class Rubric:
    """A full rubric for one question."""

    id: str
    question: str
    criteria: tuple[RubricCriterion, ...]

    @property
    def max_total(self) -> float:
        return float(sum(c.max_points for c in self.criteria))


@dataclass(frozen=True)
class CriterionAssessment:
    """A grader's judgement on one criterion, with evidence for explainability."""

    criterion_id: str
    outcome: CriterionOutcome
    evidence_span: str  # quoted text from the student's answer supporting the outcome
    confidence: float = 1.0  # 0.0-1.0; feeds calibration + escalation


@dataclass(frozen=True)
class ProposedGrade:
    """A grader's structured proposal for one student answer.

    The tool PROPOSES; a teacher must approve/override (human-in-the-loop).
    The grade is decomposable into per-criterion assessments so it is inspectable.
    """

    rubric_id: str
    assessments: tuple[CriterionAssessment, ...]
    # Optional signal from Track A interpretability: True means the grade appears to
    # rely on spurious features and should be escalated regardless of confidence.
    spurious_reliance_flag: bool = False
    notes: str = ""

    def total_points(self, rubric: Rubric) -> float:
        by_id = {c.id: c for c in rubric.criteria}
        return sum(
            by_id[a.criterion_id].points_for(a.outcome)
            for a in self.assessments
            if a.criterion_id in by_id
        )

    def min_confidence(self) -> float:
        return min((a.confidence for a in self.assessments), default=1.0)


@dataclass(frozen=True)
class GradedExample:
    """A fixture: a student answer plus the teacher's ground-truth grade.

    ``teacher_outcomes`` maps criterion_id -> CriterionOutcome (the ground truth).
    Fixtures are SYNTHETIC. No real student data.
    """

    id: str
    rubric_id: str
    answer_text: str
    teacher_outcomes: dict[str, CriterionOutcome] = field(default_factory=dict)

    def teacher_total(self, rubric: Rubric) -> float:
        by_id = {c.id: c for c in rubric.criteria}
        return sum(
            by_id[cid].points_for(outcome)
            for cid, outcome in self.teacher_outcomes.items()
            if cid in by_id
        )


class Grader:
    """Model-agnostic grader interface. Both tracks implement ``grade``.

    Implementations live in ``src/track_a_interpretable`` and
    ``src/track_b_explainable``. The evals harness only depends on this contract.
    """

    name: str = "abstract-grader"

    def grade(self, rubric: Rubric, answer_text: str) -> ProposedGrade:  # pragma: no cover
        raise NotImplementedError
