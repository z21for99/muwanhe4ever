import sqlite3

from muwanhe.compiler.index import index_documents
from muwanhe.providers.embedding import FakeEmbeddingProvider
from muwanhe.storage.db import init_db
from muwanhe.storage.extraction_db import init_extraction_db
from muwanhe.storage.vector_store import count_embeddings, init_vector_db, search


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    conn.execute(
        "INSERT INTO parse_runs (source, chars, lines, created_at) "
        "VALUES ('x', 1, 1, 'now')"
    )
    conn.execute(
        "INSERT INTO scenes "
        "(id, run_id, volume_index, chapter_index, part, scene_index, "
        "start_line, end_line, text) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("s1", 1, 1, 1, None, 0, 1, 2, "hello world"),
    )
    conn.commit()
    init_extraction_db(conn)
    conn.execute(
        "INSERT INTO llm_runs (model, scene_limit, created_at, stats) "
        "VALUES ('fake', 1, 'now', '{}')"
    )
    conn.execute(
        "INSERT INTO segments "
        "(id, llm_run_id, scene_id, segment_index, start_line, end_line, "
        "text, summary, location, story_time, participants) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("seg1", 1, "s1", 0, 0, 1, "hello world", "greeting", "here", "now", "[]"),
    )
    conn.commit()
    init_vector_db(conn)
    return conn


def test_index_scene_and_segment():
    conn = _db()
    provider = FakeEmbeddingProvider(dimensions=8)

    stats = index_documents(conn, provider, "fake")

    assert stats["documents"] == 2
    assert stats["by_kind"] == {"scene": 1, "segment": 1}
    assert count_embeddings(conn) == 2

    hits = search(conn, provider.embed(["hello world"])[0], top_k=5)
    assert hits
    assert hits[0].kind in {"scene", "segment"}


def test_index_segment_offset():
    conn = _db()
    conn.execute(
        "INSERT INTO segments "
        "(id, llm_run_id, scene_id, segment_index, start_line, end_line, "
        "text, summary, location, story_time, participants) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("seg2", 1, "s1", 1, 2, 3, "second", "second", "here", "now", "[]"),
    )
    conn.commit()
    provider = FakeEmbeddingProvider(dimensions=8)

    stats = index_documents(
        conn,
        provider,
        "fake",
        kinds=("segment",),
        limit=1,
        offset=1,
    )

    assert stats["documents"] == 1
    row = conn.execute(
        "SELECT ref_id FROM embeddings WHERE kind = 'segment'"
    ).fetchone()
    assert row == ("seg2",)
