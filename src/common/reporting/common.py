"""Shared helpers for the reporting layer — Markdown rendering + honesty framing.

Deliberately tiny and dependency-free. Every generator returns a :class:`Report`
(a title + a rendered Markdown body + a stable output filename), so the runner in
``generate.py`` can write them uniformly and tests can assert on the text without
touching the filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

# --- Honesty banners (single source of truth; reused across reports) -----------------

# The project's non-negotiable framing (see the top-level README and docs/threat-model).
# Kept as constants so every report tells the same honest story and a wording change
# happens in one place.
PLACEHOLDER_BANNER = (
    "> **Placeholder data.** The interpretability artifacts behind this section are "
    "synthetic placeholders, not real model captures. The pipeline and escalation "
    "logic are real; the *numbers* become genuine only after a Mode 3 cloud run "
    "regenerates the artifacts. Treat figures here as illustrative, not evidential."
)

BASELINE_FLOOR_BANNER = (
    "> **Baseline is a floor, not a promise.** These figures come from the naive "
    "keyword-baseline grader (offline Mode 1). They establish a floor the real Track A "
    "/ Track B graders must beat — they are not a claim about production accuracy."
)

DEFENCE_IN_DEPTH_BANNER = (
    "> **Not a safety guarantee.** Robustness/security figures measure resistance to a "
    "*taxonomy of known* attacks only. Prompt injection is an open problem; real "
    "protection is defence-in-depth (input separation, structured output, escalation, "
    "mandatory human-in-the-loop) — never a test-pass percentage."
)

HUMAN_IN_THE_LOOP_BANNER = (
    "> **The tool proposes; the teacher decides.** Every escalated grade requires a "
    "human decision, and that decision is authoritative and audited. No grade here is "
    "ever finalised by the machine alone."
)


def utc_now_iso() -> str:
    """UTC timestamp (ISO 8601) for report provenance."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Report:
    """A generated report: a title, a Markdown body, and its output filename."""

    title: str
    filename: str  # relative to the report's output subdirectory
    body: str

    def render(self) -> str:
        return self.body


# --- Markdown building blocks --------------------------------------------------------


def h1(text: str) -> str:
    return f"# {text}"


def h2(text: str) -> str:
    return f"## {text}"


def h3(text: str) -> str:
    return f"### {text}"


def provenance_line(role: str, *, extra: str = "") -> str:
    """A small italic provenance/audience line under the title."""
    line = f"*Audience: {role}. Generated {utc_now_iso()} (UTC), offline (Mode 1).*"
    if extra:
        line += f" {extra}"
    return line


def table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a GitHub-flavored Markdown table. Empty rows -> a friendly placeholder."""
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    if not rows:
        return head + "\n" + sep + "\n| " + " | ".join("_(none)_" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(cells) + " |" for cells in rows)
    return head + "\n" + sep + "\n" + body


def pct(x: float) -> str:
    return f"{x:.1%}"


def join_sections(parts: list[str]) -> str:
    """Join non-empty sections with blank lines and a trailing newline."""
    return "\n\n".join(p for p in parts if p).rstrip() + "\n"
