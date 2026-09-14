"""BM25 lexical retriever — the core default (pure standard library, zero ML).

Implements Okapi BM25 ranking over the knowledge base. BM25 improves on plain
TF-IDF with term-frequency saturation (``k1``) and document-length normalization
(``b``), which matters here because knowledge-base snippets vary in length (a
one-line criterion vs. a paragraph of guidance) — and, fittingly for this project,
BM25 avoids rewarding a document merely for being long.

Deterministic and fully transparent: ``explain`` shows the per-term contributions to
a score, so retrieval decisions are auditable.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from src.common.rag.retriever import KBDocument, RetrievedChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# A small English stopword set. Removing these stops incidental matches on common
# words (e.g. "the", "and", "its") from accumulating BM25 score, which is what lets an
# off-subject query (a maths answer against a history KB) correctly retrieve nothing
# relevant. Kept intentionally small and transparent — not a full linguistic list.
_STOPWORDS = frozenset(
    """
    a an the and or but if then else of to in on at by for with from into over under
    is are was were be been being it its this that these those as such not no nor so
    than too very can will would should could may might must do does did done
    """.split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word/number tokenizer with stopword removal.

    Shared so query and documents are tokenized consistently.
    """
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


class BM25Retriever:
    name = "bm25"

    # Relevance floor on the BM25 score scale (unbounded). Calibrated empirically on
    # the WWI KB after stopword removal: an off-subject query (e.g. a maths answer)
    # scored ~1.6 against this KB while genuinely relevant content scored ~5-8; a floor
    # of 2.0 sits in that gap. BM25 scores are corpus-dependent — re-tune per KB.
    default_min_score = 2.0

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._docs: list[KBDocument] = []
        self._doc_tokens: list[list[str]] = []
        self._doc_len: list[int] = []
        self._avgdl: float = 0.0
        self._df: Counter[str] = Counter()
        self._idf: dict[str, float] = {}
        self._n: int = 0

    def index(self, documents: list[KBDocument]) -> None:
        self._docs = list(documents)
        self._doc_tokens = [tokenize(d.text) for d in self._docs]
        self._doc_len = [len(toks) for toks in self._doc_tokens]
        self._n = len(self._docs)
        self._avgdl = (sum(self._doc_len) / self._n) if self._n else 0.0

        self._df = Counter()
        for toks in self._doc_tokens:
            for term in set(toks):
                self._df[term] += 1

        # BM25 IDF with the standard +0.5 smoothing; floored at 0 to avoid negatives.
        self._idf = {}
        for term, df in self._df.items():
            self._idf[term] = max(
                0.0, math.log((self._n - df + 0.5) / (df + 0.5) + 1.0)
            )

    def _score_doc(self, query_terms: list[str], doc_idx: int) -> float:
        if self._avgdl == 0:
            return 0.0
        freqs = Counter(self._doc_tokens[doc_idx])
        dl = self._doc_len[doc_idx]
        score = 0.0
        for term in query_terms:
            if term not in freqs:
                continue
            idf = self._idf.get(term, 0.0)
            tf = freqs[term]
            denom = tf + self.k1 * (1 - self.b + self.b * dl / self._avgdl)
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if not self._docs:
            return []
        query_terms = tokenize(query)
        scored = [
            RetrievedChunk(document=self._docs[i], score=self._score_doc(query_terms, i))
            for i in range(self._n)
        ]
        scored = [c for c in scored if c.score > 0.0]
        scored.sort(key=lambda c: (c.score, c.document.id), reverse=True)
        return scored[:top_k]

    def explain(self, query: str, doc_id: str) -> dict[str, float]:
        """Per-term BM25 contributions for one document — for transparency/audit."""
        idx = next((i for i, d in enumerate(self._docs) if d.id == doc_id), None)
        if idx is None or self._avgdl == 0:
            return {}
        freqs = Counter(self._doc_tokens[idx])
        dl = self._doc_len[idx]
        contributions: dict[str, float] = {}
        for term in tokenize(query):
            if term not in freqs:
                continue
            idf = self._idf.get(term, 0.0)
            tf = freqs[term]
            denom = tf + self.k1 * (1 - self.b + self.b * dl / self._avgdl)
            contributions[term] = idf * (tf * (self.k1 + 1)) / denom
        return contributions
