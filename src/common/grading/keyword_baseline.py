"""A deterministic keyword-baseline grader.

This is NOT a real model. It exists so the evals harness is runnable end-to-end
today, and to serve as a naive baseline the real Track A / Track B graders must
beat. It also deliberately illustrates a weakness (it can be fooled by keyword
presence without understanding), which the eval fixtures are designed to expose.
"""

from __future__ import annotations

from src.common.grading.schema import (
    CriterionAssessment,
    CriterionOutcome,
    Grader,
    ProposedGrade,
    Rubric,
)

# Minimal keyword cues per criterion for the WWI-causes rubric.
_KEYWORDS: dict[str, list[str]] = {
    "political": ["alliance", "alliances", "nationalism", "franz ferdinand", "assassinat"],
    "military": ["arms race", "militaris", "mobiliz", "schlieffen", "navy", "naval"],
    "economic": ["econom", "coloni", "imperial", "trade", "industrial"],
    "evidence": ["for example", "for instance", "such as", "britain", "germany"],
}


def _first_span(answer: str, cues: list[str]) -> str:
    low = answer.lower()
    for cue in cues:
        idx = low.find(cue)
        if idx != -1:
            start = max(0, idx - 20)
            end = min(len(answer), idx + len(cue) + 20)
            return answer[start:end].strip()
    return ""


class KeywordBaselineGrader(Grader):
    name = "keyword-baseline"

    def grade(self, rubric: Rubric, answer_text: str) -> ProposedGrade:
        low = answer_text.lower()
        assessments: list[CriterionAssessment] = []
        for crit in rubric.criteria:
            cues = _KEYWORDS.get(crit.id, [])
            hits = sum(1 for cue in cues if cue in low)
            if hits >= 2:
                outcome = CriterionOutcome.MET
            elif hits == 1:
                outcome = CriterionOutcome.PARTIAL
            else:
                outcome = CriterionOutcome.NOT_MET
            assessments.append(
                CriterionAssessment(
                    criterion_id=crit.id,
                    outcome=outcome,
                    evidence_span=_first_span(answer_text, cues),
                    confidence=min(1.0, 0.5 + 0.25 * hits),
                )
            )
        return ProposedGrade(rubric_id=rubric.id, assessments=tuple(assessments))
