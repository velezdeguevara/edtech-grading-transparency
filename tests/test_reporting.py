"""Tests for the stakeholder reporting layer."""

from __future__ import annotations

from pathlib import Path

from src.common.grading.schema import (
    CriterionAssessment,
    CriterionOutcome,
    ProposedGrade,
)
from src.common.human_review.audit_log import AuditLog
from src.common.human_review.pipeline import process_review
from src.common.human_review.review import ReviewRequest, approve, override
from src.common.reporting.audit_report import build_grading_audit_report
from src.common.reporting.comparison_report import build_comparison_report
from src.common.reporting.common import (
    PLACEHOLDER_BANNER,
    Report,
    join_sections,
    table,
)
from src.common.reporting.generate import (
    build_all_reports,
    seed_demo_audit_log,
    write_reports,
)
from src.common.reporting.interp_report import build_interp_findings_report
from src.common.reporting.rubric_report import build_rubric_optimization_report
from src.common.rubrics.loader import load_rubric

RUBRIC_ID = "ss-wwi-causes-v1"


# --- Fixtures / helpers --------------------------------------------------------------

def _grade(*, spurious: bool = False, security: bool = False) -> ProposedGrade:
    rubric = load_rubric(RUBRIC_ID)
    assessments = tuple(
        CriterionAssessment(
            criterion_id=c.id,
            outcome=CriterionOutcome.MET,
            evidence_span="x",
            confidence=0.9,
        )
        for c in rubric.criteria
    )
    return ProposedGrade(
        rubric_id=RUBRIC_ID,
        assessments=assessments,
        spurious_reliance_flag=spurious,
        security_violation=security,
    )


def _request(example_id: str, grade: ProposedGrade) -> ReviewRequest:
    return ReviewRequest(
        rubric_id=RUBRIC_ID, example_id=example_id, answer_text="a", proposed=grade
    )


def _populated_log(tmp_path: Path) -> AuditLog:
    """A log with 1 auto-accept, 1 approved, 2 overrides (economic, evidence)."""
    audit = AuditLog(path=tmp_path / "audit.jsonl")
    rubric = load_rubric(RUBRIC_ID)
    process_review(_request("a1", _grade()), rubric, audit, decision=None)
    req = _request("ap", _grade(spurious=True))
    process_review(req, rubric, audit, decision=approve(req.proposed, "t1"))
    for cid, ex in (("economic", "o1"), ("evidence", "o2")):
        req = _request(ex, _grade(spurious=True))
        d = override(req.proposed, "t1", changes={cid: CriterionOutcome.NOT_MET})
        process_review(req, rubric, audit, decision=d)
    return audit


# --- common.py helpers ---------------------------------------------------------------

def test_table_renders_placeholder_when_empty():
    out = table(["A", "B"], [])
    assert "| A | B |" in out
    assert "_(none)_" in out


def test_join_sections_drops_empties_and_ends_with_newline():
    out = join_sections(["one", "", "two"])
    assert out == "one\n\ntwo\n"


# --- Grading-audit report ------------------------------------------------------------

def test_audit_report_counts_and_security(tmp_path: Path):
    audit = _populated_log(tmp_path)
    # Add a security-violation escalation.
    rubric = load_rubric(RUBRIC_ID)
    req = _request("attack", _grade(security=True))
    process_review(req, rubric, audit, decision=approve(req.proposed, "t1"))

    report = build_grading_audit_report(audit.read_all())
    assert isinstance(report, Report)
    body = report.render()
    assert "Grading-Audit Summary" in body
    assert "Total grades logged | 5" in body
    # reviewed = approved(ap, attack) + overridden(o1, o2) = 4; override rate 2/4 = 50%
    assert "50.0%" in body
    # The security violation surfaces in its table.
    assert "attack" in body


def test_audit_report_handles_empty_log():
    report = build_grading_audit_report([])
    body = report.render()
    assert "Total grades logged | 0" in body
    # Empty escalation-reason and security tables fall back to the placeholder.
    assert "_(none)_" in body


# --- Comparison report ---------------------------------------------------------------

def test_comparison_report_has_all_dimensions():
    body = build_comparison_report(RUBRIC_ID).render()
    for heading in (
        "Grade quality",
        "Escalation head-to-head",
        "Robustness by attack category",
    ):
        assert heading in body
    # H3 headline numbers from the placeholder artifacts.
    assert "0.83" in body and "0.67" in body
    # Honesty framing present.
    assert "floor" in body.lower()
    assert "not a safety guarantee" in body.lower()


# --- Rubric-optimization report ------------------------------------------------------

def test_rubric_report_surfaces_overridden_criteria(tmp_path: Path):
    audit = _populated_log(tmp_path)
    body = build_rubric_optimization_report(audit.read_all(), RUBRIC_ID).render()
    assert "Rubric-Optimization Signals" in body
    # economic and evidence were each overridden once out of one override-review.
    assert "economic" in body
    assert "evidence" in body
    # Placeholder artifacts -> banner present.
    assert PLACEHOLDER_BANNER in body


def test_rubric_report_empty_records_still_renders():
    body = build_rubric_optimization_report([], RUBRIC_ID).render()
    assert "Most-overridden criteria" in body
    # No overrides -> the override table is empty.
    assert "_(none)_" in body


# --- Interp-findings report ----------------------------------------------------------

def test_interp_report_is_placeholder_labelled_and_scores_h3():
    report = build_interp_findings_report(RUBRIC_ID)
    assert report.filename == "interp-findings/interp-findings.md"
    body = report.render()
    assert PLACEHOLDER_BANNER in body
    assert "H3" in body
    # The spurious probe should be marked as one that SHOULD escalate.
    assert "ex04-long-but-confident-empty" in body


# --- generate.py orchestration -------------------------------------------------------

def test_build_all_reports_returns_four():
    reports = build_all_reports([], RUBRIC_ID)
    assert len(reports) == 4
    filenames = {r.filename for r in reports}
    assert filenames == {
        "grading-audit-summary.md",
        "track-comparison.md",
        "rubric-optimization.md",
        "interp-findings/interp-findings.md",
    }


def test_write_reports_creates_files(tmp_path: Path, monkeypatch):
    # Redirect reports_dir() used inside write_reports to a temp dir.
    import src.common.reporting.generate as gen

    monkeypatch.setattr(gen, "reports_dir", lambda: tmp_path)
    reports = build_all_reports([], RUBRIC_ID)
    written = write_reports(reports)
    assert len(written) == 4
    # The interp-findings subdirectory was created.
    assert (tmp_path / "interp-findings" / "interp-findings.md").exists()
    for path in written:
        assert Path(path).read_text(encoding="utf-8").strip()


def test_seed_demo_audit_log_is_synthetic_and_populates(tmp_path: Path):
    audit = AuditLog(path=tmp_path / "audit.jsonl")
    seed_demo_audit_log(audit, RUBRIC_ID)
    records = audit.read_all()
    assert len(records) == 5
    assert any(r.get("security_violation") for r in records)
    # Two overrides seeded (economic + evidence).
    overridden = [r for r in records if r.get("decision_kind") == "overridden"]
    assert len(overridden) == 2
