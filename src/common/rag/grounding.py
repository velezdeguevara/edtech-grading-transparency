"""Grounding: turn retrieved knowledge-base chunks into prompt context.

The grounding step sits between retrieval and grading. Given a query (question +
student answer) and a ``Retriever`` over the knowledge base, it retrieves the most
relevant reference material and formats it into a compact, labelled context block
that a grader injects into its prompt.

Grounding a grade in explicit, retrieved reference material (rather than the model's
parametric memory) is what supports auditability: an auditor can see exactly *which*
knowledge-base documents informed a grade.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.rag.retriever import RetrievedChunk, Retriever


@dataclass(frozen=True)
class GroundingResult:
    """The retrieved context plus provenance (which docs, at what score)."""

    context_block: str
    chunks: tuple[RetrievedChunk, ...]

    def provenance(self) -> list[dict]:
        """Auditable record of what grounded the grade."""
        return [
            {"id": c.document.id, "kind": c.document.kind, "score": round(c.score, 4)}
            for c in self.chunks
        ]


def build_query(question: str, answer_text: str) -> str:
    """Compose the retrieval query from the rubric question and the student answer."""
    return f"{question}\n{answer_text}"


def ground(
    retriever: Retriever,
    question: str,
    answer_text: str,
    top_k: int = 4,
    min_score: float | None = None,
) -> GroundingResult:
    """Retrieve top-k KB chunks for the query and format them as a context block.

    ``min_score`` filters out weak, incidental matches (e.g. a lone common token like
    "the") so a grade is only grounded in material that is actually relevant — better
    to ground in nothing than in irrelevant text.

    When ``min_score`` is None (the default), the floor comes from the retriever's own
    ``default_min_score``, because the right threshold depends on the retriever's score
    scale (BM25 is unbounded ~2.0; dense cosine is [0, 1] ~0.3). This avoids the footgun
    of a BM25-scale default silently filtering out *all* dense results. Pass an explicit
    value to override.
    """
    floor = retriever.default_min_score if min_score is None else min_score
    query = build_query(question, answer_text)
    chunks = [c for c in retriever.retrieve(query, top_k=top_k) if c.score >= floor]
    if not chunks:
        return GroundingResult(context_block="", chunks=())

    lines = ["REFERENCE_MATERIAL (retrieved; use to ground your judgement):"]
    for c in chunks:
        tag = c.document.criterion_id or c.document.kind
        lines.append(f"- [{tag}] {c.document.text}")
    return GroundingResult(context_block="\n".join(lines), chunks=tuple(chunks))
