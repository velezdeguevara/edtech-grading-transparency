# RAG — retrieval-augmented grounding

Grounds a grade in explicit, retrieved reference material (rubric criteria + marking
snippets) rather than the model's parametric memory. This supports **auditability**: an
auditor can see exactly *which* knowledge-base documents informed a grade
(`GroundingResult.provenance()`).

Tiered, capability-adaptive design — the same pattern used across the repo:

| Tier | Retriever | Dependencies | When |
|---|---|---|---|
| **Default (core)** | `BM25Retriever` (`bm25.py`) | **pure stdlib** | runs on any laptop; deterministic; the reference baseline |
| **Optional upgrade** | `DenseRetriever` (`dense.py`) | `requirements-rag.txt` | semantic retrieval for local/production use |

Both implement the same `Retriever` interface (`retriever.py`), so grounding and the
graders are unchanged whichever tier is used.

## Modules

| File | Responsibility |
|---|---|
| `retriever.py` | `Retriever` protocol, `KBDocument`, `RetrievedChunk` |
| `bm25.py` | Pure-stdlib Okapi BM25 (`k1=1.5`, `b=0.75`); `explain()` shows per-term contributions |
| `kb_loader.py` | Builds the corpus: rubric criteria + `data/knowledge_base/*.kb.json` |
| `grounding.py` | Retrieves top-k and formats a `REFERENCE_MATERIAL` context block with provenance |
| `dense.py` | Optional semantic retriever (lazy-imported) |

## Knowledge base

`data/knowledge_base/<rubric_id>.kb.json` holds reference and marking-guidance snippets.
Combined with the rubric's own criteria by `kb_loader.load_knowledge_base(rubric_id)`.
Synthetic only — no real student data.

## Using it (default, no install)

```python
from src.common.rag.bm25 import BM25Retriever
from src.common.rag.kb_loader import load_knowledge_base
from src.track_b_explainable.grader import ExplainableGrader

retriever = BM25Retriever()
retriever.index(load_knowledge_base("ss-wwi-causes-v1"))

# Opt-in grounding: pass a retriever. Without one, the grader is unchanged.
grader = ExplainableGrader(retriever=retriever)   # name becomes ...[mock+rag]
```

## Optional dense retriever

```bash
pip install -r requirements-rag.txt
```

```python
from src.common.rag.dense import DenseRetriever
retriever = DenseRetriever()  # default: intfloat/multilingual-e5-small
```

**Recommended models**
- Local / foundational (default): `intfloat/multilingual-e5-small` (~47M params; fast on
  CPU; strong ES/EN + multilingual).
- Enterprise production: `BAAI/bge-m3` (~568M params; SOTA multilingual; heavier).

**Prefixes matter.** E5 models are trained to expect `"query: "` on queries and
`"passage: "` on documents; retrieval quality drops without them. These are the
defaults. If you swap to a model that does not use them (e.g. a plain MiniLM), set
`query_prefix=""` and `doc_prefix=""`.

The embedding model downloads from Hugging Face on first use (cached), not via pip. The
dense retriever is lazy-imported: importing `dense.py` never fails without the optional
deps — only *using* it does, with a clear message pointing to `requirements-rag.txt`.

## Relevance threshold (per-retriever, not hardcoded)

`ground()` filters weak matches with a relevance floor. Because score scales differ
(BM25 is unbounded, dense cosine is `[0, 1]`), the floor is a property of the
**retriever**, not of grounding: each retriever declares `default_min_score`
(BM25 → `2.0`, Dense → `0.3`). `ground(..., min_score=None)` (the default) uses the
retriever's value, so `ground(dense_retriever, ...)` works correctly without the caller
knowing the scale — avoiding the footgun where a BM25-scale default would silently
filter out *all* dense results. Pass an explicit `min_score` to override.

## Known limitations of the lexical default (and why the dense tier exists)

BM25 matches *tokens*, not *meaning*. Two honest, tested consequences:

- **It cannot reliably separate lexically-similar-but-distinct topics.** For example, a
  "First World War" query also matches a "Second World War" passage strongly, because
  `world`, `war`, and `german` are shared. This is a genuine ceiling of lexical
  retrieval — and precisely the case the optional **dense (semantic) retriever** is
  meant to improve. The test suite asserts this limitation rather than hiding it.
- **Incidental matches on common words** (e.g. `the`, `and`) are reduced by a small
  **stopword list** in `tokenize()`, and the per-retriever relevance floor ensures an
  off-subject query (say, a maths answer sent against a history rubric) grounds in
  *nothing* rather than in irrelevant text.
