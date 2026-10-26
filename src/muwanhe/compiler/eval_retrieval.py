from __future__ import annotations

import sqlite3

from ..providers.embedding import EmbeddingProvider
from ..storage.vector_store import search
from .extract import load_scenes
from .index import scene_document


def evaluate_retrieval(
    conn: sqlite3.Connection,
    provider: EmbeddingProvider,
    limit: int = 20,
    top_k: int = 5,
    query_chars: int = 80,
) -> dict:
    scenes = load_scenes(conn, limit)
    total = 0
    top1 = 0
    top5 = 0
    reciprocal_ranks: list[float] = []

    for scene in scenes:
        document = scene_document(scene.text)
        if len(document) < 40:
            continue

        start = max(0, min(len(document) // 3, len(document) - query_chars))
        query = document[start : start + query_chars]
        vector = provider.embed([query])[0]
        hits = search(conn, vector, kind="scene", top_k=top_k)
        target = f"scene:{scene.id}"
        rank = next(
            (index + 1 for index, hit in enumerate(hits) if hit.id == target),
            None,
        )
        total += 1
        if rank == 1:
            top1 += 1
        if rank is not None and rank <= 5:
            top5 += 1
        if rank is not None:
            reciprocal_ranks.append(1.0 / rank)

    if total == 0:
        return {"scenes": 0, "top1_rate": 0.0, "top5_rate": 0.0, "mrr": 0.0}

    return {
        "scenes": total,
        "top1_rate": round(top1 / total, 4),
        "top5_rate": round(top5 / total, 4),
        "mrr": round(sum(reciprocal_ranks) / total, 4),
    }
