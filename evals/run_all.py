"""Runnable harness: run all evals for a grader against teacher ground truth.

Usage (from repo root):
    python -m evals.run_all

Runs agreement, calibration, and bias-fairness for the KeywordBaselineGrader as a
smoke test / baseline, then runs the Track A interpretable grader's escalation eval
(H3). Any grader implementing the ``Grader`` interface (Track A or Track B) can be
swapped in.
"""

from __future__ import annotations

from evals.agreement.metric import evaluate_agreement
from evals.auditability.metric import evaluate_escalation
from evals.bias_fairness.metric import evaluate_bias_fairness
from evals.calibration.metric import evaluate_calibration
from src.common.grading.keyword_baseline import KeywordBaselineGrader
from src.common.grading.schema import Grader
from src.common.rubrics.loader import load_fixtures, load_rubric
from src.track_a_interpretable.grader import InterpretableGrader

RUBRIC_ID = "ss-wwi-causes-v1"


def run_all(grader: Grader, rubric_id: str = RUBRIC_ID) -> None:
    rubric = load_rubric(rubric_id)
    examples = load_fixtures(rubric_id)

    print("--- Agreement ---")
    print(evaluate_agreement(grader, rubric, examples).summary())

    print("\n--- Calibration ---")
    print(evaluate_calibration(grader, rubric, examples).summary())

    print("\n--- Bias / fairness ---")
    print(evaluate_bias_fairness(grader, rubric, examples).summary())


def run_escalation(rubric_id: str = RUBRIC_ID) -> None:
    """Track A: interpretability-driven escalation vs. confidence-only baseline (H3)."""
    rubric = load_rubric(rubric_id)
    examples = load_fixtures(rubric_id)
    grader = InterpretableGrader()  # uses detected backend (artifact in Mode 1)
    print(f"\n--- Escalation / auditability (backend: {grader.backend.mode}) ---")
    print(evaluate_escalation(grader, rubric, examples).summary())


def main() -> None:
    print("=== Full eval suite (baseline grader) ===\n")
    run_all(KeywordBaselineGrader())
    run_escalation()
    print(
        "\nBaseline is intentionally naive; results establish a floor the real "
        "Track A / Track B graders must beat."
    )


if __name__ == "__main__":
    main()
