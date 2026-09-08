# Design: Architecture & the Explainability–Interpretability Distinction

## Purpose of this repository

This is a **comparative study with a working artifact**, not a single product. It
investigates a concrete question for professional EdTech grading:

> For a *professional* automatic grading tool that teachers will trust, which path
> delivers trustworthy AI:
>
> - **Track A — Interpretable by design**: an *open-weight* model whose internals
>   the team can audit with mechanistic interpretability (mech-interp) techniques; or
> - **Track B — Explainable + human-in-the-loop**: a *frontier* (closed-weight) model
>   that is **not** mechanistically interpretable at any scale, made trustworthy through
>   output-level explanations, strong rubrics, RAG grounding, and human review — to the
>   point where teacher intervention becomes *near-insignificant*.

The grading tool, RAG, human-review workflow, and demo UI exist to **provide real,
concrete evidence** for this comparison. Interpretability here is **functional**, an arm
of the experiment — never decoration.

The broader motivation is an AI-safety one, applied in a real context: if an automated
grader can be made reliable enough that teacher intervention is minimal, teachers are
freed for higher-value work (tutoring, class preparation, individual attention). The
question is at what cost to *auditability* and *trust*, and whether interpretability-by-
design is affordable at professional scale.

---

## The core distinction

These two terms are routinely conflated. This project depends on keeping them separate.

### Explainability (output-level, post-hoc)
Answers: **"Why did the system produce *this* grade, in human terms?"**

Example: *"This answer scored 3/5. The rubric criterion 'identifies economic causes' was
not met; the criteria 'identifies political causes' and 'uses supporting evidence' were
met. Evidence spans are highlighted."*

- Achieved via: structured prompting, rubric-grounded RAG, per-criterion scoring, evidence
  citation, uncertainty surfacing.
- Available for **any** model, including closed frontier models.
- **Post-hoc**: it is a justification constructed around the output. It does *not* prove
  the model internally reasoned this way. An auditor gets a reasonable account of what the
  system did, but not a mechanistic guarantee.

### Mechanistic interpretability (internal-level)
Answers: **"What computation *inside the model's weights* produced this output?"**

Example: *"Activation patching shows the score is causally driven by tokens in the rubric
criterion, not by answer length; an SAE feature that fires on 'confident tone' does not
influence the score."*

- Achieved via: logit lens, activation patching / causal tracing, attention analysis,
  sparse autoencoders (SAEs), probing — the AI Safety / ARENA toolkit.
- Requires **open weights and activations**. Impossible on closed frontier models.
- Provides evidence about *how the model works*, enabling detection of spurious features,
  grading-for-the-wrong-reasons, and hidden failure modes.

### Why the distinction decides the architecture
The models good enough to grade open-ended Social Science answers well (frontier) are the
ones we **cannot** mechanistically interpret. The models we **can** fully interpret today
(small open-weight, e.g. GPT-2-class, Gemma-2-2b with Gemma Scope SAEs) are weaker graders.
Track A and Track B are the two honest responses to this tension, and the study measures
what each buys and costs.

---

## System architecture

Both tracks share the same scaffolding and the **same evaluation harness**, so the
comparison is apples-to-apples. Only the model and the transparency mechanism differ.

```
                    ┌───────────────────────────────────────────┐
                    │              Shared scaffolding             │
                    │  (src/common)                               │
                    │                                             │
  student answer ─► │  rubrics ─► rag ─► grading (model-agnostic) │ ─► proposed grade
                    │                          │                  │     + per-criterion
                    │                          ▼                  │       breakdown
                    │                    human_review             │     + evidence spans
                    │              (approval / override /         │     + uncertainty
                    │               escalation logic)             │
                    └───────────────┬───────────────┬────────────┘
                                    │               │
                        ┌───────────▼───┐   ┌───────▼────────────┐
                        │ Track A        │   │ Track B            │
                        │ interpretable  │   │ explainable        │
                        │ open-weight    │   │ frontier (vendor-  │
                        │ + mech-interp  │   │ neutral) + post-hoc│
                        │ (feeds trust/  │   │ explanation layer  │
                        │  escalation)   │   │                    │
                        └───────┬────────┘   └───────┬────────────┘
                                │                     │
                        ┌───────▼─────────────────────▼───────────┐
                        │                evals                     │
                        │  agreement · calibration · bias-fairness │
                        │  robustness · auditability               │
                        └──────────────────────────────────────────┘
```

### Component responsibilities

