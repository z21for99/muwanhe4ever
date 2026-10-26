from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ..schemas import ParseResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS parse_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  chars INTEGER NOT NULL,
  lines INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS volumes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  volume_index INTEGER NOT NULL,
  source_index INTEGER NOT NULL,
  title TEXT NOT NULL,
  start_line INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS chapters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  volume_index INTEGER NOT NULL,
  chapter_index INTEGER NOT NULL,
  title TEXT NOT NULL,
  part TEXT,
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenes (
  id TEXT NOT NULL,
  run_id INTEGER NOT NULL,
  volume_index INTEGER NOT NULL,
  chapter_index INTEGER NOT NULL,
  part TEXT,
  scene_index INTEGER NOT NULL,
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  text TEXT NOT NULL,
  PRIMARY KEY (run_id, id)
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def save_parse_result(conn: sqlite3.Connection, result: ParseResult) -> int:
    cur = conn.execute(
        "INSERT INTO parse_runs (source, chars, lines, created_at) VALUES (?, ?, ?, ?)",
        (
            result.source,
            result.chars,
            result.lines,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    run_id = int(cur.lastrowid)

    for volume in result.volumes:
        conn.execute(
            "INSERT INTO volumes (run_id, volume_index, source_index, title, start_line) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, volume.index, volume.source_index, volume.title, volume.start_line),
        )

    for chapter in result.chapters:
        for part in chapter.parts:
            conn.execute(
                "INSERT INTO chapters "
                "(run_id, volume_index, chapter_index, title, part, start_line, end_line, text) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    chapter.volume_index,
                    chapter.index,
                    part.title or chapter.title,
                    part.part,
                    part.start_line,
                    part.end_line,
                    part.text,
                ),
            )

    for scene in result.scenes:
        conn.execute(
            "INSERT INTO scenes "
            "(id, run_id, volume_index, chapter_index, part, scene_index, "
            "start_line, end_line, text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scene.id,
                run_id,
                scene.volume_index,
                scene.chapter_index,
                scene.part,
                scene.scene_index,
                scene.start_line,
                scene.end_line,
                scene.text,
            ),
        )

    conn.commit()
    return run_id


def stats(conn: sqlite3.Connection) -> dict[str, int]:
    row = conn.execute("SELECT MAX(id) FROM parse_runs").fetchone()
    run_id = row[0] if row else None
    if run_id is None:
        return {"volumes": 0, "chapters": 0, "parts": 0, "scenes": 0}

    volumes = conn.execute(
        "SELECT COUNT(*) FROM volumes WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    chapters = conn.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT DISTINCT volume_index, chapter_index FROM chapters WHERE run_id = ?"
        ")",
        (run_id,),
    ).fetchone()[0]
    parts = conn.execute(
        "SELECT COUNT(*) FROM chapters WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    scenes = conn.execute(
        "SELECT COUNT(*) FROM scenes WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    return {
        "volumes": int(volumes),
        "chapters": int(chapters),
        "parts": int(parts),
        "scenes": int(scenes),
    }
