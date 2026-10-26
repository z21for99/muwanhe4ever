from __future__ import annotations

import re
import sqlite3
from collections import Counter

from ..schemas import Character, Scene, Utterance
from .attribution import attribute_quote, scene_present
from .dialogue import extract_quotes


def load_scenes(conn: sqlite3.Connection, limit: int | None = None) -> list[Scene]:
    row = conn.execute("SELECT MAX(id) FROM parse_runs").fetchone()
    run_id = row[0] if row else None
    if run_id is None:
        return []

    sql = (
        "SELECT id, volume_index, chapter_index, part, scene_index, "
        "start_line, end_line, text FROM scenes WHERE run_id = ? "
        "ORDER BY volume_index, chapter_index, scene_index"
    )
    params: list[object] = [run_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [
        Scene(
            id=row[0],
            volume_index=row[1],
            chapter_index=row[2],
            part=row[3],
            scene_index=row[4],
            start_line=row[5],
            end_line=row[6],
            text=row[7],
        )
        for row in rows
    ]


def _context(text: str, start: int, end: int, radius: int = 80) -> str:
    snippet = text[max(0, start - radius) : min(len(text), end + radius)]
    return re.sub(r"\s+", " ", snippet).strip()


def extract_scenes(
    conn: sqlite3.Connection,
    characters: list[Character],
    limit: int | None = None,
) -> tuple[list[Utterance], dict]:
    scenes = load_scenes(conn, limit)
    utterances: list[Utterance] = []

    for scene in scenes:
        present = scene_present(scene.text)
        previous_speaker: str | None = None
        for index, quote in enumerate(extract_quotes(scene.text)):
            text = quote.text.strip()
            if not text:
                continue

            attribution = attribute_quote(
                quote,
                scene.text,
                characters,
                previous_speaker,
                present,
            )
            utterance = Utterance(
                id=f"{scene.id}:q{index:03d}",
                scene_id=scene.id,
                speaker_id=attribution.speaker_id,
                addressee_id=attribution.addressee_id,
                text=text,
                context=_context(scene.text, quote.start, quote.end),
                quote_start=quote.start,
                quote_end=quote.end,
                method=attribution.method,
                confidence=attribution.confidence,
                is_dialogue=attribution.speaker_id is not None,
            )
            utterances.append(utterance)
            if attribution.speaker_id:
                previous_speaker = attribution.speaker_id

    by_speaker = Counter(item.speaker_id or "unknown" for item in utterances)
    by_method = Counter(item.method for item in utterances)
    stats = {
        "scenes": len(scenes),
        "utterances": len(utterances),
        "dialogue": sum(1 for item in utterances if item.is_dialogue),
        "by_speaker": dict(by_speaker),
        "by_method": dict(by_method),
    }
    return utterances, stats
