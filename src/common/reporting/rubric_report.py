"""Rubric-optimization signal report — audience: **content author**.

Surfaces where a rubric may need work, from two independent signals:

1. **Most-overridden criteria** (from the audit log): when teachers repeatedly change
   a particular criterion's outcome, that criterion is either ambiguous, mis-weighted,
   or hard for the grader — a concrete rubric-authoring signal (grounded in real human
   decisions, not model guesses).

2. **Weakest content attribution / most spurious-prone criteria** (from the interp
   artifacts): criteria whose grades lean least on rubric content and most on spurious
   features. This is placeholder-labelled until a real Mode 3 run, because it is derived
   from synthetic artifacts.

Both are diagnostics, not verdicts: they point the content author at criteria worth
re-reading, not at "correct" rewrites.
"""

from __future__ import annotations

from src.common.human_review.review import DecisionKind
from src.common.reporting.common import (
    PLACEHOLDER_BANNER,
    Report,
    h1,
    h2,
    join_sections,
    pct,
    provenance_line,
    table,
)
from src.common.rubrics.loader import load_rubric
from src.track_a_interpretable.artifact_backend import ArtifactBackend

FILENAME = "rubric-optimization.md"
RUBRIC_ID = "ss-wwi-causes-v1"


def _override_counts_by_criterion(records: list[dict]) -> dict[str, dict[str, int]]:
    """Per-criterion {reviewed, changed} counts from overridden audit records.

    A criterion is 'changed' when the teacher's final outcome differs from the
    proposed outcome on an overridden decision.
    """
    stats: dict[str, dict[str, int]] = {}
    for r in records:
        if r.get("decision_kind") != DecisionKind.OVERRIDDEN.value:
            continue
        proposed = r.get("proposed_outcomes", {}) or {}
        final = r.get("final_outcomes", {}) or {}
        for cid, proposed_outcome in proposed.items():
            s = stats.setdefault(cid, {"reviewed": 0, "changed": 0})
            s["reviewed"] += 1
            if final.get(cid) != proposed_outcome:
                s["changed"] += 1
    return stats


def _mean_content_attribution(backend: ArtifactBackend, rubric_id: str) -> dict[str, float]:
    """Mean content attribution per criterion across all artifact signals."""
    data = backend._load(rubric_id)  # internal read; acceptable within the package
    signals = data.get("signals", {})
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for entry in signals.values():
        for cid, val in (entry.get("content_attribution", {}) or {}).items():
            sums[cid] = sums.get(cid, 0.0) + float(val)
            counts[cid] = counts.get(cid, 0) + 1
    return {cid: sums[cid] / counts[cid] for cid in sums if counts[cid]}


def build_rubric_optimization_report(
    records: list[dict], rubric_id: str = RUBRIC_ID
) -> Report:
    rubric = load_rubric(rubric_id)
    crit_desc = {c.id: c.description for c in rubric.criteria}

    # 1. Most-overridden criteria (real human signal).
    override_stats = _override_counts_by_criterion(records)
    override_rows = []
    for cid in sorted(
        override_stats,
        key=lambda c: override_stats[c]["changed"],
        reverse=True,
    ):
        s = override_stats[cid]
        rate = s["changed"] / s["reviewed"] if s["reviewed"] else 0.0
        override_rows.append(
            [cid, str(s["changed"]), str(s["reviewed"]), pct(rate)]
        )
    override_tbl = table(
        ["Criterion", "Times changed", "Times reviewed", "Change rate"],
        override_rows,
    )

    # 2. Weakest content attribution (interp signal; placeholder-labelled).
    backend = ArtifactBackend()
    is_placeholder = backend.is_placeholder(rubric_id)
    content_attr = _mean_content_attribution(backend, rubric_id)
    attr_rows = []
    for cid in sorted(content_attr, key=lambda c: content_attr[c]):
        attr_rows.append(
            [
                cid,
                f"{content_attr[cid]:.2f}",
                crit_desc.get(cid, ""),
            ]
        )
    attr_tbl = table(
        ["Criterion", "Mean content attribution", "Description"], attr_rows
    )

    sections = [
        h1("Rubric-Optimization Signals"),
        provenance_line("content author"),
        (
            "Two independent signals point at criteria worth re-reading. They are "
            "diagnostics, not prescriptions: high override or low content attribution "
            "flags ambiguity or difficulty, it does not dictate a specific rewrite."
        ),
        h2("Most-overridden criteria (teacher signal)"),
        (
            "Grounded in real human decisions from the audit log. A high change rate "
            "means teachers frequently disagreed with the proposed outcome on this "
            "criterion — a sign it may be ambiguous or mis-weighted."
        ),
        override_tbl,
        h2("Weakest content attribution (interpretability signal)"),
    ]
    if is_placeholder:
        sections.append(PLACEHOLDER_BANNER)
    sections.extend(
        [
            (
                "Lower attribution means the grade for that criterion leaned less on "
                "rubric content (and more on spurious features). A persistently low "
                "value suggests the criterion's cues are hard for the grader to latch "
                "onto from the answer text."
            ),
            attr_tbl,
        ]
    )
    return Report(
        title="Rubric-Optimization Signals",
        filename=FILENAME,
        body=join_sections(sections),
    )
