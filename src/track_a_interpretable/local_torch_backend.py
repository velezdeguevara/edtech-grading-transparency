"""Modes 2 & 3 backend: real mechanistic interpretability via torch + TransformerLens.

This backend produces InterpSignals from a live model. It is written so the MODULE
imports cleanly even when torch/transformer_lens are absent (imports are lazy inside
methods), so it never breaks Mode 1. The heavy work runs only when actually used in a
torch-capable environment.

Model selection (env ``INTERP_MODEL``, default ``gpt2``):
  - ``gpt2``       — GPT-2-small; fits any machine, CPU ok. For developing/validating
                     the interpretability pipeline (too weak to grade well).
  - ``gemma-2-2b`` — the real target model; needs a GPU / ample RAM and a Hugging Face
                     license + token (see docs/running-modes.md).

The actual technique implementations (logit lens, activation patching, attention
analysis, SAE feature reads) live under ``interpretability/`` and are wired in as they
land; here they are represented as clearly-marked stubs so the seam is explicit.
"""

from __future__ import annotations

import os

from src.track_a_interpretable.backend import InterpSignal


class LocalTorchBackend:
    name = "local-torch-backend"

    def __init__(self, mode: str = "local", model_name: str | None = None) -> None:
        self.mode = mode  # "local" or "cloud"
        self.model_name = model_name or os.environ.get("INTERP_MODEL", "gpt2")
        self._model = None  # lazily loaded

    def _ensure_model(self) -> None:
        """Load the model on first use. Raises a clear error if deps are missing."""
        if self._model is not None:
            return
        try:
            import torch  # noqa: F401
            from transformer_lens import HookedTransformer
        except ImportError as e:  # pragma: no cover - exercised only without deps
            raise RuntimeError(
                "LocalTorchBackend requires torch + transformer_lens. Install them with "
                "`pip install -r requirements-interp.txt` in a torch-capable environment, "
                "or use Mode 1 (INTERP_MODE=artifact)."
            ) from e
        self._model = HookedTransformer.from_pretrained(self.model_name)

    def signal_for(
        self, rubric_id: str, example_id: str, answer_text: str
    ) -> InterpSignal:
        """Produce an InterpSignal from live-model interpretability.

        STUB: the real implementation will run the ``interpretability/`` techniques
        (activation patching for content vs. spurious attribution, attention analysis,
        SAE feature reads) and summarise them into the InterpSignal. It is intentionally
        not implemented until those modules land, so that this seam is explicit and the
        cloud notebook can wire them in and export artifacts for Mode 1.
        """
        self._ensure_model()
        raise NotImplementedError(
            "Real mech-interp signal extraction is wired in as the interpretability/ "
            "technique modules land. Until then use Mode 1 (artifact) for a runnable "
            "end-to-end pipeline."
        )
