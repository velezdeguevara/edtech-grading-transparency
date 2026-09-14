"""RAG retriever interface and knowledge-base types.

Tiered, capability-adaptive design mirroring the rest of the repo:

  - Default (core):   BM25Retriever (pure stdlib) — runs on any laptop, zero ML.
  - Optional upgrade: DenseRetriever (sentence-transformers + FAISS) behind
                      requirements-rag.txt, lazy-imported.

Both implement the same ``Retriever`` interface, so the grounding step and graders
depend only on this contract. The knowledge base is a small local corpus of rubric
criteria and reference/marking snippets — retrieval grounds a grade in explicit,
inspectable material rather than a model's parametric memory (supports auditability).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class KBDocument:
    """One retrievable unit in the knowledge base."""

    id: str
    text: str
    # e.g. "criterion" | "reference" | "guidance"; and the criterion it relates to.
    kind: str = "reference"
    criterion_id: str = ""


@dataclass(frozen=True)
class RetrievedChunk:
    """A knowledge-base document returned for a query, with its relevance score."""

    document: KBDocument
    score: float


@runtime_checkable
class Retriever(Protocol):
    """Retrieve the most relevant knowledge-base documents for a query.

    ``index`` prepares the retriever over a corpus; ``retrieve`` returns the top-k
    documents for a query string (question + student answer, typically).

    ``default_min_score`` is the relevance floor appropriate to THIS retriever's score
    scale — BM25 scores are unbounded (a floor of ~2 is meaningful), while dense cosine
    scores are in [0, 1] (a floor of ~0.3). Grounding uses it so callers do not have to
    know a retriever's scale; it stays overridable.
    """

    name: str
    default_min_score: float

    def index(self, documents: list[KBDocument]) -> None:
        ...

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        ...
