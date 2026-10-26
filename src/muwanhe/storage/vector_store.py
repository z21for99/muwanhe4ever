from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS embeddings (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  ref_id TEXT NOT NULL,
  text TEXT NOT NULL,
  vector TEXT NOT NULL,
  model TEXT NOT NULL,
  dim INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_embeddings_kind ON embeddings(kind);
"""


@dataclass(frozen=True)
class EmbeddingRecord:
    id: str
    kind: str
    ref_id: str
    text: str
    vector: list[float]
    model: str
    dim: int


@dataclass(frozen=True)
class SearchHit:
    id: str
    kind: str
    ref_id: str
    text: str
    score: float


def init_vector_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_embeddings(
    conn: sqlite3.Connection,
    records: list[EmbeddingRecord],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for record in records:
        conn.execute(
            "INSERT OR REPLACE INTO embeddings "
            "(id, kind, ref_id, text, vector, model, dim, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.kind,
                record.ref_id,
                record.text,
                json.dumps(record.vector),
                record.model,
                record.dim,
                now,
            ),
        )
    conn.commit()


def count_embeddings(conn: sqlite3.Connection, kind: str | None = None) -> int:
    if kind:
        row = conn.execute(
            "SELECT COUNT(*) FROM embeddings WHERE kind = ?", (kind,)
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
    return int(row[0])


def search(
    conn: sqlite3.Connection,
    query_vector: list[float],
    kind: str | None = None,
    top_k: int = 5,
) -> list[SearchHit]:
    sql = "SELECT id, kind, ref_id, text, vector FROM embeddings"
    params: list[object] = []
    if kind:
        sql += " WHERE kind = ?"
        params.append(kind)

    hits: list[SearchHit] = []
    for row in conn.execute(sql, params):
        vector = json.loads(row[4])
        hits.append(
            SearchHit(
                id=row[0],
                kind=row[1],
                ref_id=row[2],
                text=row[3],
                score=_cosine(query_vector, vector),
            )
        )
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[:top_k]


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)
