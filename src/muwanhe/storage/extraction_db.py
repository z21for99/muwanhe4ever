from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from ..characters import DEFAULT_CHARACTERS
from ..schemas import Character, Utterance

SCHEMA = """
CREATE TABLE IF NOT EXISTS characters (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  aliases TEXT NOT NULL,
  is_narrator INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS utterances (
  id TEXT PRIMARY KEY,
  run_id INTEGER NOT NULL,
  scene_id TEXT NOT NULL,
  speaker_id TEXT,
  addressee_id TEXT,
  text TEXT NOT NULL,
  context TEXT NOT NULL,
  quote_start INTEGER NOT NULL,
  quote_end INTEGER NOT NULL,
  method TEXT NOT NULL,
  confidence REAL NOT NULL,
  is_dialogue INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS extraction_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scene_limit INTEGER,
  created_at TEXT NOT NULL,
  stats TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model TEXT NOT NULL,
  scene_limit INTEGER,
  created_at TEXT NOT NULL,
  stats TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS segments (
  id TEXT PRIMARY KEY,
  llm_run_id INTEGER NOT NULL,
  scene_id TEXT NOT NULL,
  segment_index INTEGER NOT NULL,
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  text TEXT NOT NULL,
  summary TEXT NOT NULL,
  location TEXT,
  story_time TEXT,
  participants TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS style_modes (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  addressee_id TEXT,
  scene_type TEXT NOT NULL,
  emotion TEXT NOT NULL,
  description TEXT NOT NULL,
  sample_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS style_samples (
  id TEXT PRIMARY KEY,
  mode_id TEXT NOT NULL,
  utterance_id TEXT NOT NULL,
  text TEXT NOT NULL,
  context TEXT NOT NULL,
  markedness TEXT NOT NULL,
  tags TEXT NOT NULL
);
"""


def init_extraction_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def seed_characters(conn: sqlite3.Connection) -> None:
    for character in DEFAULT_CHARACTERS:
        conn.execute(
            "INSERT OR IGNORE INTO characters (id, name, aliases, is_narrator) "
            "VALUES (?, ?, ?, ?)",
            (
                character.id,
                character.name,
                json.dumps(character.aliases, ensure_ascii=False),
                int(character.is_narrator),
            ),
        )
    conn.commit()


def load_characters(conn: sqlite3.Connection) -> list[Character]:
    rows = conn.execute(
        "SELECT id, name, aliases, is_narrator FROM characters ORDER BY rowid"
    ).fetchall()
    return [
        Character(
            id=row[0],
            name=row[1],
            aliases=json.loads(row[2]),
            is_narrator=bool(row[3]),
        )
        for row in rows
    ]


def save_extraction(
    conn: sqlite3.Connection,
    utterances: list[Utterance],
    stats: dict,
    scene_limit: int | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO extraction_runs (scene_limit, created_at, stats) VALUES (?, ?, ?)",
        (
            scene_limit,
            datetime.now(timezone.utc).isoformat(),
            json.dumps(stats, ensure_ascii=False),
        ),
    )
    run_id = int(cur.lastrowid)

    for utterance in utterances:
        conn.execute(
            "INSERT OR REPLACE INTO utterances "
            "(id, run_id, scene_id, speaker_id, addressee_id, text, context, "
            "quote_start, quote_end, method, confidence, is_dialogue) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                utterance.id,
                run_id,
                utterance.scene_id,
                utterance.speaker_id,
                utterance.addressee_id,
                utterance.text,
                utterance.context,
                utterance.quote_start,
                utterance.quote_end,
                utterance.method,
                utterance.confidence,
                int(utterance.is_dialogue),
            ),
        )

    conn.commit()
    return run_id


def load_latest_stats(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT stats FROM extraction_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return json.loads(row[0]) if row else {}


def insert_llm_run(
    conn: sqlite3.Connection,
    model: str,
    scene_limit: int | None,
    stats: dict,
) -> int:
    cur = conn.execute(
        "INSERT INTO llm_runs (model, scene_limit, created_at, stats) "
        "VALUES (?, ?, ?, ?)",
        (
            model,
            scene_limit,
            datetime.now(timezone.utc).isoformat(),
            json.dumps(stats, ensure_ascii=False),
        ),
    )
    return int(cur.lastrowid)
