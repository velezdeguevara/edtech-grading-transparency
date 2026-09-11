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

## Quickstart (runs on any laptop, no GPU)

```bash
pip install -r requirements.txt          # numpy, einops, jaxtyping, pytest
python -m evals.run_all                   # runs the full eval suite + escalation demo
python -m pytest -q                       # 36 tests
```

`run_all` scores a baseline grader (agreement / calibration / bias-fairness) and then runs
the Track A **interpretability-driven escalation** eval in Mode 1 — the offline "proof" that
needs no model or GPU (see [Run modes](#run-modes)).

**Headline result (Mode 1, placeholder artifacts):** interpretability-based escalation
outperforms a confidence-only baseline at catching grades that rely on spurious features
(length / confident tone) rather than rubric content — accuracy **0.83 vs 0.67**, catching the
spurious probe case with full recall. This is the concrete demonstration that interpretability
is *functional*. The numbers become genuine (not placeholder) after a cloud run generates real
captures.

## Run modes

The same code runs in three environments (details in `docs/running-modes.md`):

| Mode | Hardware | Model | Purpose |
|------|----------|-------|---------|
| **1. Offline proof** | any laptop, no GPU | none (precomputed artifacts) | prove the interp pipeline + escalation logic work; runs in CI |
| **2. Local real** | enough RAM / a GPU | GPT-2-small → Gemma-2-2b | run actual mech-interp locally |
| **3. Cloud** | cloud GPU | Gemma-2-2b + Gemma Scope SAEs | full-fidelity study; generates the Mode 1 artifacts |

Force a mode with `INTERP_MODE=artifact|local|cloud`; it auto-detects and falls back to Mode 1.

## How to read this repo

| Path | What's there | Status |
|---|---|---|
| `docs/design.md` | Architecture + the explainability-vs-interpretability distinction | ✅ |
| `docs/thesis-and-hypotheses.md` | Falsifiable hypotheses (H1–H5) and success metrics | ✅ |
| `docs/auditability.md` | What an auditor can/can't be told under each track | ✅ |
| `docs/running-modes.md` | The three run modes and hardware needs | ✅ |
| `docs/threat-model.md` | Adversarial & safety considerations | ✅ |
| `src/common/grading/` | Shared schema, model-agnostic `Grader` interface, keyword baseline | ✅ |
| `src/common/rubrics/` | Rubric + fixture loaders | ✅ |
| `src/common/rag/` | Retrieval of rubric criteria / references | 🔲 planned |
| `src/common/human_review/` | Override capture, approval, escalation routing | 🔲 planned |
| `src/track_a_interpretable/` | Interp backends (artifact / torch), escalation logic, interpretable grader | ✅ |
| `src/track_b_explainable/` | Vendor-neutral grader + OpenAI-compatible / mock providers | ✅ |
| `evals/agreement`, `calibration`, `bias_fairness`, `auditability` | The scientific centerpiece | ✅ |
| `evals/robustness/` | Adversarial answers, prompt injection | 🔲 planned |
| `interpretability/` | Cloud notebook + technique write-ups (logit lens, SAEs, patching, attention) | ◑ notebook stub; techniques planned |
| `data/` | Example rubrics + **synthetic** fixtures + placeholder interp artifacts | ✅ |
| `ui/` | Demo: take an example test, see grade + explanation + interpretability view | 🔲 planned |
| `reports/` | Interp findings + grading-audit / comparison write-ups | 🔲 planned |

Legend: ✅ implemented · ◑ partial/stub · 🔲 planned

## Non-negotiables

- **Human-in-the-loop is mandatory** — the tool proposes, the teacher decides.
- **Structured, decomposable grades** — per-criterion, with evidence, inspectable and overridable.
- **No real student data** — fixtures are synthetic; no PII in the repository.

## Status

**Implemented and tested (36 passing tests):** the shared grading contract and rubric/fixture
loaders; the full eval suite (agreement, calibration, bias-fairness, and the H3 escalation
eval); the vendor-neutral Track B grader (mock default + OpenAI-compatible provider); and the
Track A interpretability groundwork (artifact backend for Mode 1, torch-lazy backend for
Modes 2/3, escalation policy, and the interpretable grader that flags spurious-reliance).

**Planned next:** the human-review layer (consume the escalation flag), the RAG layer, the
`robustness` eval, real model runs (Track B via API; Track A/Mode 3 via the cloud notebook to
replace placeholder artifacts with genuine Gemma captures), and the demo UI.
