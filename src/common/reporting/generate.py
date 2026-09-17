"""CLI runner: generate all four stakeholder reports into ``reports/``.

Usage (from repo root):
    python -m src.common.reporting.generate            # write reports to reports/
    python -m src.common.reporting.generate --stdout   # print instead of writing
    python -m src.common.reporting.generate --demo-audit  # seed a demo audit log first

The two audit-derived reports (grading-audit summary, rubric-optimization) need audit
records. If the on-disk log is empty and ``--demo-audit`` is given, a small SYNTHETIC
demo log is generated so the reports are non-empty and self-contained — clearly framed
as a demo, never presented as real grading history.

Layout written under ``reports/``:
    grading-audit-summary.md
    track-comparison.md
    rubric-optimization.md
    interp-findings/interp-findings.md
"""

from __future__ import annotations

import argparse

from src.common.grading.schema import (
    CriterionAssessment,
    CriterionOutcome,
    ProposedGrade,
)
from src.common.human_review.audit_log import AuditLog, build_record
from src.common.human_review.pipeline import process_review
from src.common.human_review.review import ReviewRequest, override, route
from src.common.paths import reports_dir
from src.common.reporting.audit_report import build_grading_audit_report
from src.common.reporting.comparison_report import build_comparison_report
from src.common.reporting.common import Report
from src.common.reporting.interp_report import build_interp_findings_report
from src.common.reporting.rubric_report import build_rubric_optimization_report
from src.common.rubrics.loader import load_rubric

RUBRIC_ID = "ss-wwi-causes-v1"


def build_all_reports(records: list[dict], rubric_id: str = RUBRIC_ID) -> list[Report]:
    """Build all four reports from audit records + the eval suite."""
    return [
        build_grading_audit_report(records),
        build_comparison_report(rubric_id),
        build_rubric_optimization_report(records, rubric_id),
        build_interp_findings_report(rubric_id),
    ]


def write_reports(reports: list[Report]) -> list[str]:
    """Write each report under reports/, creating subdirectories as needed."""
    out_dir = reports_dir()
    written: list[str] = []
    for report in reports:
        path = out_dir / report.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.render(), encoding="utf-8")
        written.append(str(path))
    return written


def seed_demo_audit_log(audit_log: AuditLog, rubric_id: str = RUBRIC_ID) -> None:
    """Seed a SMALL synthetic audit log so audit reports are non-empty for a demo.

    Deliberately synthetic and modest: a couple of auto-accepts, an approval, a couple
    of overrides (touching different criteria), and one security-violation escalation.
    Never represents real grading history.
    """
    rubric = load_rubric(rubric_id)

    def grade(*, spurious: bool = False, security: bool = False) -> ProposedGrade:
        assessments = tuple(
            CriterionAssessment(
                criterion_id=c.id,
                outcome=CriterionOutcome.MET,
                evidence_span="(synthetic demo)",
                confidence=0.9,
            )
            for c in rubric.criteria
        )
        return ProposedGrade(
            rubric_id=rubric_id,
            assessments=assessments,
            spurious_reliance_flag=spurious,
            security_violation=security,
        )

    def request(example_id: str, g: ProposedGrade) -> ReviewRequest:
        return ReviewRequest(
            rubric_id=rubric_id,
            example_id=example_id,
            answer_text="(synthetic demo answer)",
            proposed=g,
        )

    # Two auto-accepted grades.
    process_review(request("demo-auto-1", grade()), rubric, audit_log, decision=None)
    process_review(request("demo-auto-2", grade()), rubric, audit_log, decision=None)

    # One escalated grade the teacher overrode on 'economic'.
    req = request("demo-override-econ", grade(spurious=True))
    dec = override(
        req.proposed, "demo-teacher", changes={"economic": CriterionOutcome.NOT_MET}
    )
    process_review(req, rubric, audit_log, decision=dec)

    # One escalated grade the teacher overrode on 'evidence'.
    req = request("demo-override-evidence", grade(spurious=True))
    dec = override(
        req.proposed, "demo-teacher", changes={"evidence": CriterionOutcome.PARTIAL}
    )
    process_review(req, rubric, audit_log, decision=dec)

    # One security-violation escalation, approved after human review (attack rejected).
    req = request("demo-attack", grade(security=True))
    dec = override(req.proposed, "demo-teacher", changes={}, comment="rejected attack")
    # override with no changes is recorded as APPROVED (see review.override); build the
    # record explicitly so the security_violation escalation stays visible in the log.
    audit_log.append(build_record(req, route(req), rubric, dec))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate stakeholder reports.")
    parser.add_argument(
        "--stdout", action="store_true", help="print reports instead of writing files"
    )
    parser.add_argument(
        "--demo-audit",
        action="store_true",
        help="seed a synthetic demo audit log if the on-disk log is empty",
    )
    parser.add_argument("--rubric-id", default=RUBRIC_ID)
    args = parser.parse_args()

    audit_log = AuditLog()
    records = audit_log.read_all()
    if not records and args.demo_audit:
        seed_demo_audit_log(audit_log, args.rubric_id)
        records = audit_log.read_all()

    reports = build_all_reports(records, args.rubric_id)

    if args.stdout:
        for report in reports:
            print(f"\n===== {report.filename} =====\n")
            print(report.render())
        return

    written = write_reports(reports)
    print("Wrote:")
    for path in written:
        print(f"  {path}")
    if not records:
        print(
            "\nNote: audit-derived reports are based on an EMPTY audit log. Run the "
            "review flow (e.g. python -m ui.review_cli) or pass --demo-audit to "
            "populate them."
        )


if __name__ == "__main__":
    main()
