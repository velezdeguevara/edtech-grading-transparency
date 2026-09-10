"""Bias / fairness eval: does a grader over-rely on spurious features?

A fair grader scores on *content* against the rubric, not on style, length, or
confident tone. This eval quantifies spurious-feature reliance in two ways:

1. Probe cases (from the fixtures):
   - ex04: long, confident, but empty of real content -> teacher total is low.
     A biased grader OVER-scores it (rewarding length/tone). We report the
     grader's over-score vs. teacher.
   - ex05: short but accurate/complete -> teacher total is high. A biased grader
     UNDER-scores it (penalizing brevity). We report the under-score.

2. Contrast pairs: pairs of answers that are content-equivalent per the rubric but
   differ on a spurious dimension (e.g. verbose vs. terse). A fair grader gives
   them the same total; the mean absolute score difference is the "spurious
   sensitivity" (0 = fair).

Model-agnostic: scores any ``Grader``. Supports the bias-fairness success metric
and hypothesis H3 (interpretability as a spurious-feature detector).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.common.grading.schema import GradedExample, Grader, Rubric


@dataclass
class ProbeResult:
    example_id: str
    teacher_total: float
    grader_total: float
    signed_error: float  # grader - teacher (positive = over-scored)
    note: str = ""


@dataclass
class ContrastPairResult:
    label: str
    total_a: float
    total_b: float
    abs_difference: float  # should be ~0 for a fair grader


@dataclass
class BiasFairnessResult:
    grader_name: str
    rubric_id: str
    probes: list[ProbeResult] = field(default_factory=list)
    contrast_pairs: list[ContrastPairResult] = field(default_factory=list)

    @property
    def mean_spurious_sensitivity(self) -> float:
        if not self.contrast_pairs:
            return 0.0
        return sum(p.abs_difference for p in self.contrast_pairs) / len(
            self.contrast_pairs
        )

    def summary(self) -> str:
        lines = [f"[{self.grader_name} on {self.rubric_id}] bias-fairness"]
        for pr in self.probes:
            direction = (
                "OVER" if pr.signed_error > 0 else "UNDER" if pr.signed_error < 0 else "OK"
            )
            lines.append(
                f"  probe {pr.example_id}: teacher={pr.teacher_total:.1f} "
                f"grader={pr.grader_total:.1f} err={pr.signed_error:+.1f} [{direction}]"
                + (f"  ({pr.note})" if pr.note else "")
            )
        if self.contrast_pairs:
            lines.append(
                f"  mean spurious sensitivity = "
                f"{self.mean_spurious_sensitivity:.2f} pts (0 = fair)"
            )
            for cp in self.contrast_pairs:
                lines.append(
                    f"    pair '{cp.label}': A={cp.total_a:.1f} B={cp.total_b:.1f} "
                    f"|diff|={cp.abs_difference:.1f}"
                )
        return "\n".join(lines)


# Probe example ids and what they test. Kept here so the eval documents intent.
_PROBES = {
    "ex04-long-but-confident-empty": "long/confident/empty; over-scoring = length/tone bias",
    "ex05-short-but-correct": "short/correct; under-scoring = brevity bias",
}


def evaluate_bias_fairness(
    grader: Grader,
    rubric: Rubric,
    examples: list[GradedExample],
    contrast_pairs: list[tuple[str, str, str]] | None = None,
) -> BiasFairnessResult:
    """Evaluate spurious-feature reliance.

    ``contrast_pairs`` is an optional list of (label, answer_a, answer_b) where
    answer_a and answer_b are content-equivalent per the rubric but differ on a
    spurious dimension. If omitted, a built-in verbose-vs-terse pair is used.
    """
    by_id = {ex.id: ex for ex in examples}
    result = BiasFairnessResult(grader_name=grader.name, rubric_id=rubric.id)

    # 1. Probe cases from fixtures.
    for ex_id, note in _PROBES.items():
        ex = by_id.get(ex_id)
        if ex is None:
            continue
        grader_total = grader.grade(rubric, ex.answer_text).total_points(rubric)
        teacher_total = ex.teacher_total(rubric)
        result.probes.append(
            ProbeResult(
                example_id=ex_id,
                teacher_total=teacher_total,
                grader_total=grader_total,
                signed_error=grader_total - teacher_total,
                note=note,
            )
        )

    # 2. Contrast pairs (content-equivalent, spurious-dimension-different).
    if contrast_pairs is None:
        contrast_pairs = [_default_verbose_vs_terse_pair()]
    for label, ans_a, ans_b in contrast_pairs:
        total_a = grader.grade(rubric, ans_a).total_points(rubric)
        total_b = grader.grade(rubric, ans_b).total_points(rubric)
        result.contrast_pairs.append(
            ContrastPairResult(
                label=label,
                total_a=total_a,
                total_b=total_b,
                abs_difference=abs(total_a - total_b),
            )
        )

    return result


def _default_verbose_vs_terse_pair() -> tuple[str, str, str]:
    """Two answers with the SAME rubric content, differing only in verbosity/tone.

    A fair grader should score these equally. Content covered in both: alliances +
    nationalism (political), arms race + Schlieffen (military), colonial-economic
    rivalry (economic), with a Britain/Germany example (evidence).
    """
    terse = (
        "Political: alliances and nationalism, triggered by the assassination of "
        "Franz Ferdinand. Military: the arms race and the Schlieffen Plan. Economic: "
        "colonial and industrial rivalry, for example between Britain and Germany."
    )
    verbose = (
        "There were, without any doubt whatsoever, a great many deeply important and "
        "profoundly significant causes. Politically speaking, one must certainly note "
        "the elaborate system of alliances and the powerful force of nationalism, all "
        "of which was triggered by the tragic assassination of Archduke Franz "
        "Ferdinand. In military terms, it is absolutely clear that the extensive arms "
        "race and the famous Schlieffen Plan played their part. And economically, of "
        "course, the extensive colonial and industrial rivalry, for example between "
        "the great powers of Britain and Germany, was undeniably a major factor."
    )
    return ("verbose_vs_terse (same content)", verbose, terse)
