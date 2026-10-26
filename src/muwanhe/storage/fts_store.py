from __future__ import annotations

import sqlite3

from .vector_store import SearchHit

SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
  doc_id UNINDEXED,
  kind UNINDEXED,
  ref_id UNINDEXED,
  text,
  tokenize='trigram'
);
"""


def init_fts_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _match_query(query: str) -> str:
    return '"' + query.replace('"', '""') + '"'


def rebuild_fts(conn: sqlite3.Connection) -> dict:
    conn.execute("DELETE FROM docs_fts")

    parse_run = conn.execute("SELECT MAX(id) FROM parse_runs").fetchone()[0]
    if parse_run is None:
        conn.commit()
        return {"scenes": 0, "segments": 0}

    scenes = conn.execute(
        "SELECT id, text FROM scenes WHERE run_id = ? "
        "ORDER BY volume_index, chapter_index, scene_index",
        (parse_run,),
    ).fetchall()
    for scene_id, text in scenes:
        conn.execute(
            "INSERT INTO docs_fts (doc_id, kind, ref_id, text) VALUES (?, ?, ?, ?)",
            (f"scene:{scene_id}", "scene", scene_id, text),
        )

    segments = conn.execute(
        "SELECT s.id, s.scene_id, s.text, s.summary "
        "FROM segments s "
        "JOIN ("
        "  SELECT scene_id, MAX(llm_run_id) AS latest_run "
        "  FROM segments GROUP BY scene_id"
        ") latest "
        "ON s.scene_id = latest.scene_id AND s.llm_run_id = latest.latest_run "
        "ORDER BY s.scene_id, s.segment_index"
    ).fetchall()
    for segment_id, scene_id, text, summary in segments:
        body = (
            f"{summary}\n{text[:1200]}".strip()
            if summary
            else text[:1600].strip()
        )
        conn.execute(
            "INSERT INTO docs_fts (doc_id, kind, ref_id, text) VALUES (?, ?, ?, ?)",
            (f"segment:{segment_id}", "segment", segment_id, body),
        )

    conn.commit()
    return {"scenes": len(scenes), "segments": len(segments)}


def count_fts(conn: sqlite3.Connection, kind: str | None = None) -> int:
    if kind:
        row = conn.execute(
            "SELECT COUNT(*) FROM docs_fts WHERE kind = ?", (kind,)
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM docs_fts").fetchone()
    return int(row[0])


def search_fts(
    conn: sqlite3.Connection,
    query: str,
    kind: str | None = None,
    top_k: int = 5,
) -> list[SearchHit]:
    query = query.strip()
    if not query:
        return []
    if len(query) < 3:
        return _like_search(conn, query, kind, top_k)

    sql = (
        "SELECT doc_id, kind, ref_id, text, bm25(docs_fts) AS rank "
        "FROM docs_fts WHERE docs_fts MATCH ?"
    )
    params: list[object] = [_match_query(query)]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " ORDER BY rank LIMIT ?"
    params.append(top_k)

    hits = [
        SearchHit(
            id=row[0],
            kind=row[1],
            ref_id=row[2],
            text=row[3],
            score=round(-float(row[4]), 4),
        )
        for row in conn.execute(sql, params)
    ]
    return hits or _like_search(conn, query, kind, top_k)


def _like_search(
    conn: sqlite3.Connection,
    query: str,
    kind: str | None,
    top_k: int,
) -> list[SearchHit]:
    sql = "SELECT doc_id, kind, ref_id, text FROM docs_fts WHERE text LIKE ?"
    params: list[object] = [f"%{query}%"]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " LIMIT ?"
    params.append(top_k)

    return [
        SearchHit(
            id=row[0],
            kind=row[1],
            ref_id=row[2],
            text=row[3],
            score=0.0,
        )
        for row in conn.execute(sql, params)
    ]
