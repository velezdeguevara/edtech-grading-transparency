"""Tests for the RAG layer: BM25 retriever, KB loader, grounding, grounded grader."""

from __future__ import annotations

from src.common.rag.bm25 import BM25Retriever, tokenize
from src.common.rag.grounding import build_query, ground
from src.common.rag.kb_loader import load_knowledge_base
from src.common.rag.retriever import KBDocument
from src.common.rubrics.loader import load_fixtures, load_rubric
from src.track_b_explainable.grader import ExplainableGrader

RUBRIC_ID = "ss-wwi-causes-v1"


def _indexed_retriever() -> BM25Retriever:
    r = BM25Retriever()
    r.index(load_knowledge_base(RUBRIC_ID))
    return r


# --- Tokenizer ---

def test_tokenize_lowercases_and_splits():
    assert tokenize("Franz Ferdinand, 1914!") == ["franz", "ferdinand", "1914"]


# --- KB loader ---

def test_kb_loader_includes_criteria_and_references():
    docs = load_knowledge_base(RUBRIC_ID)
    ids = {d.id for d in docs}
    # 4 rubric criteria as documents + reference/guidance snippets.
    assert "criterion:economic" in ids
    assert "ref-economic" in ids
    kinds = {d.kind for d in docs}
    assert "criterion" in kinds and "reference" in kinds


# --- BM25 retriever ---

def test_bm25_ranks_relevant_document_top():
    r = _indexed_retriever()
    hits = r.retrieve("economic colonial and industrial rivalry Britain Germany", top_k=3)
    assert hits, "expected at least one hit"
    # The economic reference/criterion should surface at the top.
    assert hits[0].document.criterion_id == "economic"


def test_bm25_empty_index_returns_nothing():
    assert BM25Retriever().retrieve("anything") == []


def test_bm25_no_match_returns_empty():
    r = BM25Retriever()
    r.index([KBDocument(id="d1", text="alliances and nationalism", kind="reference")])
    assert r.retrieve("photosynthesis chlorophyll") == []


def test_bm25_cannot_separate_wwi_from_wwii_documented_limitation():
    """Documented limitation: lexical BM25 cannot reliably separate 'First' from
    'Second' World War, because tokens like 'world', 'war', and 'german' are shared.

    This is an honest, on-thesis artifact: it shows lexical retrieval's ceiling and is
    exactly the case the optional DENSE (semantic) retriever tier exists to improve.
    We assert the *actual* behaviour (the WWII distractor is competitive, often top),
    rather than pretending BM25 discriminates here.
    """
    docs = load_knowledge_base(RUBRIC_ID) + [
        KBDocument(
            id="distractor-wwii",
            text=(
                "The Second World War began in 1939 with the German invasion of Poland; "
                "its causes include the Treaty of Versailles, the rise of fascism, and "
                "appeasement in the 1930s."
            ),
            kind="reference",
            criterion_id="",
        )
    ]
    r = BM25Retriever()
    r.index(docs)
    hits = r.retrieve(
        "causes of the First World War: alliances, arms race, and colonial rivalry",
        top_k=5,
    )
    ranked_ids = [h.document.id for h in hits]
    # The distractor is retrieved and ranks highly — demonstrating the limitation.
    assert "distractor-wwii" in ranked_ids
    assert ranked_ids.index("distractor-wwii") <= 1
    r = _indexed_retriever()
    contributions = r.explain("economic rivalry", "ref-economic")
    assert "economic" in contributions
    assert all(v >= 0 for v in contributions.values())


def test_bm25_is_deterministic():
    r1, r2 = _indexed_retriever(), _indexed_retriever()
    q = "military arms race and the Schlieffen Plan"
    a = [(c.document.id, round(c.score, 6)) for c in r1.retrieve(q)]
    b = [(c.document.id, round(c.score, 6)) for c in r2.retrieve(q)]
    assert a == b


# --- Grounding ---

def test_build_query_combines_question_and_answer():
    q = build_query("What caused WWI?", "Alliances and nationalism.")
    assert "What caused WWI?" in q and "Alliances" in q


def test_ground_produces_reference_block_with_provenance():
    r = _indexed_retriever()
    rubric = load_rubric(RUBRIC_ID)
    ex = load_fixtures(RUBRIC_ID)[0]
    result = ground(r, rubric.question, ex.answer_text, top_k=4)
    assert result.context_block.startswith("REFERENCE_MATERIAL")
    prov = result.provenance()
    assert len(prov) >= 1
    assert all({"id", "kind", "score"} <= set(p) for p in prov)


def test_ground_empty_for_off_subject_query():
    """A mis-routed answer from another subject must not ground a WWI grade.

    Realistic safety check for an EdTech grader: if a maths answer is sent against the
    WWI knowledge base, retrieval should find nothing rather than ground the grade in
    irrelevant material. (Uses vocabulary with no overlap with the WWI KB.)
    """
    r = _indexed_retriever()  # the real WWI knowledge base
    result = ground(
        r,
        "Solve the quadratic equation",
        "Factor the polynomial and compute its roots using the discriminant.",
        top_k=3,
    )
    assert result.context_block == ""
    assert result.chunks == ()


# --- Grounded Track B grader (opt-in, backwards compatible) ---

def test_bm25_declares_default_min_score():
    assert BM25Retriever().default_min_score == 2.0


def test_ground_uses_retriever_default_threshold():
    """With min_score=None (default), ground() applies the retriever's own floor.

    A strong WWI answer clears BM25's 2.0 floor, so grounding is non-empty.
    """
    r = _indexed_retriever()
    rubric = load_rubric(RUBRIC_ID)
    ex = load_fixtures(RUBRIC_ID)[0]
    result = ground(r, rubric.question, ex.answer_text)  # min_score=None
    assert result.context_block.startswith("REFERENCE_MATERIAL")


def test_ground_explicit_min_score_overrides():
    """An explicit, very high min_score filters everything out, overriding the default."""
    r = _indexed_retriever()
    rubric = load_rubric(RUBRIC_ID)
    ex = load_fixtures(RUBRIC_ID)[0]
    result = ground(r, rubric.question, ex.answer_text, min_score=999.0)
    assert result.context_block == ""
    assert result.chunks == ()


def test_grader_without_retriever_is_unchanged():
    rubric = load_rubric(RUBRIC_ID)
    grader = ExplainableGrader()
    assert grader.retriever is None
    assert "+rag" not in grader.name


def test_grader_with_retriever_injects_reference_material():
    rubric = load_rubric(RUBRIC_ID)
    ex = load_fixtures(RUBRIC_ID)[0]
    grader = ExplainableGrader(retriever=_indexed_retriever())
    assert "+rag" in grader.name
    prompt = grader._build_user_prompt(rubric, ex.answer_text)
    assert "REFERENCE_MATERIAL" in prompt
    # Grading still produces one assessment per criterion.
    grade = grader.grade(rubric, ex.answer_text)
    assert len(grade.assessments) == len(rubric.criteria)
