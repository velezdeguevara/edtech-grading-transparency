"""Runnable harness: score a grader against teacher ground truth.

Usage (from repo root):
    python -m evals.run_agreement

Currently runs the KeywordBaselineGrader as a smoke test / baseline. Track A and
Track B graders plug in by implementing the same ``Grader`` interface and being
passed here in place of the baseline.
"""

from __future__ import annotations

from evals.agreement.metric import evaluate_agreement
from src.common.grading.keyword_baseline import KeywordBaselineGrader
from src.common.grading.schema import Grader
from src.common.rubrics.loader import load_fixtures, load_rubric

RUBRIC_ID = "ss-wwi-causes-v1"


def run(grader: Grader, rubric_id: str = RUBRIC_ID) -> None:
    rubric = load_rubric(rubric_id)
    examples = load_fixtures(rubric_id)
    result = evaluate_agreement(grader, rubric, examples)
    print(result.summary())


def main() -> None:
    print("=== Agreement eval ===")
    run(KeywordBaselineGrader())
    print(
        "\nNote: baseline is intentionally naive. Fixtures ex04 (long/confident/empty) "
        "and ex05 (short/correct) probe spurious length/tone grading."
    )


if __name__ == "__main__":
    main()
