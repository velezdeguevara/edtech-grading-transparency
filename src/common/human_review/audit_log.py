"""Append-only audit log + override-rate summary for human review.

Every routing + human decision is recorded as one JSON line (JSONL) in
``reports/grading-audit/``. Append-only, timestamped, and self-contained per record
— the "concrete audit trail" that serves compliance/auditor needs.

IMPORTANT: this provides audit-log *infrastructure*. It does NOT, by itself, make any
deployment legally compliant (e.g. with the EU AI Act). Legal conformity is an
organisational process; this module supplies one technical ingredient of it.

The override-rate summary aggregates records to track how often teachers override the
tool — the signal behind hypothesis H4 ("teacher intervention becomes insignificant")
and a product-owner metric.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.common.grading.schema import Rubric
from src.common.human_review.review import (
    DecisionKind,
    ReviewRequest,
    ReviewRoute,
    TeacherDecision,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AUDIT_DIR = REPO_ROOT / "reports" / "grading-audit"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_record(
    request: ReviewRequest,
    route: ReviewRoute,
    rubric: Rubric,
    decision: TeacherDecision | None,
) -> dict:
    """Build one audit record. ``decision`` is None for auto-accepted grades."""
    proposed_outcomes = {
        a.criterion_id: a.outcome.value for a in request.proposed.assessments
    }
    record: dict = {
        "timestamp": _utc_now_iso(),
        "rubric_id": request.rubric_id,
        "example_id": request.example_id,
        "route": route.value,
        "escalate_reason": request.escalate_reason(),
        "spurious_reliance_flag": request.proposed.spurious_reliance_flag,
        "proposed_outcomes": proposed_outcomes,
        "proposed_total": request.proposed.total_points(rubric),
        "min_confidence": request.proposed.min_confidence(),
    }
    if decision is not None:
        record.update(
            {
                "decision_kind": decision.kind.value,
                "teacher_id": decision.teacher_id,
                "final_outcomes": {
                    cid: o.value for cid, o in decision.final_outcomes.items()
                },
                "final_total": decision.final_total(rubric),
                "teacher_comment": decision.comment,
            }
        )
    else:
        record["decision_kind"] = "auto_accepted"
    return record


class AuditLog:
    """Append-only JSONL audit log."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_AUDIT_DIR / "audit.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        records = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records


@dataclass
class OverrideRateSummary:
    total: int
    auto_accepted: int
    escalated: int
    approved: int
    overridden: int

    @property
    def override_rate(self) -> float:
        """Fraction of *human-reviewed* grades the teacher overrode."""
        reviewed = self.approved + self.overridden
        return self.overridden / reviewed if reviewed else 0.0

    @property
    def escalation_rate(self) -> float:
        return self.escalated / self.total if self.total else 0.0

    def summary(self) -> str:
        return (
            f"records={self.total}  auto_accepted={self.auto_accepted}  "
            f"escalated={self.escalated}  approved={self.approved}  "
            f"overridden={self.overridden}  "
            f"override_rate={self.override_rate:.2%}  "
            f"escalation_rate={self.escalation_rate:.2%}"
        )


def summarize_override_rate(records: list[dict]) -> OverrideRateSummary:
    total = len(records)
    auto = sum(1 for r in records if r.get("decision_kind") == "auto_accepted")
    escalated = sum(1 for r in records if r.get("route") == ReviewRoute.ESCALATE_TO_HUMAN.value)
    approved = sum(1 for r in records if r.get("decision_kind") == DecisionKind.APPROVED.value)
    overridden = sum(
        1 for r in records if r.get("decision_kind") == DecisionKind.OVERRIDDEN.value
    )
    return OverrideRateSummary(
        total=total,
        auto_accepted=auto,
        escalated=escalated,
        approved=approved,
        overridden=overridden,
    )
