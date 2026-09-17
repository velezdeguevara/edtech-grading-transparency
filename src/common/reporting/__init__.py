"""Stakeholder-oriented reporting layer.

Turns the existing eval suite + human-review audit log into offline, stdlib-only
Markdown reports, one per stakeholder role (see ``README.md``):

  - grading-audit summary   -> auditor
  - comparison write-up      -> product owner
  - rubric-optimization      -> content author
  - interp-findings          -> researcher

Every report carries an honesty banner: placeholder interpretability artifacts are
labelled as such, the baseline grader is labelled as a floor (not a promise), and
robustness/security are framed as defence-in-depth, never a guarantee. Nothing here
depends on a model, GPU, or third-party package.
"""

from __future__ import annotations

from src.common.reporting.audit_report import build_grading_audit_report
from src.common.reporting.comparison_report import build_comparison_report
from src.common.reporting.interp_report import build_interp_findings_report
from src.common.reporting.rubric_report import build_rubric_optimization_report

__all__ = [
    "build_grading_audit_report",
    "build_comparison_report",
    "build_rubric_optimization_report",
    "build_interp_findings_report",
]
