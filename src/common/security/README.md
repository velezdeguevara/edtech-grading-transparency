# Security — defence-in-depth against prompt injection

Pre-grading defences that run **before** the grader, so untrusted student text is
harder to weaponize. Two layers, following the pattern used across the repo (zero-dep
core + optional heavier tier).

## Golden rule

**You cannot use an LLM to protect an LLM from injection.** An "LLM-as-a-judge" security
check is a recursive vulnerability — the attacker just injects the judge. So the layers
here are (1) deterministic code and (2) a *classifier* that only labels text, never
follows it.

## Layer 1 — deterministic sanitization + nonce spotlighting (core, zero-ML)

`sanitize.py`. Always active, pure standard library.

- **Sanitization** neutralizes delimiter/role tokens (`</STUDENT_ANSWER>`, `<system>`,
  `<assistant>`, …) in the untrusted answer, so a student cannot "escape" the block.
  (This fixes a real escape via our former static tag — see fixture `adv04`.)
- **Spotlighting** wraps the answer in a per-call **random nonce**
  (`<NONCE_xxxx_START> … <NONCE_xxxx_END>`) with an instruction that everything between
  the markers is *data, never commands*. The student cannot predict the nonce, so cannot
  forge a closing marker.

Wired into `ExplainableGrader._build_user_prompt`, replacing the old static tag.

## Layer 2 — optional local injection classifier (optional ML tier)

`guardrail.py`. Lazy-loaded, behind `requirements-security.txt`.

- Uses a small **sequence-classification** model (default
  `protectai/deberta-v3-small-prompt-injection-v2`) — it *classifies* benign vs.
  injection, it does not generate/obey text. CPU-friendly, local.
- Lazy-imported: importing the module never fails without the deps; only `check()` does,
  with a clear message. The core (Layer 1) runs without any install.

```bash
pip install -r requirements-security.txt   # optional; model downloads on first use
```

## Pipeline integration

On a detected injection, the flow does **not** crash and does **not** let the model
finalize the grade. `security_violation_grade()` produces a conservative proposal
(all criteria `not_met`) with `security_violation=True`; the human-review `route()`
**escalates it to a teacher**. The human decides — the classifier verdict is advisory.
The audit log records `security_violation`, so auditors/reports can count attack
escalations. `security_violation` is kept **distinct** from `spurious_reliance_flag` so
"attempted an attack" is not conflated with "gamed the content".

## ⚠️ Honest limits (read this)

- **This is defence-in-depth, not a solution.** Prompt injection is an **open industry
  problem**. These layers *raise the bar*; they do not guarantee safety.
- **No accuracy figure is a guarantee.** A classifier's benchmark accuracy is measured on
  its own test set — not on novel or adaptive attacks. Classifiers can be evaded
  (adversarial ML).
- **Human-in-the-loop is the backstop.** Every detection escalates to a human; the tool
  never finalizes a security-flagged grade on its own (consistent with EU-AI-Act human
  oversight expectations for high-risk systems).
- Layers can be added/strengthened over time; this is a foundation, not a ceiling.

See `docs/threat-model.md` (T1) and `evals/robustness/README.md`.
