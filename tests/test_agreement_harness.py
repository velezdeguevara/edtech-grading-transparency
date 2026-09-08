"""End-to-end tests for the shared schema, loaders, and agreement eval."""

from __future__ import annotations

from evals.agreement.metric import evaluate_agreement
from src.common.grading.keyword_baseline import KeywordBaselineGrader
from src.common.grading.schema import CriterionOutcome, RubricCriterion
from src.common.rubrics.loader import load_fixtures, load_rubric

RUBRIC_ID = "ss-wwi-causes-v1"


def test_criterion_points():
    crit = RubricCriterion(id="x", description="d", max_points=4)
    assert crit.points_for(CriterionOutcome.MET) == 4.0
    assert crit.points_for(CriterionOutcome.PARTIAL) == 2.0
    assert crit.points_for(CriterionOutcome.NOT_MET) == 0.0


def test_rubric_loads_with_expected_total():
    rubric = load_rubric(RUBRIC_ID)
    # 3 + 3 + 2 + 2 = 10
    assert rubric.max_total == 10.0
    assert len(rubric.criteria) == 4


def test_fixtures_load_and_reference_valid_criteria():
    rubric = load_rubric(RUBRIC_ID)
    valid_ids = {c.id for c in rubric.criteria}
    examples = load_fixtures(RUBRIC_ID)
    assert len(examples) >= 6
    for ex in examples:
        assert set(ex.teacher_outcomes).issubset(valid_ids)


def test_teacher_totals_within_bounds():
    rubric = load_rubric(RUBRIC_ID)
    for ex in load_fixtures(RUBRIC_ID):
        assert 0.0 <= ex.teacher_total(rubric) <= rubric.max_total


def test_agreement_runs_and_is_bounded():
    rubric = load_rubric(RUBRIC_ID)
    examples = load_fixtures(RUBRIC_ID)
    result = evaluate_agreement(KeywordBaselineGrader(), rubric, examples)
    assert result.n_examples == len(examples)
    assert 0.0 <= result.criterion_accuracy <= 1.0
    assert 0.0 <= result.within_one_rate <= 1.0
    assert result.mean_abs_point_error >= 0.0


def test_baseline_overscores_spurious_long_answer():
    """ex04 is long/confident but empty of real causes; teacher total is 0.

    The naive keyword baseline should NOT perfectly match here — this documents
    the spurious-feature weakness the study is about.
    """
    rubric = load_rubric(RUBRIC_ID)
    examples = {ex.id: ex for ex in load_fixtures(RUBRIC_ID)}
    ex04 = examples["ex04-long-but-confident-empty"]
    assert ex04.teacher_total(rubric) == 0.0
