import sqlite3

from muwanhe.storage.db import init_db
from muwanhe.storage.extraction_db import init_extraction_db
from muwanhe.storage.fts_store import (
    count_fts,
    init_fts_db,
    rebuild_fts,
    search_fts,
)


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
        ("s1", 1, 1, 1, None, 0, 1, 2, "父亲回家骂母亲，家里很安静。"),
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
        (
            "seg1",
            1,
            "s1",
            0,
            0,
            1,
            "父亲骂母亲，家里很安静。",
            "父亲骂母亲",
            "家",
            "晚上",
            "[]",
        ),
    )
    conn.commit()
    init_fts_db(conn)
    return conn


def test_rebuild_and_search_fts():
    conn = _db()
    stats = rebuild_fts(conn)

    assert stats == {"scenes": 1, "segments": 1}
    assert count_fts(conn) == 2

    hits = search_fts(conn, "骂母亲", top_k=5)
    assert hits
    assert all(hit.kind in {"scene", "segment"} for hit in hits)

    scene_hits = search_fts(conn, "骂母亲", kind="scene", top_k=5)
    assert [hit.ref_id for hit in scene_hits] == ["s1"]

    short_hits = search_fts(conn, "母亲", kind="scene", top_k=5)
    assert [hit.ref_id for hit in short_hits] == ["s1"]
