# Human-in-the-loop review

Reference implementation of the project's central non-negotiable: **the tool
proposes, the teacher decides.** Foundational and offline — standard library only,
no web framework, no model, no GPU. It models the *concept* end-to-end so it can be
studied, tested, and audited.

This is **not** a product teacher-dashboard. A production UI belongs in a separate
product repository. The demo interface here is a plain CLI at `ui/review_cli.py`.

## Flow

```
ProposedGrade (+ EscalationDecision from Track A)
    → ReviewRequest
    → route()            AUTO_ACCEPT  or  ESCALATE_TO_HUMAN
    → TeacherDecision    approve / override   (the human decision is authoritative)
    → append-only JSONL audit record   (reports/grading-audit/)
    → override-rate summary            (feeds hypothesis H4)
```

An escalated grade **cannot** be finalised without a `TeacherDecision` — the pipeline
raises if one is missing, enforcing human oversight in code, not just in docs.

## Modules

| File | Responsibility |
|---|---|
| `review.py` | `ReviewRequest`, `TeacherDecision`, routing (`route`, `route_all_to_human`), `approve`/`override` helpers |
| `audit_log.py` | Append-only JSONL `AuditLog`, `build_record`, `OverrideRateSummary` |
| `pipeline.py` | `process_review` — route → (human decides if escalated) → record |

## What each stakeholder gets

| Stakeholder | Value from this layer |
|---|---|
| **Teacher / tutor** | Proposes vs. decides: they approve or override; escalated items require their judgement. |
| **Content author** | Overrides + escalation reasons reveal which rubric criteria the model got wrong or graded for spurious reasons — raw material for rubric optimisation. |
| **Compliance auditor** | Every routing + human decision is an immutable, timestamped audit record with its rationale. |
| **Product owner** | Override rate and escalation rate over time — the H4 signal ("does teacher intervention shrink as rubrics/context improve?"). |

## Compliance caveat

This provides audit-log **infrastructure**, not legal compliance. Automated grading is
classified High-Risk under frameworks such as the EU AI Act, and conformity is an
organisational process (documentation, risk management, human-oversight procedures,
contestability). This module supplies one technical ingredient — a traceable decision
log with enforced human oversight — not a compliance guarantee.

## Try it

```bash
python -m ui.review_cli
```

Runs the WWI fixtures through the Track A interpretable grader, shows proposed grades
and escalation reasons, simulates teacher decisions on escalated items, and prints the
override-rate summary.
