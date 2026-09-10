"""Tests for the calibration and bias-fairness evals."""

from __future__ import annotations

from evals.bias_fairness.metric import evaluate_bias_fairness
from evals.calibration.metric import _bin_index, evaluate_calibration
from src.common.grading.keyword_baseline import KeywordBaselineGrader
from src.common.rubrics.loader import load_fixtures, load_rubric

RUBRIC_ID = "ss-wwi-causes-v1"


def _rubric_and_examples():
    return load_rubric(RUBRIC_ID), load_fixtures(RUBRIC_ID)


# --- Calibration ---

def test_bin_index_bounds():
    assert _bin_index(0.0, 5) == 0
    assert _bin_index(1.0, 5) == 4  # top edge falls in last bin
    assert _bin_index(0.5, 5) == 2
    assert _bin_index(-1.0, 5) == 0  # clamped
    assert _bin_index(2.0, 5) == 4  # clamped


def test_calibration_runs_and_ece_bounded():
    rubric, examples = _rubric_and_examples()
    result = evaluate_calibration(KeywordBaselineGrader(), rubric, examples, n_bins=5)
    assert result.n_assessments == len(examples) * len(rubric.criteria)
    assert 0.0 <= result.ece <= 1.0
    # Every assessment should land in exactly one bin.
    assert sum(b.count for b in result.bins) == result.n_assessments


def test_calibration_bin_accuracy_bounded():
    rubric, examples = _rubric_and_examples()
    result = evaluate_calibration(KeywordBaselineGrader(), rubric, examples)
    for b in result.bins:
        assert 0.0 <= b.accuracy <= 1.0
        assert 0.0 <= b.mean_confidence <= 1.0


# --- Bias / fairness ---

def test_bias_fairness_runs_and_reports_probes():
    rubric, examples = _rubric_and_examples()
    result = evaluate_bias_fairness(KeywordBaselineGrader(), rubric, examples)
    probe_ids = {p.example_id for p in result.probes}
    assert "ex04-long-but-confident-empty" in probe_ids
    assert "ex05-short-but-correct" in probe_ids


def test_contrast_pair_difference_nonnegative():
    rubric, examples = _rubric_and_examples()
    result = evaluate_bias_fairness(KeywordBaselineGrader(), rubric, examples)
    assert result.mean_spurious_sensitivity >= 0.0
    for cp in result.contrast_pairs:
        assert cp.abs_difference >= 0.0


def test_custom_contrast_pair_identical_answers_is_fair():
    """Two identical answers must produce zero spurious sensitivity."""
    rubric, examples = _rubric_and_examples()
    same = "Alliances and nationalism, the arms race and Schlieffen Plan, colonial rivalry."
    result = evaluate_bias_fairness(
        KeywordBaselineGrader(),
        rubric,
        examples,
        contrast_pairs=[("identical", same, same)],
    )
    identical = [cp for cp in result.contrast_pairs if cp.label == "identical"][0]
    assert identical.abs_difference == 0.0
