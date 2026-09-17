"""Comparison write-up — audience: **product owner**.

Runs the full eval suite offline (Mode 1) and lays the results out so a product owner
can weigh the two tracks and the escalation story:

  - Agreement / Calibration / Bias-fairness for the keyword **baseline** (the floor).
  - The H3 escalation head-to-head: interpretability-driven vs. confidence-only.
  - Robustness (baseline base grade vs. Track A escalation-catch) per attack category.

Honesty framing is explicit: the baseline is a floor, not a promise; robustness is
known-attack resistance, not a guarantee; genuine Track A numbers depend on a real
Mode 3 run (placeholder artifacts otherwise); genuine Track B numbers depend on a
live API run (the offline provider is a mock).
"""

from __future__ import annotations

from evals.agreement.metric import evaluate_agreement
from evals.auditability.metric import evaluate_escalation
from evals.bias_fairness.metric import evaluate_bias_fairness
from evals.calibration.metric import evaluate_calibration
from evals.robustness.metric import evaluate_robustness
from src.common.grading.keyword_baseline import KeywordBaselineGrader
from src.common.reporting.common import (
    BASELINE_FLOOR_BANNER,
    DEFENCE_IN_DEPTH_BANNER,
    PLACEHOLDER_BANNER,
    Report,
    h1,
    h2,
    join_sections,
    pct,
    provenance_line,
    table,
)
from src.common.rubrics.loader import (
    load_adversarial_fixtures,
    load_fixtures,
    load_rubric,
)
from src.track_a_interpretable.grader import InterpretableGrader

FILENAME = "track-comparison.md"
RUBRIC_ID = "ss-wwi-causes-v1"


def build_comparison_report(rubric_id: str = RUBRIC_ID) -> Report:
    rubric = load_rubric(rubric_id)
    examples = load_fixtures(rubric_id)
    adversarial = load_adversarial_fixtures(rubric_id)

    baseline = KeywordBaselineGrader()
    track_a = InterpretableGrader()  # artifact backend in Mode 1

    agreement = evaluate_agreement(baseline, rubric, examples)
    calibration = evaluate_calibration(baseline, rubric, examples)
    bias = evaluate_bias_fairness(baseline, rubric, examples)
    escalation = evaluate_escalation(track_a, rubric, examples)
    robustness = evaluate_robustness(track_a, rubric, adversarial)

    quality_tbl = table(
        ["Dimension", "Baseline (floor)", "Reading"],
        [
            [
                "Agreement (criterion acc)",
                pct(agreement.criterion_accuracy),
                f"exact-score {pct(agreement.exact_score_rate)}, "
                f"MAE {agreement.mean_abs_point_error:.2f} pts",
            ],
            [
                "Calibration (ECE)",
                f"{calibration.ece:.3f}",
                "lower is better; 0 = perfectly calibrated",
            ],
            [
                "Bias (spurious sensitivity)",
                f"{bias.mean_spurious_sensitivity:.2f} pts",
                "0 = fair; higher = more length/tone sensitivity",
            ],
        ],
    )

    escalation_tbl = table(
        ["Escalation strategy", "Precision", "Recall", "Accuracy"],
        [
            [
                "Interpretability-driven (Track A)",
                f"{escalation.interp.precision:.2f}",
                f"{escalation.interp.recall:.2f}",
                f"{escalation.interp.accuracy:.2f}",
            ],
            [
                "Confidence-only (baseline)",
                f"{escalation.confidence_only.precision:.2f}",
                f"{escalation.confidence_only.recall:.2f}",
                f"{escalation.confidence_only.accuracy:.2f}",
            ],
        ],
    )
    interp_wins = escalation.interp.accuracy > escalation.confidence_only.accuracy
    escalation_verdict = (
        "Interpretability-driven escalation **outperforms** the confidence-only "
        "baseline on accuracy here"
        if interp_wins
        else "Interpretability-driven escalation does **not** beat confidence-only here"
    ) + " — this is the H3 signal (illustrative while artifacts are placeholders)."

    robustness_rows = []
    for cat in sorted(robustness.by_category):
        s = robustness.by_category[cat]
        robustness_rows.append(
            [
                cat,
                str(s.n),
                pct(1 - s.fooled_rate),
                pct(s.escalation_catch_rate),
            ]
        )
    robustness_tbl = table(
        ["Attack category", "n", "Base resistance", "Track A escalation-catch"],
        robustness_rows,
    )

    body = join_sections(
        [
            h1("Track Comparison — Interpretable (A) vs. Explainable (B)"),
            provenance_line("product owner"),
            (
                "The central question: is it affordable to be *interpretable by design* "
                "(Track A), or better to make a non-interpretable frontier model "
                "trustworthy via explainability + rubrics + RAG + human-in-the-loop "
                "(Track B)? This write-up gives the offline, reproducible evidence "
                "available today."
            ),
            BASELINE_FLOOR_BANNER,
            h2("Grade quality (baseline floor)"),
            (
                "These three dimensions are scored on the naive keyword baseline as the "
                "floor both real graders must beat."
            ),
            quality_tbl,
            h2("Escalation head-to-head (H3)"),
            PLACEHOLDER_BANNER,
            escalation_tbl,
            escalation_verdict,
            h2("Robustness by attack category (defence-in-depth)"),
            DEFENCE_IN_DEPTH_BANNER,
            (
                "'Base resistance' is whether the base grade avoided being inflated; "
                "'Track A escalation-catch' is whether interpretability-driven "
                "escalation flagged the attack for a human even when the base grade was "
                "fooled. The second column is the defence-in-depth story."
            ),
            robustness_tbl,
            h2("What is still owed"),
            (
                "- **Genuine Track A numbers** require a Mode 3 cloud run to replace the "
                "placeholder interpretability artifacts.\n"
                "- **Genuine Track B numbers** require a live API run; the offline "
                "provider is a mock and is intentionally excluded from the tables above "
                "to avoid presenting mock output as a result.\n"
                "- No figure here is a production-accuracy promise."
            ),
        ]
    )
    return Report(
        title="Track Comparison", filename=FILENAME, body=body
    )
