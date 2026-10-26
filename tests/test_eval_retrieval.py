import sqlite3

from muwanhe.compiler.eval_retrieval import (
    evaluate_retrieval,
    evaluate_retrieval_fts,
)
from muwanhe.compiler.index import index_documents
from muwanhe.storage.db import init_db
from muwanhe.storage.extraction_db import init_extraction_db
from muwanhe.storage.fts_store import init_fts_db, rebuild_fts
from muwanhe.storage.vector_store import init_vector_db


class KeywordEmbedding:
    dimensions = 2

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [
            [1.0, 0.0] if "alpha" in text else [0.0, 1.0]
            for text in texts
        ]


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    init_extraction_db(conn)
    conn.execute(
        "INSERT INTO parse_runs (source, chars, lines, created_at) "
        "VALUES ('x', 1, 1, 'now')"
    )
    scenes = [
        ("s1", "alpha " * 60),
        ("s2", "beta " * 60),
    ]
    for index, (scene_id, text) in enumerate(scenes):
        conn.execute(
            "INSERT INTO scenes "
            "(id, run_id, volume_index, chapter_index, part, scene_index, "
            "start_line, end_line, text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (scene_id, 1, 1, 1, None, index, 1, 2, text),
        )
    conn.commit()
    init_vector_db(conn)
    return conn


def test_retrieval_eval_top1():
    conn = _db()
    provider = KeywordEmbedding()
    index_documents(conn, provider, "fake", kinds=("scene",))

    stats = evaluate_retrieval(conn, provider, limit=2, top_k=5)

    assert stats["scenes"] == 2
    assert stats["top1_rate"] == 1.0
    assert stats["top5_rate"] == 1.0


def test_retrieval_eval_fts_top1():
    conn = _db()
    init_fts_db(conn)
    rebuild_fts(conn)

    stats = evaluate_retrieval_fts(conn, limit=2, top_k=5)

    assert stats["scenes"] == 2
    assert stats["top1_rate"] == 1.0
