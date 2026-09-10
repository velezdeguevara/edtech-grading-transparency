# Track B — Explainable, vendor-neutral grader

Implements the shared `Grader` interface (`src/common/grading/schema.py`) so the
`evals/` harness scores it identically to every other grader.

It is **explainable** (rubric-grounded, structured per-criterion output with evidence
spans and confidence) but **not** mechanistically interpretable — that limitation is
the point of Track B.

## Providers

Text generation is delegated to a `Provider` (see `providers.py`), keeping the study
vendor-neutral.

- **`MockProvider`** (default) — offline, deterministic, **no API key**. Lets the
  harness and tests run without network access.
- **`OpenAICompatibleProvider`** — calls any OpenAI-compatible `/chat/completions`
  endpoint (OpenAI, vLLM, Ollama's OpenAI endpoint, LM Studio, gateways, ...).

## Running with the mock (default)

```python
from evals.run_all import run_all
from src.track_b_explainable.grader import ExplainableGrader

run_all(ExplainableGrader())  # uses MockProvider
```

## Running against a real OpenAI-compatible endpoint

Configuration comes **only** from environment variables. The API key is never read
from or written to the repository.

```bash
export GRADER_API_BASE="https://api.openai.com/v1"   # or http://localhost:11434/v1 (Ollama), etc.
export GRADER_MODEL="gpt-4o-mini"                      # or llama3.1, qwen2.5, ...
export GRADER_API_KEY="sk-..."                         # secret; do NOT commit. Some local servers ignore it.
```

```python
from evals.run_all import run_all
from src.track_b_explainable.grader import ExplainableGrader
from src.track_b_explainable.providers import OpenAICompatibleProvider

run_all(ExplainableGrader(provider=OpenAICompatibleProvider()))
```

## Safety notes

- The grader **fails safe**: malformed JSON, missing, or unknown criteria are treated
  as `not_met` with zero confidence, so a bad model response yields a conservative
  (low) grade rather than crashing or silently inflating a grade.
- The tool **proposes**; a teacher must approve/override (human-in-the-loop).
- `GRADER_API_KEY` must come from the environment. `.env` files are gitignored.
