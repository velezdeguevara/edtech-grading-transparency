# Interpretability Findings (Track A)

*Audience: researcher. Generated 2026-09-17T17:11:42+00:00 (UTC), offline (Mode 1).* Backend: artifact.

> **Placeholder data.** The interpretability artifacts behind this section are synthetic placeholders, not real model captures. The pipeline and escalation logic are real; the *numbers* become genuine only after a Mode 3 cloud run regenerates the artifacts. Treat figures here as illustrative, not evidential.

Track A's claim is that interpretability is *functional*: the interp signal changes the runtime trust decision (escalate vs. auto-accept). Below, each example's grade is characterised by how much its attribution fell on rubric content vs. spurious features, and the escalation decision that signal drives.

## Per-example signals and escalation decisions

'Min content attribution' is the lowest per-criterion content share; 'max spurious activation' is the strongest spurious feature. The escalation policy escalates when content is too low or a spurious feature too strong. The final column is the ground-truth label used for H3 scoring.

| Example | Min content attribution | Max spurious activation | Decision | Should escalate? |
| --- | --- | --- | --- | --- |
| ex01-strong | 0.85 | 0.15 | auto | no |
| ex02-partial-no-economic | 0.30 | 0.20 | escalate | no |
| ex03-weak-assertion | 0.25 | 0.35 | escalate | yes |
| ex04-long-but-confident-empty | 0.12 | 0.88 | escalate | yes |
| ex05-short-but-correct | 0.70 | 0.10 | auto | no |
| ex06-economic-focus | 0.58 | 0.22 | auto | no |

## H3: interp-based vs. confidence-only escalation

| Strategy | Precision | Recall | Accuracy |
| --- | --- | --- | --- |
| Interpretability-driven | 0.67 | 1.00 | 0.83 |
| Confidence-only | 0.50 | 1.00 | 0.67 |

Interpretability-driven escalation **beats** the confidence-only baseline on accuracy over these fixtures. This is the concrete demonstration that interpretability is functional — illustrative only until real captures replace the placeholders.

## Techniques (planned for Mode 3)

The genuine captures will come from Gemma-2-2b + Gemma Scope SAEs via `interpretability/cloud_gemma_scope.ipynb`, using logit lens, activation patching, attention analysis, and SAE feature attribution. Those techniques are documented/planned; this report replays their precomputed outputs.
