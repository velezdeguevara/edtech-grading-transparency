"""Load rubrics and fixtures from JSON into the shared dataclasses."""

from __future__ import annotations

import json
from pathlib import Path

from src.common.grading.schema import (
    CriterionOutcome,
    GradedExample,
    Rubric,
    RubricCriterion,
)

# Repository root, derived from this file's location (src/common/rubrics/loader.py).
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"


def load_rubric(rubric_id: str) -> Rubric:
    path = DATA_DIR / "rubrics" / f"{rubric_id}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    criteria = tuple(
        RubricCriterion(
            id=c["id"],
            description=c["description"],
            max_points=int(c["max_points"]),
        )
        for c in raw["criteria"]
    )
    return Rubric(id=raw["id"], question=raw["question"], criteria=criteria)


def load_fixtures(rubric_id: str) -> list[GradedExample]:
    path = DATA_DIR / "fixtures" / f"{rubric_id}.fixtures.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    examples: list[GradedExample] = []
    for ex in raw["examples"]:
        outcomes = {
            cid: CriterionOutcome(val) for cid, val in ex["teacher_outcomes"].items()
        }
        examples.append(
            GradedExample(
                id=ex["id"],
                rubric_id=raw["rubric_id"],
                answer_text=ex["answer_text"],
                teacher_outcomes=outcomes,
            )
        )
    return examples
