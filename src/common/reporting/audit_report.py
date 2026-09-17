"""Grading-audit summary report — audience: **auditor**.

Answers the auditor's questions from the append-only audit log (see
``src/common/human_review/audit_log.py``):
  - How many grades were auto-accepted vs. escalated to a human?
  - Of the human-reviewed grades, how many were overridden? (override rate — H4)
  - Why were grades escalated (escalation reasons, incl. security violations)?
  - Which attempted attacks were caught and escalated?

It reads audit *records* (dicts) so it works against a real on-disk log or an
in-memory list — no coupling to how the log was produced.
"""

from __future__ import annotations

from collections import Counter

from src.common.human_review.audit_log import AuditLog, summarize_override_rate
from src.common.human_review.review import ReviewRoute
from src.common.reporting.common import (
    HUMAN_IN_THE_LOOP_BANNER,
    Report,
    h1,
    h2,
    join_sections,
    pct,
    provenance_line,
    table,
)

FILENAME = "grading-audit-summary.md"
_ESCALATE = ReviewRoute.ESCALATE_TO_HUMAN.value


def build_grading_audit_report(records: list[dict]) -> Report:
    """Build the auditor's summary from audit-log records."""
    summary = summarize_override_rate(records)

    overview = table(
        ["Metric", "Value"],
        [
            ["Total grades logged", str(summary.total)],
            ["Auto-accepted", str(summary.auto_accepted)],
            ["Escalated to human", str(summary.escalated)],
            ["Approved by teacher", str(summary.approved)],
            ["Overridden by teacher", str(summary.overridden)],
            ["Escalation rate", pct(summary.escalation_rate)],
            [
                "Override rate (of reviewed)",
                pct(summary.override_rate),
            ],
        ],
    )

    # Escalation reasons — free-text reason strings grouped and counted.
    reason_counts = Counter(
        (r.get("escalate_reason") or "").strip()
        for r in records
        if r.get("route") == _ESCALATE
    )
    reason_rows = [
        [reason or "_(no reason recorded)_", str(count)]
        for reason, count in reason_counts.most_common()
    ]
    reasons_tbl = table(["Escalation reason", "Count"], reason_rows)

    # Security violations (attempted attacks) — a distinct, high-signal subset.
    security_records = [r for r in records if r.get("security_violation")]
    security_rows = [
        [
            r.get("example_id", "?"),
            r.get("route", "?"),
            (r.get("decision_kind") or "?"),
        ]
        for r in security_records
    ]
    security_tbl = table(
        ["Example", "Route", "Decision"], security_rows
    )

    spurious_flagged = sum(1 for r in records if r.get("spurious_reliance_flag"))

    body = join_sections(
        [
            h1("Grading-Audit Summary"),
            provenance_line("auditor"),
            HUMAN_IN_THE_LOOP_BANNER,
            (
                "This report is derived entirely from the append-only audit log. Each "
                "logged grade is either auto-accepted or escalated to a human; every "
                "escalated grade carries a teacher decision (approve/override) with a "
                "rationale. The log is the technical audit trail — it does not, by "
                "itself, constitute legal/regulatory compliance."
            ),
            h2("Decision overview"),
            overview,
            h2("Why grades were escalated"),
            (
                f"Grades flagged for spurious-feature reliance: **{spurious_flagged}**. "
                "Reasons below aggregate the free-text rationale on each escalated grade."
            ),
            reasons_tbl,
            h2("Attempted attacks (security violations)"),
            (
                f"Detected likely prompt-injection / attack attempts: "
                f"**{len(security_records)}**. A detection escalates to a human — it is "
                "never finalised by the tool. Detection covers a known-attack taxonomy "
                "only (defence-in-depth, not a guarantee)."
            ),
            security_tbl,
        ]
    )
    return Report(title="Grading-Audit Summary", filename=FILENAME, body=body)


def build_grading_audit_report_from_log(audit_log: AuditLog | None = None) -> Report:
    """Convenience: read the default (or given) on-disk audit log and summarise it."""
    log = audit_log or AuditLog()
    return build_grading_audit_report(log.read_all())
