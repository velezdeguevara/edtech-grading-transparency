"""Tests for the human-in-the-loop review layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.common.grading.schema import (
    CriterionAssessment,
    CriterionOutcome,
    ProposedGrade,
)
from src.common.human_review.audit_log import (
    AuditLog,
    build_record,
    summarize_override_rate,
)
from src.common.human_review.pipeline import process_review
from src.common.human_review.review import (
    DecisionKind,
    ReviewRequest,
    ReviewRoute,
    approve,
    override,
    route,
    route_all_to_human,
)
from src.common.rubrics.loader import load_rubric

RUBRIC_ID = "ss-wwi-causes-v1"


def _grade(flag: bool) -> ProposedGrade:
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
        rubric_id=RUBRIC_ID, assessments=assessments, spurious_reliance_flag=flag
    )


def _request(flag: bool) -> ReviewRequest:
    return ReviewRequest(
        rubric_id=RUBRIC_ID,
        example_id="ex-test",
        answer_text="some answer",
        proposed=_grade(flag),
    )


# --- Routing ---

def test_route_auto_accept_when_not_flagged():
    assert route(_request(flag=False)) is ReviewRoute.AUTO_ACCEPT


def test_route_escalates_when_flagged():
    assert route(_request(flag=True)) is ReviewRoute.ESCALATE_TO_HUMAN


def test_route_all_to_human_always_escalates():
    assert route_all_to_human(_request(flag=False)) is ReviewRoute.ESCALATE_TO_HUMAN


# --- Decision authority ---

def test_approve_matches_proposal():
    grade = _grade(flag=False)
    decision = approve(grade, teacher_id="t1")
    assert decision.kind is DecisionKind.APPROVED
    rubric = load_rubric(RUBRIC_ID)
    assert decision.final_total(rubric) == grade.total_points(rubric)


def test_override_changes_outcome_and_total():
    grade = _grade(flag=True)
    rubric = load_rubric(RUBRIC_ID)
    decision = override(
        grade, teacher_id="t1", changes={"political": CriterionOutcome.NOT_MET}
    )
    assert decision.kind is DecisionKind.OVERRIDDEN
    # Overriding one MET criterion to NOT_MET lowers the total.
    assert decision.final_total(rubric) < grade.total_points(rubric)


def test_override_that_matches_proposal_is_approved():
    grade = _grade(flag=False)
    # "change" a criterion to the value it already has -> effectively an approval.
    decision = override(
        grade, teacher_id="t1", changes={"political": CriterionOutcome.MET}
    )
    assert decision.kind is DecisionKind.APPROVED


# --- Pipeline enforces human-in-the-loop ---

def test_escalated_request_requires_decision(tmp_path: Path):
    audit = AuditLog(path=tmp_path / "audit.jsonl")
    rubric = load_rubric(RUBRIC_ID)
    with pytest.raises(ValueError):
        process_review(_request(flag=True), rubric, audit, decision=None)


def test_auto_accept_logs_without_decision(tmp_path: Path):
    audit = AuditLog(path=tmp_path / "audit.jsonl")
    rubric = load_rubric(RUBRIC_ID)
    taken = process_review(_request(flag=False), rubric, audit, decision=None)
    assert taken is ReviewRoute.AUTO_ACCEPT
    records = audit.read_all()
    assert len(records) == 1
    assert records[0]["decision_kind"] == "auto_accepted"


# --- Audit log ---

def test_audit_log_appends_and_reads(tmp_path: Path):
    audit = AuditLog(path=tmp_path / "audit.jsonl")
    rubric = load_rubric(RUBRIC_ID)
    req = _request(flag=True)
    decision = override(
        req.proposed, teacher_id="t1", changes={"economic": CriterionOutcome.NOT_MET}
    )
    process_review(req, rubric, audit, decision=decision)
    process_review(_request(flag=False), rubric, audit, decision=None)
    records = audit.read_all()
    assert len(records) == 2
    assert all("timestamp" in r for r in records)


def test_build_record_contains_provenance(tmp_path: Path):
    rubric = load_rubric(RUBRIC_ID)
    req = _request(flag=True)
    rec = build_record(req, ReviewRoute.ESCALATE_TO_HUMAN, rubric, approve(req.proposed, "t1"))
    for key in ("timestamp", "rubric_id", "example_id", "route", "proposed_total"):
        assert key in rec


# --- Override-rate summary (H4) ---

def test_override_rate_summary(tmp_path: Path):
    audit = AuditLog(path=tmp_path / "audit.jsonl")
    rubric = load_rubric(RUBRIC_ID)
    # 1 auto-accept, 1 approved, 2 overridden.
    process_review(_request(flag=False), rubric, audit, decision=None)
    process_review(_request(flag=True), rubric, audit, decision=approve(_grade(True), "t1"))
    for _ in range(2):
        req = _request(flag=True)
        d = override(req.proposed, "t1", changes={"political": CriterionOutcome.NOT_MET})
        process_review(req, rubric, audit, decision=d)

    summary = summarize_override_rate(audit.read_all())
    assert summary.total == 4
    assert summary.auto_accepted == 1
    assert summary.approved == 1
    assert summary.overridden == 2
    # override rate = overridden / (approved + overridden) = 2/3
    assert abs(summary.override_rate - (2 / 3)) < 1e-9
