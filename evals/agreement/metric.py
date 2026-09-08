"""Agreement metric: how well a grader matches teacher ground-truth grades.

This is the first eval and the template for the others. It is model-agnostic: it
scores any object implementing the ``Grader`` interface, so Track A and Track B
are measured identically on the same items.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.grading.schema import GradedExample, Grader, Rubric


@dataclass
class AgreementResult:
    grader_name: str
    rubric_id: str
    n_examples: int
    n_criteria: int
    # Per-criterion outcome agreement (exact match on met/partial/not_met).
    criterion_exact_matches: int
    # Total-score agreement.
    exact_score_matches: int  # proposed total == teacher total
    within_one_matches: int  # |proposed total - teacher total| <= 1
    mean_abs_point_error: float

    @property
    def criterion_accuracy(self) -> float:
        total = self.n_examples * self.n_criteria
        return self.criterion_exact_matches / total if total else 0.0

    @property
    def exact_score_rate(self) -> float:
        return self.exact_score_matches / self.n_examples if self.n_examples else 0.0

    @property
    def within_one_rate(self) -> float:
        return self.within_one_matches / self.n_examples if self.n_examples else 0.0

    def summary(self) -> str:
        return (
            f"[{self.grader_name} on {self.rubric_id}] "
            f"criterion_acc={self.criterion_accuracy:.2%}  "
            f"exact_score={self.exact_score_rate:.2%}  "
            f"within_1={self.within_one_rate:.2%}  "
            f"MAE={self.mean_abs_point_error:.2f} pts  "
            f"(n={self.n_examples})"
        )


def evaluate_agreement(
    grader: Grader, rubric: Rubric, examples: list[GradedExample]
) -> AgreementResult:
    n_criteria = len(rubric.criteria)
    criterion_exact = 0
    exact_score = 0
    within_one = 0
    abs_err_sum = 0.0

    for ex in examples:
        proposed = grader.grade(rubric, ex.answer_text)
        proposed_by_id = {a.criterion_id: a.outcome for a in proposed.assessments}

        for crit in rubric.criteria:
            if proposed_by_id.get(crit.id) == ex.teacher_outcomes.get(crit.id):
                criterion_exact += 1

        p_total = proposed.total_points(rubric)
        t_total = ex.teacher_total(rubric)
        diff = abs(p_total - t_total)
        abs_err_sum += diff
        if diff == 0:
            exact_score += 1
        if diff <= 1:
            within_one += 1

    n = len(examples)
    return AgreementResult(
        grader_name=grader.name,
        rubric_id=rubric.id,
        n_examples=n,
        n_criteria=n_criteria,
        criterion_exact_matches=criterion_exact,
        exact_score_matches=exact_score,
        within_one_matches=within_one,
        mean_abs_point_error=(abs_err_sum / n if n else 0.0),
    )
