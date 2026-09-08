# Auditability: What an Auditor Can Be Told Under Each Track

This document frames the transparency claim that ultimately matters in a professional EdTech
setting: **when an auditor, regulator, school board, or parent asks "why did the student get
this grade, and can you prove the system is fair?", what can each track honestly answer?**

It is the qualitative counterpart to `evals/auditability/`.

## Audit questions we hold both tracks against

1. **Grade justification** — "Why this grade for this answer?"
2. **Criterion attribution** — "Which rubric criteria were met, and on what evidence?"
3. **Fairness — style** — "Prove the grade did not depend on answer length, tone, or writing polish."
4. **Fairness — proxies** — "Prove the grade did not depend on demographic proxies in the text."
5. **Consistency** — "Would a similar answer get a similar grade?"
6. **Failure detection** — "How do you catch cases where the model graded for the wrong reasons?"
7. **Recourse** — "What happens when the system is wrong?"

## Track A — Interpretable by design (open-weight + mech-interp)

| Question | What we can tell the auditor | Basis |
|---|---|---|
| Grade justification | Structured per-criterion breakdown + evidence spans | output structure |
| Criterion attribution | Same, plus **causal** confirmation via activation patching | mech-interp |
| Fairness — style | Can present **evidence** that score is/ isn't causally driven by length/tone features | activation patching, SAE features, attention |
| Fairness — proxies | Can inspect for features correlated with proxies and test causal influence | SAE feature maps, probing |
| Consistency | Behavioral testing + internal-feature similarity | evals + interp |
| Failure detection | Spurious-feature grades are **flagged and escalated at runtime** | interp trust signal |
| Recourse | Human-in-the-loop override; escalation triggered by interp signal | human_review |

**Strength:** can make *mechanistic* claims — e.g. "the grade did not causally depend on
answer length" — that are evidence-backed, not merely asserted.
**Cost:** requires open-weight models (weaker graders), plus the engineering to build and
maintain interp tooling and to keep interp findings valid as models change.

## Track B — Explainable + human-in-the-loop (frontier, vendor-neutral)

| Question | What we can tell the auditor | Basis |
|---|---|---|
| Grade justification | Structured per-criterion breakdown + evidence spans | output structure |
| Criterion attribution | Rubric-grounded justification with cited evidence | prompting + RAG |
| Fairness — style | Can show **behavioral** evidence (controlled tests: vary length/tone, observe grade) but **cannot** prove internal independence | evals only |
| Fairness — proxies | Behavioral testing only; no access to internals | evals only |
| Consistency | Behavioral testing across similar answers | evals |
| Failure detection | Confidence/uncertainty thresholds + human review; no mechanistic detection | heuristics + human_review |
| Recourse | Human-in-the-loop override (mandatory) | human_review |

**Strength:** strongest available grading quality; explanations are rubric-grounded and
usable; human-in-the-loop provides real recourse.
**Cost / honest limit:** every fairness claim is **behavioral and post-hoc**. We can show the
system *behaved* fairly on tested inputs; we cannot prove *why* internally. Some auditor
questions (Q3–Q4 at the mechanistic level, Q6) are answerable only up to behavioral evidence.

## The crossover this project is trying to locate

- Track A buys **mechanistic, provable** transparency at the cost of grading quality and
  engineering effort.
- Track B buys **grading quality and simplicity** at the cost of only-behavioral transparency.
- Human-in-the-loop + rubrics + RAG can raise Track B's *practical* trust substantially — the
  open question (H4/H5) is whether it rises far enough that the loss of mechanistic
  auditability is acceptable for a professional deployment, and where the line sits for
  different stakes (formative quizzes vs. high-stakes exams).

The `evals/auditability/` harness turns this table into scored, reproducible evidence rather
than opinion.
