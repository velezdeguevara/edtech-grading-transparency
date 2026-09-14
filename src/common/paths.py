"""Shared path helpers — locate the repository root robustly.

Anchoring to a repo marker (rather than a hardcoded ``parents[N]`` count) makes the
loaders resilient to files being moved within the repo: they keep working as long as
they live somewhere under the repository root. Used by every module that reads data
files, so there is one reliable way to find the repo root instead of scattered magic
numbers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# Markers that identify the repository root. The first found while walking upward wins.
_ROOT_MARKERS = (".git", "requirements.txt", "pyproject.toml")


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return the repository root by walking upward from this file until a marker.

    Falls back to the ancestor that contains a ``data`` directory, and finally to a
    fixed ancestor, so it degrades gracefully rather than raising in odd layouts.
    """
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if any((parent / marker).exists() for marker in _ROOT_MARKERS):
            return parent
    # Fallbacks (should rarely trigger): a parent containing data/, else 2 levels up.
    for parent in here.parents:
        if (parent / "data").is_dir():
            return parent
    return here.parents[2]


def data_dir() -> Path:
    """Path to the repository's ``data`` directory."""
    return repo_root() / "data"


def reports_dir() -> Path:
    """Path to the repository's ``reports`` directory."""
    return repo_root() / "reports"
