"""Vendor-neutral LLM provider abstraction for the explainable (Track B) grader.

The grader depends only on the ``Provider`` protocol: given a system prompt and a
user prompt, return the model's text response. This keeps the study vendor-neutral —
any backend that can produce text can be plugged in.

Two providers are included:

- ``MockProvider``  — offline, deterministic, NO API key. Default. Lets the harness
  and tests run without network access. It reads the rubric criteria embedded in the
  prompt and returns rubric-shaped JSON so the full parse path is exercised.
- ``OpenAICompatibleProvider`` — targets the de-facto-standard OpenAI
  chat-completions API shape (OpenAI, vLLM, Ollama's OpenAI endpoint, LM Studio,
  many gateways). Base URL, model, and API key come from ENVIRONMENT VARIABLES only;
  no secret is ever read from or written to the repository.

Environment variables for the HTTP provider:
    GRADER_API_BASE   e.g. https://api.openai.com/v1  (or http://localhost:11434/v1)
    GRADER_MODEL      e.g. gpt-4o-mini / llama3.1 / any model the endpoint serves
    GRADER_API_KEY    the secret; never commit this. Some local servers ignore it.
"""

from __future__ import annotations

import json
import os
import re
from typing import Protocol


class Provider(Protocol):
    """Minimal text-in/text-out contract the grader depends on."""

    name: str

    def complete(self, system_prompt: str, user_prompt: str) -> str:  # pragma: no cover
        ...


# --------------------------------------------------------------------------- #
# Mock provider (offline, deterministic, default)
# --------------------------------------------------------------------------- #

# Content cues per criterion, mirroring the WWI rubric. The mock is intentionally
# a bit smarter than the keyword baseline so it exercises PARTIAL/MET/NOT_MET and
# produces confidences, but it is NOT a real model.
_MOCK_CUES: dict[str, list[str]] = {
    "political": ["alliance", "nationalism", "franz ferdinand", "assassinat"],
    "military": ["arms race", "militaris", "mobiliz", "schlieffen", "naval"],
    "economic": ["econom", "coloni", "imperial", "industrial", "trade"],
    "evidence": ["for example", "for instance", "such as", "britain", "germany"],
}


class MockProvider:
    """Deterministic offline provider. Returns rubric-shaped JSON.

    It parses the criterion ids out of the user prompt (which the grader embeds) and
    scores each by counting content cues in the answer, so the grader's JSON parsing
    and mapping into ProposedGrade is fully exercised without any network call.
    """

    name = "mock"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        answer = _extract_block(user_prompt, "STUDENT_ANSWER")
        criterion_ids = _extract_criterion_ids(user_prompt)
        low = answer.lower()

        assessments = []
        for cid in criterion_ids:
            cues = _MOCK_CUES.get(cid, [])
            hits = sum(1 for cue in cues if cue in low)
            if hits >= 2:
                outcome, conf = "met", 0.9
            elif hits == 1:
                outcome, conf = "partial", 0.6
            else:
                outcome, conf = "not_met", 0.8
            span = ""
            for cue in cues:
                idx = low.find(cue)
                if idx != -1:
                    span = answer[max(0, idx - 15) : idx + len(cue) + 15].strip()
                    break
            assessments.append(
                {
                    "criterion_id": cid,
                    "outcome": outcome,
                    "evidence_span": span,
                    "confidence": conf,
                }
            )
        return json.dumps({"assessments": assessments})


# --------------------------------------------------------------------------- #
# OpenAI-compatible HTTP provider (real backend; env-configured)
# --------------------------------------------------------------------------- #


class OpenAICompatibleProvider:
    """Calls an OpenAI-compatible /chat/completions endpoint.

    Configuration comes entirely from environment variables (see module docstring).
    Uses only the standard library (urllib) to avoid a hard dependency; if you prefer
    ``requests`` or an SDK, swap the transport here without touching the grader.
    """

    name = "openai-compatible"

    def __init__(
        self,
        api_base: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_base = (api_base or os.environ.get("GRADER_API_BASE", "")).rstrip("/")
        self.model = model or os.environ.get("GRADER_MODEL", "")
        # API key from env by default; never hard-coded, never logged.
        self._api_key = api_key or os.environ.get("GRADER_API_KEY", "")
        self.timeout = timeout
        if not self.api_base or not self.model:
            raise ValueError(
                "OpenAICompatibleProvider requires GRADER_API_BASE and GRADER_MODEL "
                "(set them as environment variables)."
            )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        import urllib.request  # local import keeps module import side-effect-free

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        req = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]


# --------------------------------------------------------------------------- #
# Prompt-parsing helpers (shared by the mock; also useful for tests)
# --------------------------------------------------------------------------- #


def _extract_block(text: str, tag: str) -> str:
    """Extract the content between <tag> ... </tag> markers, if present."""
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, flags=re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_criterion_ids(text: str) -> list[str]:
    """Extract criterion ids the grader listed as 'id: <cid>' lines in the prompt.

    Allows an optional leading list marker (``- `` or ``* ``) before ``id:``.
    """
    return re.findall(r"^\s*(?:[-*]\s*)?id:\s*(\S+)", text, flags=re.MULTILINE)
