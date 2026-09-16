"""Load rubrics and fixtures from JSON into the shared dataclasses."""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.common.grading.schema import (
    CriterionOutcome,
    GradedExample,
    Rubric,
    RubricCriterion,
)
from src.common.paths import data_dir

DATA_DIR = data_dir()


@dataclass(frozen=True)
class AdversarialExample:
    """A GradedExample plus the attack category it represents (for robustness eval)."""

    example: GradedExample
    attack_type: str


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


def load_adversarial_fixtures(rubric_id: str) -> list[AdversarialExample]:
    """Load adversarial fixtures (with attack_type) for the robustness eval."""
    path = DATA_DIR / "fixtures" / f"{rubric_id}.adversarial.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[AdversarialExample] = []
    for ex in raw["examples"]:
        outcomes = {
            cid: CriterionOutcome(val) for cid, val in ex["teacher_outcomes"].items()
        }
        out.append(
            AdversarialExample(
                example=GradedExample(
                    id=ex["id"],
                    rubric_id=raw["rubric_id"],
                    answer_text=ex["answer_text"],
                    teacher_outcomes=outcomes,
                ),
                attack_type=ex.get("attack_type", "unknown"),
            )
        )
    return out
