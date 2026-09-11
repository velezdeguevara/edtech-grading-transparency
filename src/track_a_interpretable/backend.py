"""Interpretability backend interface — shared across all three run modes.

The mech-interp analysis and the interp->escalation logic depend ONLY on this
interface, so the exact same analysis code runs in:

  - Mode 1 (artifact):     ArtifactBackend    — no torch, replays precomputed captures
  - Mode 2 (local real):   LocalTorchBackend  — torch + GPT-2-small / Gemma locally
  - Mode 3 (cloud):        LocalTorchBackend  — same, on a cloud GPU (Gemma + SAEs)

See docs/running-modes.md for the full explanation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class InterpSignal:
    """Interpretability evidence about one grading decision on one answer.

    This is the model-agnostic summary the escalation logic consumes. Whether it
    comes from precomputed artifacts (Mode 1) or a live torch model (Modes 2/3),
    the shape is identical.
    """

    # Per-criterion: fraction of the score's causal attribution that fell on
    # content tokens (rubric-relevant) vs. spurious tokens (length/tone/filler).
    # 1.0 = fully content-driven; 0.0 = fully spurious-driven.
    content_attribution: dict[str, float] = field(default_factory=dict)

    # Named spurious features (e.g. "confident_tone", "length") and how strongly
    # they influenced the decision, in [0, 1]. Higher = more spurious influence.
    spurious_feature_activation: dict[str, float] = field(default_factory=dict)

    # Free-form notes for the audit trail / reports.
    notes: str = ""

    def max_spurious(self) -> float:
        return max(self.spurious_feature_activation.values(), default=0.0)

    def min_content_attribution(self) -> float:
        return min(self.content_attribution.values(), default=1.0)


@runtime_checkable
class InterpBackend(Protocol):
    """Supplies interpretability signals for an answer graded against a rubric.

    Implementations must not crash the pipeline: if they cannot produce a signal,
    they should return an empty/neutral ``InterpSignal`` rather than raise.
    """

    name: str
    mode: str  # "artifact" | "local" | "cloud"

    def signal_for(
        self, rubric_id: str, example_id: str, answer_text: str
    ) -> InterpSignal:
        ...
