# Thesis & Hypotheses

## Research question

Is it **affordable, at professional scale**, to build a Social Science automatic grading
tool that is *interpretable by design* (open-weight + mechanistic interpretability), or is
it better to accept a *non-interpretable* frontier model made trustworthy through
*explainability + human-in-the-loop + strong rubrics + RAG* — driving teacher intervention
low enough that the freed time is reinvested in tutoring, class preparation, and student
attention?

This is an applied **AI-safety** question: it is about *how to earn justified trust* in an
automated judgment used in a real educational setting, and what that trust costs in
auditability.

## Two tracks under test

- **Track A — Interpretable by design.** Open-weight model. Mechanistic interpretability
  (activation patching, attention analysis, SAEs, logit lens) is used to audit *why* a grade
  was produced and to drive a **trust/escalation signal**.
- **Track B — Explainable + human-in-the-loop.** Frontier (vendor-neutral) model. No
  mechanistic access; trust rests on post-hoc explanation, rubrics, RAG, and mandatory teacher
  review.

Both tracks share `src/common` scaffolding and the **same `evals/` harness**.

---

## Hypotheses (falsifiable)

**H1 — Grading quality.**
Track B (frontier) achieves higher agreement with teacher ground-truth grades than the
fully-interpretable Track A small model, on open-ended Social Science answers.
*Falsified if* Track A (interpretable) matches Track B within a pre-registered margin.

**H2 — The interpretability cost.**
There is a measurable gap between the *fully-interpretable* Track A model (Gemma-2-2b class)
and a *usable* open-weight grader (9–14B class). The size of this gap quantifies the "price of
interpretability by design."
*Falsified if* the small interpretable model grades acceptably with no meaningful gap.

**H3 — Interpretability as a trust signal.**
For Track A, mech-interp can detect grades that rely on **spurious features** (length, tone,
irrelevant tokens), and escalating exactly those grades to teachers improves reliability more
than random or confidence-only escalation of the same volume.
*Falsified if* interp-based escalation is no better than a confidence-threshold baseline.

**H4 — Diminishing teacher intervention.**
As rubrics and RAG context improve, the teacher **override rate** falls toward a low plateau,
and the residual overrides concentrate on genuinely ambiguous/argumentative answers.
*Falsified if* override rate does not fall, or falls without concentrating on ambiguous cases.

**H5 — Auditability ceiling.**
Track B's explanations, however good, cannot answer certain auditor questions that Track A can
(e.g. "prove the grade did not depend on writing style"). The `auditability` eval will show a
class of questions answerable only under Track A.
*Falsified if* post-hoc explanation answers the same auditor questions to the same depth.

---

## Success metrics (identical across both tracks)

| Dimension | Metric | Eval location |
|---|---|---|
| Grading quality | Agreement with teacher grades (exact + within-1); per-criterion accuracy | `evals/agreement/` |
| Calibration | Confidence vs. correctness; reliability curves; ECE | `evals/calibration/` |
| Bias / fairness | Sensitivity to answer length, tone, style, demographic proxies | `evals/bias_fairness/` |
| Robustness | Behavior on adversarial answers & prompt injection in student text | `evals/robustness/` |
| Auditability | Depth-of-explanation an auditor can obtain; questions answerable per track | `evals/auditability/` |
| Human effort | Teacher override rate; time-to-review; residual-case difficulty | `reports/grading-audit/` |

A result is only valid if produced by the **same harness on the same items** for both tracks.

---

## What "affordable at professional scale" means here

- **Compute & latency:** open-weight hosting + interp analysis vs. frontier API cost/latency.
- **Engineering effort:** building and maintaining mech-interp tooling vs. prompt/RAG engineering.
- **Auditability delivered per unit effort:** how much *justified trust* each path yields.
- **Residual human cost:** teacher time still required under each track (ties to H4).

The deliverable for tech venues is not "which model is best" but a defensible answer to
*"for a professional EdTech grader, is interpretability-by-design worth its cost, or is
explainability-plus-human-in-the-loop the pragmatic path — and where is the crossover?"*

## Intended audience & framing

Summits, universities, and EdTech/AI-safety practitioners. The working tool, RAG, human-review
workflow, and demo UI exist to make the evidence **concrete and reproducible**, so claims are
backed by runnable examples rather than assertions.
