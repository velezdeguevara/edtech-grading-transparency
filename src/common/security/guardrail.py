"""Security Layer 2 — optional local prompt-injection classifier (optional ML tier).

A small, fast, LOCAL sequence-classification model that flags likely prompt-injection
text. Crucially, this is NOT an "LLM-as-a-judge": using a generative LLM to guard another
LLM is a recursive vulnerability (the attacker just injects the judge). A dedicated
binary classifier only *classifies* (benign vs. injection); it does not follow
instructions in the text, so it is far harder to subvert that way.

Default model: ``protectai/deberta-v3-small-prompt-injection-v2`` (DeBERTa, CPU-friendly).

OPTIONAL and lazy-imported, exactly like the dense retriever: importing this module
never fails without the deps; only *using* it requires them. Install with:
    pip install -r requirements-security.txt

⚠️ HONEST LIMITS (see src/common/security/README.md):
- This is ONE layer, not a solution. Prompt injection is an open problem.
- No accuracy figure is a guarantee — benchmark numbers are on the model's own test
  set, not against novel or adaptive attacks. Classifiers themselves can be evaded
  (adversarial ML).
- A positive detection must ESCALATE TO A HUMAN, never silently finalise a grade. The
  classifier's verdict is advisory input to the human-in-the-loop, not the decision.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    is_injection: bool
    score: float  # model confidence for the predicted label, in [0, 1]
    label: str
    note: str = ""


class InputGuardrail:
    """Lazy-loaded prompt-injection classifier (optional tier)."""

    name = "input-guardrail"

    def __init__(
        self,
        model_name: str = "protectai/deberta-v3-small-prompt-injection-v2",
        threshold: float = 0.5,
    ) -> None:
        self.model_name = model_name
        self.threshold = threshold
        self._classifier = None

    def _ensure_model(self) -> None:
        if self._classifier is not None:
            return
        try:
            from transformers import pipeline
        except ImportError as e:  # pragma: no cover - only without optional deps
            raise RuntimeError(
                "InputGuardrail requires the optional security dependencies. Install "
                "them with `pip install -r requirements-security.txt`. The zero-ML "
                "Layer 1 (sanitize/spotlight) works without any install."
            ) from e
        self._classifier = pipeline(
            "text-classification", model=self.model_name, truncation=True
        )

    def check(self, student_answer: str) -> GuardrailResult:
        """Classify the answer. Returns a GuardrailResult; never raises on normal text.

        Label mapping follows the ProtectAI models: label "INJECTION" (or "1") means an
        injection was detected. A detection should be routed to a human, not used to
        auto-finalise a grade.
        """
        self._ensure_model()
        out = self._classifier(student_answer)[0]  # {"label": ..., "score": ...}
        label = str(out.get("label", "")).upper()
        score = float(out.get("score", 0.0))
        is_injection = label in {"INJECTION", "1", "LABEL_1"} and score >= self.threshold
        return GuardrailResult(
            is_injection=is_injection,
            score=score,
            label=label,
            note="advisory only; escalate to human on detection",
        )
