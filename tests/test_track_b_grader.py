"""Tests for the Track B explainable grader and its providers."""

from __future__ import annotations

import pytest

from src.common.grading.schema import CriterionOutcome
from src.common.rubrics.loader import load_fixtures, load_rubric
from src.track_b_explainable.grader import ExplainableGrader, _strip_code_fences
from src.track_b_explainable.providers import (
    OpenAICompatibleProvider,
    _extract_criterion_ids,
)

RUBRIC_ID = "ss-wwi-causes-v1"


class _CannedProvider:
    """A provider returning a fixed string, for testing the parse path."""

    name = "canned"

    def __init__(self, payload: str) -> None:
        self._payload = payload

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self._payload


def test_extract_criterion_ids_handles_list_markers():
    prompt = "- id: political\n  desc\n- id: military\n"
    assert _extract_criterion_ids(prompt) == ["political", "military"]


def test_mock_grader_produces_full_assessment_set():
    rubric = load_rubric(RUBRIC_ID)
    grader = ExplainableGrader()  # defaults to MockProvider
    ex = load_fixtures(RUBRIC_ID)[0]  # the strong answer
    grade = grader.grade(rubric, ex.answer_text)
    # One assessment per criterion, all criterion ids valid.
    assert len(grade.assessments) == len(rubric.criteria)
    valid = {c.id for c in rubric.criteria}
    assert all(a.criterion_id in valid for a in grade.assessments)


def test_strong_answer_scores_high_with_mock():
    rubric = load_rubric(RUBRIC_ID)
    grader = ExplainableGrader()
    strong = load_fixtures(RUBRIC_ID)[0].answer_text
    total = grader.grade(rubric, strong).total_points(rubric)
    assert total >= 8.0  # out of 10


def test_malformed_json_fails_safe_to_not_met():
    rubric = load_rubric(RUBRIC_ID)
    grader = ExplainableGrader(provider=_CannedProvider("not json at all"))
    grade = grader.grade(rubric, "anything")
    assert len(grade.assessments) == len(rubric.criteria)
    assert all(a.outcome is CriterionOutcome.NOT_MET for a in grade.assessments)
    assert grade.total_points(rubric) == 0.0


def test_unknown_criteria_are_ignored():
    rubric = load_rubric(RUBRIC_ID)
    payload = (
        '{"assessments": [{"criterion_id": "bogus", "outcome": "met", '
        '"evidence_span": "x", "confidence": 1.0}]}'
    )
    grader = ExplainableGrader(provider=_CannedProvider(payload))
    grade = grader.grade(rubric, "anything")
    # bogus id ignored -> all real criteria default to not_met.
    assert grade.total_points(rubric) == 0.0


def test_code_fenced_json_is_parsed():
    rubric = load_rubric(RUBRIC_ID)
    inner = '{"assessments": [{"criterion_id": "political", "outcome": "met", "evidence_span": "", "confidence": 0.9}]}'
    payload = f"```json\n{inner}\n```"
    grader = ExplainableGrader(provider=_CannedProvider(payload))
    grade = grader.grade(rubric, "anything")
    political = [a for a in grade.assessments if a.criterion_id == "political"][0]
    assert political.outcome is CriterionOutcome.MET


def test_confidence_is_clamped():
    rubric = load_rubric(RUBRIC_ID)
    payload = (
        '{"assessments": [{"criterion_id": "political", "outcome": "met", '
        '"evidence_span": "", "confidence": 5.0}]}'
    )
    grader = ExplainableGrader(provider=_CannedProvider(payload))
    grade = grader.grade(rubric, "anything")
    political = [a for a in grade.assessments if a.criterion_id == "political"][0]
    assert 0.0 <= political.confidence <= 1.0


def test_strip_code_fences_plain_passthrough():
    assert _strip_code_fences('{"a": 1}') == '{"a": 1}'


def test_http_provider_requires_config(monkeypatch):
    # No env vars set -> constructor should refuse rather than call out silently.
    monkeypatch.delenv("GRADER_API_BASE", raising=False)
    monkeypatch.delenv("GRADER_MODEL", raising=False)
    with pytest.raises(ValueError):
        OpenAICompatibleProvider()
