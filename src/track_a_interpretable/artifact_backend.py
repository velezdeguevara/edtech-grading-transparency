"""Mode 1 backend: replay precomputed interpretability artifacts (no torch).

Reads small artifact files from ``data/interp_artifacts/<rubric_id>.artifacts.json``
and returns the stored ``InterpSignal`` for each example. This lets any laptop run
the mech-interp analysis + escalation logic with no model, no GPU, no torch.

Until a real Mode 3 run overwrites them, the shipped artifacts are clearly labelled
synthetic placeholders (see the "placeholder" flag in the JSON). The backend exposes
that status so reports can state it honestly.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.track_a_interpretable.backend import InterpSignal

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "data" / "interp_artifacts"


class ArtifactBackend:
    name = "artifact-backend"
    mode = "artifact"

    def __init__(self, fallback_note: str = "") -> None:
        self._fallback_note = fallback_note
        self._cache: dict[str, dict] = {}

    def _load(self, rubric_id: str) -> dict:
        if rubric_id in self._cache:
            return self._cache[rubric_id]
        path = ARTIFACTS_DIR / f"{rubric_id}.artifacts.json"
        data: dict = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        self._cache[rubric_id] = data
        return data

    def is_placeholder(self, rubric_id: str) -> bool:
        """True if the shipped artifacts are synthetic placeholders (not real captures)."""
        return bool(self._load(rubric_id).get("placeholder", True))

    def signal_for(
        self, rubric_id: str, example_id: str, answer_text: str
    ) -> InterpSignal:
        data = self._load(rubric_id)
        entries = data.get("signals", {})
        entry = entries.get(example_id)
        note_bits = []
        if self._fallback_note:
            note_bits.append(self._fallback_note)
        if data.get("placeholder", True):
            note_bits.append("synthetic placeholder artifact")

        if entry is None:
            # Neutral signal: assume content-driven, no spurious influence. Never raise.
            note_bits.append("no artifact for example; neutral signal")
            return InterpSignal(notes="; ".join(note_bits))

        return InterpSignal(
            content_attribution=dict(entry.get("content_attribution", {})),
            spurious_feature_activation=dict(
                entry.get("spurious_feature_activation", {})
            ),
            notes="; ".join(note_bits) if note_bits else entry.get("notes", ""),
        )
