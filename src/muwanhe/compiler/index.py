from __future__ import annotations

import sqlite3
from collections import Counter

from ..providers.embedding import EmbeddingProvider
from ..storage.vector_store import EmbeddingRecord, upsert_embeddings
from .extract import load_scenes


def scene_document(text: str, max_chars: int = 1500) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    head = max_chars - 500
    return text[:head].rstrip() + "\n...\n" + text[-500:].lstrip()


def build_scene_documents(
    conn: sqlite3.Connection,
    limit: int | None = None,
) -> list[dict]:
    documents = []
    for scene in load_scenes(conn, limit):
        documents.append(
            {
                "id": f"scene:{scene.id}",
                "kind": "scene",
                "ref_id": scene.id,
                "text": scene_document(scene.text),
            }
        )
    return documents


def build_segment_documents(
    conn: sqlite3.Connection,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    sql = (
        "SELECT s.id, s.scene_id, s.text, s.summary "
        "FROM segments s "
        "JOIN ("
        "  SELECT scene_id, MAX(llm_run_id) AS latest_run "
        "  FROM segments GROUP BY scene_id"
        ") latest "
        "ON s.scene_id = latest.scene_id AND s.llm_run_id = latest.latest_run "
        "ORDER BY s.scene_id, s.segment_index "
        "LIMIT ? OFFSET ?"
    )
    params: list[object] = [limit if limit is not None else -1, offset]

    documents = []
    for segment_id, scene_id, text, summary in conn.execute(sql, params):
        body = (
            f"{summary}\n{text[:800]}".strip()
            if summary
            else text[:1200].strip()
        )
        if not body:
            continue
        documents.append(
            {
                "id": f"segment:{segment_id}",
                "kind": "segment",
                "ref_id": segment_id,
                "text": body,
            }
        )
    return documents


def index_documents(
    conn: sqlite3.Connection,
    provider: EmbeddingProvider,
    model: str,
    kinds: tuple[str, ...] = ("scene", "segment"),
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    documents: list[dict] = []
    if "scene" in kinds:
        documents.extend(build_scene_documents(conn, limit))
    if "segment" in kinds:
        documents.extend(build_segment_documents(conn, limit, offset))

    if not documents:
        return {
            "documents": 0,
            "by_kind": {},
            "dim": 0,
            "model": model,
        }

    vectors = provider.embed([document["text"] for document in documents])
    records = [
        EmbeddingRecord(
            id=document["id"],
            kind=document["kind"],
            ref_id=document["ref_id"],
            text=document["text"],
            vector=vector,
            model=model,
            dim=len(vector),
        )
        for document, vector in zip(documents, vectors)
    ]
    upsert_embeddings(conn, records)

    counts = Counter(document["kind"] for document in documents)
    return {
        "documents": len(documents),
        "by_kind": dict(counts),
        "dim": len(vectors[0]),
        "model": model,
    }
