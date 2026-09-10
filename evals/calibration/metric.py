"""Calibration eval: does a grader's confidence track its correctness?

For each per-criterion assessment, the grader reports a ``confidence`` in [0, 1].
This eval checks whether that confidence is *calibrated*: among assessments the
grader was ~0.8 confident in, roughly 80% should be correct.

Outputs reliability bins and Expected Calibration Error (ECE). This is model-
agnostic and scores any object implementing the ``Grader`` interface, so both
tracks are measured identically. Directly supports the calibration success metric
and informs confidence-based escalation baselines (see docs/thesis-and-hypotheses).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.common.grading.schema import GradedExample, Grader, Rubric


@dataclass
class ReliabilityBin:
    lo: float
    hi: float
    count: int = 0
    correct: int = 0
    confidence_sum: float = 0.0

    @property
    def accuracy(self) -> float:
        return self.correct / self.count if self.count else 0.0

    @property
    def mean_confidence(self) -> float:
        return self.confidence_sum / self.count if self.count else 0.0

    @property
    def gap(self) -> float:
        """|confidence - accuracy| within this bin (0 = perfectly calibrated)."""
        return abs(self.mean_confidence - self.accuracy) if self.count else 0.0


@dataclass
class CalibrationResult:
    grader_name: str
    rubric_id: str
    n_assessments: int
    ece: float  # Expected Calibration Error (lower is better)
    bins: list[ReliabilityBin] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"[{self.grader_name} on {self.rubric_id}] "
            f"ECE={self.ece:.3f}  (n_assessments={self.n_assessments})"
        ]
        for b in self.bins:
            if b.count == 0:
                continue
            lines.append(
                f"  conf[{b.lo:.1f}-{b.hi:.1f}]  n={b.count:2d}  "
                f"mean_conf={b.mean_confidence:.2f}  acc={b.accuracy:.2f}  "
                f"gap={b.gap:.2f}"
            )
        return "\n".join(lines)


def _make_bins(n_bins: int) -> list[ReliabilityBin]:
    edges = [i / n_bins for i in range(n_bins + 1)]
    return [ReliabilityBin(lo=edges[i], hi=edges[i + 1]) for i in range(n_bins)]


def _bin_index(confidence: float, n_bins: int) -> int:
    # Clamp to [0, 1]; the top edge (1.0) falls into the last bin.
    c = min(max(confidence, 0.0), 1.0)
    idx = int(c * n_bins)
    return min(idx, n_bins - 1)


def evaluate_calibration(
    grader: Grader,
    rubric: Rubric,
    examples: list[GradedExample],
    n_bins: int = 5,
) -> CalibrationResult:
    bins = _make_bins(n_bins)
    n_assessments = 0

    for ex in examples:
        proposed = grader.grade(rubric, ex.answer_text)
        for a in proposed.assessments:
            truth = ex.teacher_outcomes.get(a.criterion_id)
            if truth is None:
                continue
            is_correct = a.outcome == truth
            b = bins[_bin_index(a.confidence, n_bins)]
            b.count += 1
            b.confidence_sum += a.confidence
            if is_correct:
                b.correct += 1
            n_assessments += 1

    # ECE = weighted average of per-bin |confidence - accuracy|.
    ece = (
        sum(b.count * b.gap for b in bins) / n_assessments if n_assessments else 0.0
    )
    return CalibrationResult(
        grader_name=grader.name,
        rubric_id=rubric.id,
        n_assessments=n_assessments,
        ece=ece,
        bins=bins,
    )
