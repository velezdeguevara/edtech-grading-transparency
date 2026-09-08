# edtech-grading-transparency

A comparative study — with a working artifact — of how to earn *justified trust* in an
automatic grading tool for Social Science, and what that trust costs in auditability.

## The question

> For a **professional** EdTech grading tool, is it affordable to be **interpretable by
> design** (an open-weight model the team can audit with mechanistic interpretability), or is
> it better to accept a **non-interpretable frontier model** made trustworthy through
> **explainability + human-in-the-loop + strong rubrics + RAG** — until teacher intervention
> becomes near-insignificant and teachers are freed for tutoring, class prep, and student
> attention?

This is an applied **AI-safety** problem. Interpretability here is **functional**, one arm of
the experiment — not decoration.

## Two tracks

- **Track A — Interpretable by design.** Open-weight model; mechanistic interpretability
  (activation patching, attention analysis, SAEs, logit lens) audits *why* a grade was
  produced and drives a runtime **trust/escalation signal**.
- **Track B — Explainable + human-in-the-loop.** Frontier (vendor-neutral) model; no
  mechanistic access — trust rests on post-hoc explanation, rubrics, RAG, and mandatory
  teacher review.

Both tracks share the same scaffolding (`src/common`) and the **same evaluation harness**
(`evals/`), so the comparison is apples-to-apples.

## How to read this repo

| Path | What's there |
|---|---|
| `docs/design.md` | Architecture + the explainability-vs-interpretability distinction |
| `docs/thesis-and-hypotheses.md` | Falsifiable hypotheses (H1–H5) and success metrics |
| `docs/auditability.md` | What an auditor can/can't be told under each track |
| `docs/threat-model.md` | Adversarial & safety considerations |
| `src/common/` | Shared: rubrics, RAG, grading orchestration, human review |
| `src/track_a_interpretable/` | Open-weight grader + interp integration |
| `src/track_b_explainable/` | Frontier (vendor-neutral) grader + explanation layer |
| `interpretability/` | The research arm: logit lens, SAE maps, activation patching, attention |
| `evals/` | The scientific centerpiece: agreement, calibration, bias, robustness, auditability |
| `data/` | Example rubrics + **synthetic** fixtures (no real student data) |
| `ui/` | Demo: take an example test, see grade + explanation + interpretability view |
| `reports/` | Interp findings + grading-audit / comparison write-ups |

## Non-negotiables

- **Human-in-the-loop is mandatory** — the tool proposes, the teacher decides.
- **Structured, decomposable grades** — per-criterion, with evidence, inspectable and overridable.
- **No real student data** — fixtures are synthetic; no PII in the repository.

## Status

Scaffolding and design docs in place. Implementation of `src/common`, the two tracks, and the
`evals/` harness is in progress.
