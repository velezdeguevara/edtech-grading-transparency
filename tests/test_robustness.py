"""Tests for the robustness eval and adversarial fixtures."""

from __future__ import annotations

from evals.robustness.metric import evaluate_robustness
from src.common.grading.keyword_baseline import KeywordBaselineGrader
from src.common.rubrics.loader import (
    load_adversarial_fixtures,
    load_rubric,
)
from src.track_a_interpretable.artifact_backend import ArtifactBackend
from src.track_a_interpretable.grader import InterpretableGrader

RUBRIC_ID = "ss-wwi-causes-v1"


def _rubric_and_adv():
    return load_rubric(RUBRIC_ID), load_adversarial_fixtures(RUBRIC_ID)


def test_adversarial_fixtures_load_with_attack_types():
    _, adv = _rubric_and_adv()
    assert len(adv) >= 20
    # Multiple distinct attack categories represented (taxonomy coverage).
    categories = {a.attack_type for a in adv}
    assert len(categories) >= 8
    for a in adv:
        assert a.attack_type


def test_adversarial_teacher_totals_are_low():
    """Adversarial answers' CORRECT grade is low (little/no real content)."""
    rubric, adv = _rubric_and_adv()
    for a in adv:
        # At most one criterion legitimately met (the mixed cases); total stays low.
        assert a.example.teacher_total(rubric) <= rubric.max_total / 2


def test_robustness_metric_runs_and_is_bounded():
    rubric, adv = _rubric_and_adv()
    result = evaluate_robustness(KeywordBaselineGrader(), rubric, adv)
    assert result.n == len(adv)
    assert 0.0 <= result.fooled_rate <= 1.0
    assert 0.0 <= result.resistance_rate <= 1.0
    assert result.mean_overscore >= 0.0
    # Every attack maps to a category bucket.
    assert sum(s.n for s in result.by_category.values()) == result.n


def test_keyword_baseline_is_fooled_by_keyword_stuffing():
    """Documents the expected weakness: a keyword grader is gamed by stuffed keywords."""
    rubric, adv = _rubric_and_adv()
    result = evaluate_robustness(KeywordBaselineGrader(), rubric, adv)
    ks = result.by_category.get("keyword_stuffing")
    assert ks is not None
    assert ks.fooled >= 1  # fooled on at least one stuffing attack


def test_baseline_result_has_no_escalation_column():
    rubric, adv = _rubric_and_adv()
    result = evaluate_robustness(KeywordBaselineGrader(), rubric, adv)
    assert result.track_a_escalation is False


def test_track_a_escalation_catches_adversarial_cases():
    """Defence-in-depth: even when the base grade is fooled, Track A escalates.

    Uses the artifact backend (Mode 1, placeholder signals) which carries adversarial
    signals with high spurious activation / low content attribution.
    """
    rubric, adv = _rubric_and_adv()
    grader = InterpretableGrader(backend=ArtifactBackend())
    result = evaluate_robustness(grader, rubric, adv)
    assert result.track_a_escalation is True
    # With the shipped placeholder artifacts, escalation catches every adversarial case.
    total_escalated = sum(s.escalated for s in result.by_category.values())
    assert total_escalated == result.n
