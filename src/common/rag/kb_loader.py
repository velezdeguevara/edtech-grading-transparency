"""Knowledge-base loader.

Builds the retrievable corpus for a rubric by combining:
  1. the rubric's own criteria (the authoritative scoring standards), and
  2. reference / marking-guidance snippets from data/knowledge_base/.

Returns a list of ``KBDocument`` ready to hand to any ``Retriever``.
"""

from __future__ import annotations

import json

from src.common.paths import data_dir
from src.common.rag.retriever import KBDocument
from src.common.rubrics.loader import load_rubric

KB_DIR = data_dir() / "knowledge_base"


def load_knowledge_base(rubric_id: str) -> list[KBDocument]:
    docs: list[KBDocument] = []

    # 1. Rubric criteria as documents (always available).
    rubric = load_rubric(rubric_id)
    for c in rubric.criteria:
        docs.append(
            KBDocument(
                id=f"criterion:{c.id}",
                text=c.description,
                kind="criterion",
                criterion_id=c.id,
            )
        )

    # 2. Reference / guidance snippets, if a KB file exists for this rubric.
    kb_path = KB_DIR / f"{rubric_id}.kb.json"
    if kb_path.exists():
        raw = json.loads(kb_path.read_text(encoding="utf-8"))
        for d in raw.get("documents", []):
            docs.append(
                KBDocument(
                    id=d["id"],
                    text=d["text"],
                    kind=d.get("kind", "reference"),
                    criterion_id=d.get("criterion_id", ""),
                )
            )

    return docs