| Component | Location | Responsibility |
|---|---|---|
| Rubrics | `src/common/rubrics/` | Rubric schema, parsing, criteria matching. Rubrics are the **authoritative** scoring criteria; the model compares against them, it does not invent standards. |
| RAG | `src/common/rag/` | Retrieve the rubric criteria and reference material relevant to a question. Grounds the grade in explicit, inspectable context. |
| Grading | `src/common/grading/` | Model-agnostic orchestration. Produces **structured** output: per-criterion met/partial/not-met + evidence span + proposed sub-score → aggregated grade. Never free-form prose scores. |
| Human review | `src/common/human_review/` | The tool **proposes**, never **finalizes**. Captures teacher overrides, records approval, houses escalation logic (when to route to a human). |
| Track A | `src/track_a_interpretable/` | Open-weight grader; integrates mech-interp signals. |
| Track B | `src/track_b_explainable/` | Frontier (vendor-neutral) grader + post-hoc explanation layer. |
| Interpretability | `interpretability/` | The research arm (Track A): logit lens, SAE feature maps, activation patching, attention analysis. |
| Evals | `evals/` | The scientific centerpiece; identical metrics across both tracks. |
| Data | `data/` | Example rubrics and **synthetic** fixtures. No real student PII, ever. |
| UI | `ui/` | Demo: take an example test, see grade + explanation + (Track A) interpretability view. Exists to make the evidence tangible in talks. |
| Reports | `reports/` | Interp findings (Track A) and grading-audit/comparison write-ups. |

---

## How interpretability stays functional (not decoration)

For **Track A**, mech-interp is wired into the runtime trust decision, not bolted on:

- **Activation patching / causal tracing** answers *"what did the grade causally depend on?"*
  If the score depends on the rubric criterion and relevant answer spans → higher trust.
  If it depends on answer length, tone, or irrelevant tokens → **spurious**, escalate to teacher.
- **Attention analysis** checks whether the model attends to rubric criteria and evidence
  spans versus irrelevant tokens — "is it grading for the right reasons?"
- **SAEs (Gemma Scope on Gemma-2-2b)** surface interpretable features; we look for
  content features (e.g. "mentions economic causes") versus style/confidence features that
  should not drive a grade.
- **Logit lens** shows how the pass/fail decision forms across layers — primarily for
  auditing and illustration.

The intended payoff: **interpretability output becomes an escalation signal.** A grade that
mech-interp shows to rely on spurious features is automatically flagged for human review.
This is a concrete AI-safety contribution: using interpretability to decide *when to trust
versus escalate* an automated judgment.

For **Track B**, we are explicit and honest: no mechanistic access exists. We produce the
best possible **post-hoc explanation** for an auditor (rubric-grounded justification,
evidence spans, uncertainty) and treat human-in-the-loop + rubrics + RAG as the trust
mechanism. The `evals/auditability/` track scores *how deep* an explanation each approach
can actually give an auditor.

---

## Model choices

### Track A — interpretable, open-weight
- **Deep interpretability work:** **Gemma-2-2b** with **Gemma Scope SAEs**, the best-
  supported target for real mech-interp today (TransformerLens / SAELens / nnsight tooling).
- **"Usable grader" variant:** a larger open-weight instruct model (e.g. Gemma-2-9b-it or a
  comparable 7–14B open-weight instruct model) to represent the strongest grader on which
  interpretability is *still possible in principle*.
- Rationale: retain the option of interpretability while approaching acceptable grading
  quality. The gap between the fully-interpretable small model and the usable open-weight
  model is itself a finding.

### Track B — explainable, frontier (vendor-neutral)
- A **frontier hosted model** (kept vendor-neutral in this repo; e.g. a Claude- / GPT-4-class
  model), accessed via API. The design deliberately avoids hard-coding a vendor so providers
  can be swapped without changing the study.
- No mechanistic interpretability is available at any scale for these models; transparency is
  explainability + human-in-the-loop only.

---

## Non-negotiables

- **Human-in-the-loop is mandatory.** Every proposed grade requires teacher approval. The
  tool proposes; the teacher decides.
- **Structured, decomposable output.** Grades break down into rubric criteria with evidence,
  so they are inspectable and overridable.
- **No real student data.** Fixtures are synthetic. No PII enters the repository.
- **Interpretability is an experimental arm**, either feeding the trust/escalation signal
  (Track A) or explicitly absent and replaced by post-hoc explanation (Track B).

See `docs/thesis-and-hypotheses.md` for the falsifiable hypotheses and success metrics,
`docs/auditability.md` for what an auditor can be told under each track, and
`docs/threat-model.md` for adversarial and safety considerations.
