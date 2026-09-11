"""Capability detection: pick the right InterpBackend for the current environment.

Order of decision:
  1. If INTERP_MODE is set explicitly (artifact|local|cloud), honour it.
  2. Otherwise, if torch + a usable model appear available, choose the torch backend.
  3. Otherwise, fall back to the artifact backend (Mode 1) so the pipeline always runs.

The detector never raises on a missing optional dependency; it degrades to Mode 1.
See docs/running-modes.md.
"""

from __future__ import annotations

import importlib.util
import os

from src.track_a_interpretable.backend import InterpBackend

VALID_MODES = ("artifact", "local", "cloud")


def _torch_available() -> bool:
    return importlib.util.find_spec("torch") is not None


def _transformer_lens_available() -> bool:
    return importlib.util.find_spec("transformer_lens") is not None


def detect_mode() -> str:
    """Return the mode to use: 'artifact', 'local', or 'cloud'."""
    forced = os.environ.get("INTERP_MODE", "").strip().lower()
    if forced in VALID_MODES:
        return forced
    if forced:
        # An unrecognised value should not silently pick something surprising.
        raise ValueError(
            f"INTERP_MODE={forced!r} is invalid; expected one of {VALID_MODES}."
        )
    # Auto-detect: need both torch and transformer_lens for a real run.
    if _torch_available() and _transformer_lens_available():
        return "local"
    return "artifact"


def get_backend(mode: str | None = None) -> InterpBackend:
    """Construct the backend for the given (or detected) mode.

    Falls back to the artifact backend if a torch backend is requested but its
    dependencies are unavailable, so a misconfigured environment still runs Mode 1.
    """
    resolved = (mode or detect_mode()).lower()
    if resolved not in VALID_MODES:
        raise ValueError(f"Unknown mode {resolved!r}; expected one of {VALID_MODES}.")

    if resolved in ("local", "cloud"):
        if _torch_available() and _transformer_lens_available():
            from src.track_a_interpretable.local_torch_backend import LocalTorchBackend

            return LocalTorchBackend(mode=resolved)
        # Requested a real run but deps missing -> degrade to artifact with a note.
        from src.track_a_interpretable.artifact_backend import ArtifactBackend

        return ArtifactBackend(
            fallback_note=(
                f"requested mode '{resolved}' but torch/transformer_lens are "
                "unavailable; fell back to artifact mode"
            )
        )

    from src.track_a_interpretable.artifact_backend import ArtifactBackend

    return ArtifactBackend()
