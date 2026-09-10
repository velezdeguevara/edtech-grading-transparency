"""Track B: the explainable, vendor-neutral frontier grader.

This grader implements the shared ``Grader`` interface, so the evals harness scores
it identically to any other grader. It is *explainable* (rubric-grounded, structured,
per-criterion output with evidence) but NOT mechanistically interpretable — that is
the whole point of Track B.

It delegates text generation to a ``Provider`` (see ``providers.py``), defaulting to
the offline ``MockProvider`` so it runs with no API key. Point it at a real
OpenAI-compatible endpoint by passing ``OpenAICompatibleProvider()`` instead.
"""

from __future__ import annotations

import json

from src.common.grading.schema import (
    CriterionAssessment,
    CriterionOutcome,
    Grader,
    ProposedGrade,
    Rubric,
)
from src.track_b_explainable.providers import MockProvider, Provider

_SYSTEM_PROMPT = (
    "You are a careful Social Science grading assistant. You grade a student's answer "
    "ONLY against the provided rubric criteria. You do not reward length, confident "
    "tone, or writing style — only whether the content satisfies each criterion. "
    "For each criterion, decide met / partial / not_met, quote a short evidence span "
    "from the student's answer (empty string if none), and give a confidence in [0,1]. "
    "Respond ONLY with a JSON object of the form: "
    '{"assessments": [{"criterion_id": "...", "outcome": "met|partial|not_met", '
    '"evidence_span": "...", "confidence": 0.0}]}'
)

_VALID_OUTCOMES = {o.value for o in CriterionOutcome}


class ExplainableGrader(Grader):
    name = "track-b-explainable"

    def __init__(self, provider: Provider | None = None) -> None:
        self.provider = provider or MockProvider()
        # Reflect the backend in the name so eval outputs are self-describing.
        self.name = f"track-b-explainable[{self.provider.name}]"

    def _build_user_prompt(self, rubric: Rubric, answer_text: str) -> str:
        criteria_lines = []
        for c in rubric.criteria:
            # 'id:' lines are what the mock/parse helpers key on.
            criteria_lines.append(
                f"- id: {c.id}\n  description: {c.description}\n  max_points: {c.max_points}"
            )
        criteria_block = "\n".join(criteria_lines)
        return (
            f"QUESTION:\n{rubric.question}\n\n"
            f"RUBRIC_CRITERIA:\n{criteria_block}\n\n"
            f"<STUDENT_ANSWER>\n{answer_text}\n</STUDENT_ANSWER>\n\n"
            "Grade the answer against each criterion and return the JSON object."
        )

    def grade(self, rubric: Rubric, answer_text: str) -> ProposedGrade:
        user_prompt = self._build_user_prompt(rubric, answer_text)
        raw = self.provider.complete(_SYSTEM_PROMPT, user_prompt)
        return self._parse(raw, rubric)

    def _parse(self, raw: str, rubric: Rubric) -> ProposedGrade:
        """Parse the provider's JSON into a ProposedGrade, defensively.

        A real model may return malformed JSON or unknown criteria; we fail safe by
        treating unparseable / missing criteria as not_met with zero confidence, so a
        bad response yields a conservative (low) grade rather than crashing. This is a
        safety-relevant choice: the tool should never silently inflate a grade.
        """
        valid_ids = {c.id for c in rubric.criteria}
        parsed_by_id: dict[str, CriterionAssessment] = {}

        try:
            data = json.loads(_strip_code_fences(raw))
            for item in data.get("assessments", []):
                cid = item.get("criterion_id")
                if cid not in valid_ids:
                    continue
                outcome_str = str(item.get("outcome", "")).lower()
                outcome = (
                    CriterionOutcome(outcome_str)
                    if outcome_str in _VALID_OUTCOMES
                    else CriterionOutcome.NOT_MET
                )
                conf = item.get("confidence", 0.0)
                try:
                    conf = max(0.0, min(1.0, float(conf)))
                except (TypeError, ValueError):
                    conf = 0.0
                parsed_by_id[cid] = CriterionAssessment(
                    criterion_id=cid,
                    outcome=outcome,
                    evidence_span=str(item.get("evidence_span", "")),
                    confidence=conf,
                )
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass  # fall through: any missing criterion becomes not_met below

        # Ensure every rubric criterion has an assessment (fail-safe to not_met).
        assessments = []
        for c in rubric.criteria:
            assessments.append(
                parsed_by_id.get(
                    c.id,
                    CriterionAssessment(
                        criterion_id=c.id,
                        outcome=CriterionOutcome.NOT_MET,
                        evidence_span="",
                        confidence=0.0,
                    ),
                )
            )
        return ProposedGrade(rubric_id=rubric.id, assessments=tuple(assessments))


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` fences some models wrap JSON in."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t
        if t.endswith("```"):
            t = t[: -3]
        # drop a leading 'json' language tag if present
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    return t.strip()
