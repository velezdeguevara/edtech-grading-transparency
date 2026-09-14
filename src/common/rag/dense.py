"""Optional dense (semantic) retriever — the upgrade tier, NOT the core default.

Uses local sentence-embeddings + cosine similarity for semantic retrieval, which finds
relevant material even when wording differs from the query (unlike lexical BM25). This
needs heavier dependencies, so it is OPTIONAL and lazy-imported: importing this module
never fails when the optional packages are absent — only *using* it requires them.
The core default remains ``BM25Retriever`` (pure stdlib, no install).

Install the optional deps in a suitable environment:
    pip install -r requirements-rag.txt

RECOMMENDED MODELS:
- Local / foundational (default): ``intfloat/multilingual-e5-small`` (~47M params,
  fast on laptop CPUs, strong ES/EN and broad multilingual support).
- Enterprise production: ``BAAI/bge-m3`` (~568M params, state-of-the-art multilingual;
  heavier RAM/GPU requirements).

NOTE ON PREFIXES: instruction-tuned E5 models are trained to expect ``"query: "`` on
the query and ``"passage: "`` on documents; retrieval quality drops without them. These
prefixes are model-specific — if you swap to a model that does not use them (e.g. a
plain MiniLM), set ``query_prefix`` and ``doc_prefix`` to ``""``.

All retrievers implement the same ``Retriever`` interface, so grounding and graders
work unchanged whichever tier or model is used.
"""

from __future__ import annotations

from src.common.rag.retriever import KBDocument, RetrievedChunk


class DenseRetriever:
    """Sentence-embedding + cosine-similarity retriever (optional tier).

    Fully local (no cloud): the embedding model runs on-device. Dependencies are
    imported lazily in ``_ensure_model``.
    """

    name = "dense"

    # Relevance floor on the cosine-similarity scale ([0, 1] for normalized embeddings).
    # ~0.3 is a reasonable default for E5-family models; tune per model/KB. This is far
    # below BM25's floor because the score scales differ — which is exactly why the floor
    # lives with the retriever rather than being hardcoded in grounding.
    default_min_score = 0.3

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-small",
        query_prefix: str = "query: ",
        doc_prefix: str = "passage: ",
    ) -> None:
        self.model_name = model_name
        self.query_prefix = query_prefix
        self.doc_prefix = doc_prefix
        self._model = None
        self._docs: list[KBDocument] = []
        self._embeddings = None  # numpy array [n_docs, dim]

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:  # pragma: no cover - only without optional deps
            raise RuntimeError(
                "DenseRetriever requires the optional RAG dependencies. Install them "
                "with `pip install -r requirements-rag.txt`, or use the default "
                "BM25Retriever (pure stdlib, no install)."
            ) from e
        self._model = SentenceTransformer(self.model_name)

    def index(self, documents: list[KBDocument]) -> None:
        self._ensure_model()
        self._docs = list(documents)

        # Apply the document prefix required by instruction-tuned models like E5.
        texts = [self.doc_prefix + d.text for d in self._docs]

        # normalize_embeddings=True lets us use a plain dot product as cosine similarity.
        self._embeddings = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if not self._docs:
            return []
        self._ensure_model()
        import numpy as np

        # Apply the query prefix before encoding.
        formatted_query = self.query_prefix + query
        q = self._model.encode(
            [formatted_query], normalize_embeddings=True, convert_to_numpy=True
        )[0]

        sims = self._embeddings @ q  # cosine similarity (embeddings are normalized)
        order = np.argsort(-sims)[:top_k]
        return [
            RetrievedChunk(document=self._docs[i], score=float(sims[i]))
            for i in order
            if sims[i] > 0.0
        ]
