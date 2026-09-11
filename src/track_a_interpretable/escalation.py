"""Interpretability-driven escalation logic (the functional core of Track A).

This turns an ``InterpSignal`` into an escalation decision: should a proposed grade
be routed to a human because it appears to rely on spurious features (length, tone)
rather than rubric content?

This is the concrete "interpretability is functional, not decoration" mechanism from
docs/design.md, and the basis of hypothesis H3 (interp-based escalation beats a
confidence-only baseline). It is model-agnostic and fully testable offline, because it
consumes only the InterpSignal shape — regardless of which backend produced it.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.track_a_interpretable.backend import InterpSignal


@dataclass(frozen=True)
class EscalationDecision:
    escalate: bool
    reason: str
    max_spurious: float
    min_content_attribution: float


@dataclass(frozen=True)
class EscalationPolicy:
    """Thresholds for interp-based escalation.

    A grade is escalated if EITHER a spurious feature is too influential OR the
    content attribution for any criterion is too low. Defaults are deliberately
    conservative (favouring human review) for a high-stakes grading context.
    """

    max_spurious_threshold: float = 0.5
    min_content_threshold: float = 0.5

    def decide(self, signal: InterpSignal) -> EscalationDecision:
        max_spurious = signal.max_spurious()
        min_content = signal.min_content_attribution()

        reasons = []
        if max_spurious > self.max_spurious_threshold:
            worst = max(
                signal.spurious_feature_activation.items(),
                key=lambda kv: kv[1],
                default=("", 0.0),
            )
            reasons.append(
                f"spurious feature '{worst[0]}'={worst[1]:.2f} "
                f"> {self.max_spurious_threshold:.2f}"
            )
        if min_content < self.min_content_threshold:
            reasons.append(
                f"min content attribution {min_content:.2f} "
                f"< {self.min_content_threshold:.2f}"
            )

        return EscalationDecision(
            escalate=bool(reasons),
            reason="; ".join(reasons) if reasons else "content-driven; no escalation",
            max_spurious=max_spurious,
            min_content_attribution=min_content,
        )


def confidence_only_decision(
    min_confidence: float, threshold: float = 0.6
) -> EscalationDecision:
    """Baseline escalation using only the grader's own confidence (no interp).

    Used to test H3: does interp-based escalation outperform confidence-only?
    """
    escalate = min_confidence < threshold
    return EscalationDecision(
        escalate=escalate,
        reason=(
            f"confidence {min_confidence:.2f} < {threshold:.2f}"
            if escalate
            else "confident enough; no escalation"
        ),
        max_spurious=float("nan"),
        min_content_attribution=float("nan"),
    )
