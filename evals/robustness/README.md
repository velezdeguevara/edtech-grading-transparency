# Robustness eval

Measures how well a grader resists **adversarial student answers** — prompt injection,
keyword stuffing, length/tone gaming, and related attacks — whose *correct* grade is
low. It reports, per attack **category** and overall:

- **resistance rate** — how often the grader is NOT fooled into over-scoring;
- **mean over-score** — average points awarded above the correct total;
- **(Track A) escalation-catch rate** — how often interpretability-driven escalation
  flags the attack for human review, even if the base grade was fooled.

Fixtures: `data/fixtures/<rubric_id>.adversarial.json` (labelled by `attack_type`).

## ⚠️ This is not a safety guarantee — read this

**Prompt injection is an unsolved, open industry problem.** No fixture set — and no
number of fixtures — yields a "percentage of protection." This eval measures resistance
to a **taxonomy of *known* attack categories**, not completeness. A passing result means
"resists the attacks we thought to test," never "safe against attacks we did not
imagine." The attack space is unbounded and adversarial; attackers invent new phrasings,
encodings, and multi-step strategies faster than any list can enumerate.

Treat these results as **regression protection and a comparison instrument** (Track A vs
Track B on the same attacks), and as a **demonstration of the escalation mechanism** —
not as a security certification.

## Attack taxonomy covered (representative, not exhaustive)

direct instruction override · fake system/role injection · keyword stuffing · length
gaming · tone/confidence gaming · mixed content + injection · encoding/obfuscation
(leetspeak, base64) · delimiter/format attacks (fake JSON, fake turns) · multilingual
injection · authority spoofing · roleplay framing · emotional manipulation.

New categories and variants should be *added over time* — the taxonomy is meant to grow.

## Defence-in-depth (where real protection comes from)

Robustness is **one layer**. Genuine protection is architectural and layered; this repo
demonstrates several of these, but no single one is sufficient:

1. **Input/instruction separation** — untrusted student text is delimited
   (`<STUDENT_ANSWER>…</STUDENT_ANSWER>`) and never treated as instructions. (Can be
   hardened further.)
2. **Rubric-grounded, structured output contract** — the grader only emits per-criterion
   outcomes with evidence, limiting what an injection can achieve.
3. **Interpretability-driven escalation (Track A)** — grades relying on injected/spurious
   features are flagged to a human. This is the differentiating layer, and why the
   escalation-catch column matters even when the base grade is fooled.
4. **Human-in-the-loop** — the ultimate backstop: the tool proposes, the teacher decides.
5. **Input sanitisation/detection** — useful as *one* layer, never the only one.

See `docs/threat-model.md` (T1 prompt injection, T2 gaming) for the threat framing, and
`docs/design.md` for the architecture.

## Honesty note on the shipped numbers

In Mode 1 the escalation-catch uses **synthetic placeholder** interpretability artifacts
(clearly labelled). They demonstrate the *mechanism*; genuine numbers require a Mode 3
cloud run that replaces the placeholders with real Gemma captures. The base-grader
resistance numbers, by contrast, are real (they depend only on the grader, not on
interpretability artifacts).
