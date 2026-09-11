"""Tests for Track A: backend, capability detection, escalation, grader, and eval."""

from __future__ import annotations

import pytest

from evals.auditability.metric import SHOULD_ESCALATE, evaluate_escalation
from src.common.rubrics.loader import load_fixtures, load_rubric
from src.track_a_interpretable.artifact_backend import ArtifactBackend
from src.track_a_interpretable.backend import InterpSignal
from src.track_a_interpretable.capability import detect_mode, get_backend
from src.track_a_interpretable.escalation import (
    EscalationPolicy,
    confidence_only_decision,
)
from src.track_a_interpretable.grader import InterpretableGrader

RUBRIC_ID = "ss-wwi-causes-v1"


def _rubric_and_examples():
    return load_rubric(RUBRIC_ID), load_fixtures(RUBRIC_ID)


# --- InterpSignal ---

def test_interp_signal_aggregates():
    sig = InterpSignal(
        content_attribution={"a": 0.9, "b": 0.4},
        spurious_feature_activation={"tone": 0.7, "length": 0.2},
    )
    assert sig.max_spurious() == 0.7
    assert sig.min_content_attribution() == 0.4


def test_empty_signal_is_neutral():
    sig = InterpSignal()
    assert sig.max_spurious() == 0.0
    assert sig.min_content_attribution() == 1.0


# --- Capability detection ---

def test_detect_mode_respects_env(monkeypatch):
    monkeypatch.setenv("INTERP_MODE", "artifact")
    assert detect_mode() == "artifact"


def test_detect_mode_rejects_invalid(monkeypatch):
    monkeypatch.setenv("INTERP_MODE", "banana")
    with pytest.raises(ValueError):
        detect_mode()


def test_get_backend_local_falls_back_when_torch_missing(monkeypatch):
    # torch is not installed in the core venv, so requesting 'local' must degrade.
    monkeypatch.delenv("INTERP_MODE", raising=False)
    backend = get_backend("local")
    assert backend.mode == "artifact"  # graceful fallback


# --- Artifact backend (Mode 1) ---

def test_artifact_backend_reads_probe_signal():
    backend = ArtifactBackend()
    sig = backend.signal_for(RUBRIC_ID, "ex04-long-but-confident-empty", "irrelevant")
    # ex04 is the spurious probe: high spurious, low content.
    assert sig.max_spurious() > 0.5
    assert sig.min_content_attribution() < 0.5


def test_artifact_backend_marks_placeholder():
    backend = ArtifactBackend()
    assert backend.is_placeholder(RUBRIC_ID) is True


def test_artifact_backend_unknown_example_is_neutral():
    backend = ArtifactBackend()
    sig = backend.signal_for(RUBRIC_ID, "does-not-exist", "x")
    assert sig.max_spurious() == 0.0
    assert sig.min_content_attribution() == 1.0


# --- Escalation policy ---

def test_policy_escalates_on_high_spurious():
    policy = EscalationPolicy()
    sig = InterpSignal(
        content_attribution={"a": 0.9},
        spurious_feature_activation={"tone": 0.9},
    )
    assert policy.decide(sig).escalate is True


def test_policy_no_escalation_when_content_driven():
    policy = EscalationPolicy()
    sig = InterpSignal(
        content_attribution={"a": 0.9, "b": 0.85},
        spurious_feature_activation={"tone": 0.1},
    )
    assert policy.decide(sig).escalate is False


def test_confidence_only_baseline():
    assert confidence_only_decision(0.4, threshold=0.6).escalate is True
    assert confidence_only_decision(0.9, threshold=0.6).escalate is False


# --- Track A grader ---

def test_track_a_flags_spurious_example():
    rubric, _ = _rubric_and_examples()
    grader = InterpretableGrader(backend=ArtifactBackend())
    graded, decision = grader.grade_example(
        rubric, "ex04-long-but-confident-empty", "irrelevant"
    )
    assert decision.escalate is True
    assert graded.spurious_reliance_flag is True


def test_track_a_does_not_flag_content_driven():
    rubric, _ = _rubric_and_examples()
    grader = InterpretableGrader(backend=ArtifactBackend())
    graded, decision = grader.grade_example(
        rubric, "ex05-short-but-correct", "irrelevant"
    )
    assert decision.escalate is False
    assert graded.spurious_reliance_flag is False


# --- Escalation eval (H3) ---

def test_escalation_eval_interp_beats_or_matches_confidence():
    rubric, examples = _rubric_and_examples()
    grader = InterpretableGrader(backend=ArtifactBackend())
    result = evaluate_escalation(grader, rubric, examples)
    # With placeholder artifacts, interp-based should be at least as accurate.
    assert result.interp.accuracy >= result.confidence_only.accuracy
    # ex04 (spurious) must be caught by interp-based escalation (recall on it).
    assert result.interp.recall == 1.0


def test_should_escalate_labels_cover_fixtures():
    _, examples = _rubric_and_examples()
    for ex in examples:
        assert ex.id in SHOULD_ESCALATE
