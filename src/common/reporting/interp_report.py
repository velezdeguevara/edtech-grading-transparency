"""Interp-findings report — audience: **researcher**.

Presents the Track A interpretability results: per-example content-attribution vs.
spurious-feature activation, the escalation decision each signal drives, and the H3
head-to-head (interp-based vs. confidence-only escalation).

This report is **placeholder-labelled** whenever the underlying artifacts are
synthetic (the default until a Mode 3 cloud run). The pipeline, signals, and
escalation logic are real and exercised here; only the *captures* are placeholders.
It writes to ``reports/interp-findings/`` (its own subdirectory) to sit alongside
future real captures.
"""

from __future__ import annotations

from evals.auditability.metric import SHOULD_ESCALATE, evaluate_escalation
from src.common.reporting.common import (
    PLACEHOLDER_BANNER,
    Report,
    h1,
    h2,
    join_sections,
    provenance_line,
    table,
)
from src.common.rubrics.loader import load_fixtures, load_rubric
from src.track_a_interpretable.artifact_backend import ArtifactBackend
from src.track_a_interpretable.escalation import EscalationPolicy
from src.track_a_interpretable.grader import InterpretableGrader

FILENAME = "interp-findings/interp-findings.md"
RUBRIC_ID = "ss-wwi-causes-v1"


def build_interp_findings_report(rubric_id: str = RUBRIC_ID) -> Report:
    rubric = load_rubric(rubric_id)
    examples = load_fixtures(rubric_id)

    backend = ArtifactBackend()
    is_placeholder = backend.is_placeholder(rubric_id)
    policy = EscalationPolicy()

    # Per-example interpretability signals + the escalation decision they drive.
    signal_rows = []
    for ex in examples:
        signal = backend.signal_for(rubric_id, ex.id, ex.answer_text)
        decision = policy.decide(signal)
        signal_rows.append(
            [
                ex.id,
                f"{signal.min_content_attribution():.2f}",
                f"{signal.max_spurious():.2f}",
                "escalate" if decision.escalate else "auto",
                "yes" if SHOULD_ESCALATE.get(ex.id, False) else "no",
            ]
        )
    signal_tbl = table(
        [
            "Example",
            "Min content attribution",
            "Max spurious activation",
            "Decision",
            "Should escalate?",
        ],
        signal_rows,
    )

    # H3 head-to-head.
    grader = InterpretableGrader(backend=backend, policy=policy)
    escalation = evaluate_escalation(grader, rubric, examples)
    h3_tbl = table(
        ["Strategy", "Precision", "Recall", "Accuracy"],
        [
            [
                "Interpretability-driven",
                f"{escalation.interp.precision:.2f}",
                f"{escalation.interp.recall:.2f}",
                f"{escalation.interp.accuracy:.2f}",
            ],
            [
                "Confidence-only",
                f"{escalation.confidence_only.precision:.2f}",
                f"{escalation.confidence_only.recall:.2f}",
                f"{escalation.confidence_only.accuracy:.2f}",
            ],
        ],
    )
    interp_wins = escalation.interp.accuracy > escalation.confidence_only.accuracy

    sections = [
        h1("Interpretability Findings (Track A)"),
        provenance_line("researcher", extra=f"Backend: {backend.mode}."),
    ]
    if is_placeholder:
        sections.append(PLACEHOLDER_BANNER)
    sections.extend(
        [
            (
                "Track A's claim is that interpretability is *functional*: the interp "
                "signal changes the runtime trust decision (escalate vs. auto-accept). "
                "Below, each example's grade is characterised by how much its "
                "attribution fell on rubric content vs. spurious features, and the "
                "escalation decision that signal drives."
            ),
            h2("Per-example signals and escalation decisions"),
            (
                "'Min content attribution' is the lowest per-criterion content share; "
                "'max spurious activation' is the strongest spurious feature. The "
                "escalation policy escalates when content is too low or a spurious "
                "feature too strong. The final column is the ground-truth label used "
                "for H3 scoring."
            ),
            signal_tbl,
            h2("H3: interp-based vs. confidence-only escalation"),
            h3_tbl,
            (
                "Interpretability-driven escalation "
                + ("**beats**" if interp_wins else "does **not** beat")
                + " the confidence-only baseline on accuracy over these fixtures. "
                "This is the concrete demonstration that interpretability is functional"
                + (
                    " — illustrative only until real captures replace the placeholders."
                    if is_placeholder
                    else "."
                )
            ),
            h2("Techniques (planned for Mode 3)"),
            (
                "The genuine captures will come from Gemma-2-2b + Gemma Scope SAEs via "
                "`interpretability/cloud_gemma_scope.ipynb`, using logit lens, activation "
                "patching, attention analysis, and SAE feature attribution. Those "
                "techniques are documented/planned; this report replays their "
                "precomputed outputs."
            ),
        ]
    )
    return Report(
        title="Interpretability Findings (Track A)",
        filename=FILENAME,
        body=join_sections(sections),
    )
