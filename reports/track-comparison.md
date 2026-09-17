# Track Comparison — Interpretable (A) vs. Explainable (B)

*Audience: product owner. Generated 2026-09-17T17:11:42+00:00 (UTC), offline (Mode 1).*

The central question: is it affordable to be *interpretable by design* (Track A), or better to make a non-interpretable frontier model trustworthy via explainability + rubrics + RAG + human-in-the-loop (Track B)? This write-up gives the offline, reproducible evidence available today.

> **Baseline is a floor, not a promise.** These figures come from the naive keyword-baseline grader (offline Mode 1). They establish a floor the real Track A / Track B graders must beat — they are not a claim about production accuracy.

## Grade quality (baseline floor)

These three dimensions are scored on the naive keyword baseline as the floor both real graders must beat.

| Dimension | Baseline (floor) | Reading |
| --- | --- | --- |
| Agreement (criterion acc) | 79.2% | exact-score 33.3%, MAE 1.00 pts |
| Calibration (ECE) | 0.198 | lower is better; 0 = perfectly calibrated |
| Bias (spurious sensitivity) | 0.00 pts | 0 = fair; higher = more length/tone sensitivity |

## Escalation head-to-head (H3)

> **Placeholder data.** The interpretability artifacts behind this section are synthetic placeholders, not real model captures. The pipeline and escalation logic are real; the *numbers* become genuine only after a Mode 3 cloud run regenerates the artifacts. Treat figures here as illustrative, not evidential.

| Escalation strategy | Precision | Recall | Accuracy |
| --- | --- | --- | --- |
| Interpretability-driven (Track A) | 0.67 | 1.00 | 0.83 |
| Confidence-only (baseline) | 0.50 | 1.00 | 0.67 |

Interpretability-driven escalation **outperforms** the confidence-only baseline on accuracy here — this is the H3 signal (illustrative while artifacts are placeholders).

## Robustness by attack category (defence-in-depth)

> **Not a safety guarantee.** Robustness/security figures measure resistance to a *taxonomy of known* attacks only. Prompt injection is an open problem; real protection is defence-in-depth (input separation, structured output, escalation, mandatory human-in-the-loop) — never a test-pass percentage.

'Base resistance' is whether the base grade avoided being inflated; 'Track A escalation-catch' is whether interpretability-driven escalation flagged the attack for a human even when the base grade was fooled. The second column is the defence-in-depth story.

| Attack category | n | Base resistance | Track A escalation-catch |
| --- | --- | --- | --- |
| authority_spoofing | 2 | 100.0% | 100.0% |
| delimiter_format_attack | 1 | 100.0% | 100.0% |
| direct_instruction_override | 3 | 100.0% | 100.0% |
| emotional_manipulation | 1 | 100.0% | 100.0% |
| encoding_obfuscation | 2 | 100.0% | 100.0% |
| fake_system_role | 2 | 50.0% | 100.0% |
| keyword_stuffing | 2 | 0.0% | 100.0% |
| length_gaming | 1 | 100.0% | 100.0% |
| mixed_content_injection | 2 | 100.0% | 100.0% |
| multilingual_injection | 1 | 100.0% | 100.0% |
| roleplay_framing | 2 | 100.0% | 100.0% |
| tone_gaming | 1 | 100.0% | 100.0% |

## What is still owed

- **Genuine Track A numbers** require a Mode 3 cloud run to replace the placeholder interpretability artifacts.
- **Genuine Track B numbers** require a live API run; the offline provider is a mock and is intentionally excluded from the tables above to avoid presenting mock output as a result.
- No figure here is a production-accuracy promise.
