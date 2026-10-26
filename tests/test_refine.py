import json
import sqlite3

from muwanhe.compiler.refine import refine_attributions
from muwanhe.providers.llm import FakeLLM
from muwanhe.storage.db import init_db
from muwanhe.storage.extraction_db import init_extraction_db, seed_characters


def _refine_db() -> sqlite3.Connection:
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
        (
            "s1",
            1,
            1,
            1,
            None,
            0,
            1,
            2,
            "“你来了。”她说。\n“嗯。”我说。",
        ),
    )
    init_extraction_db(conn)
    seed_characters(conn)
    conn.execute(
        "INSERT INTO extraction_runs (scene_limit, created_at, stats) "
        "VALUES (1, 'now', '{}')"
    )
    conn.execute(
        "INSERT INTO utterances "
        "(id, run_id, scene_id, speaker_id, addressee_id, text, context, "
        "quote_start, quote_end, method, confidence, is_dialogue) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "s1:q000",
            1,
            "s1",
            None,
            None,
            "你来了。",
            "“你来了。”她说。",
            1,
            5,
            "turn",
            0.4,
            1,
        ),
    )
    conn.commit()
    return conn


def test_refine_updates_utterance_and_stores_segments():
    conn = _refine_db()
    fake = FakeLLM(
        {
            "attributions": [
                {
                    "index": 0,
                    "speaker": "muwanhe",
                    "addressee": "baifengyuan",
                    "confidence": 0.9,
                }
            ],
            "segments": [
                {
                    "start": 0,
                    "end": 1,
                    "summary": "两人对话",
                    "location": "家",
                    "time": "晚上",
                    "participants": ["baifengyuan", "muwanhe"],
                }
            ],
        }
    )

    stats = refine_attributions(conn, fake, "fake-model", limit=1)

    assert stats["updated"] == 1
    assert stats["segments"] == 1
    assert stats["by_speaker"] == {"muwanhe": 1}

    row = conn.execute(
        "SELECT speaker_id, addressee_id, method, confidence FROM utterances "
        "WHERE id = 's1:q000'"
    ).fetchone()
    assert row == ("muwanhe", "baifengyuan", "llm", 0.9)

    segment = conn.execute(
        "SELECT scene_id, start_line, end_line, participants FROM segments"
    ).fetchone()
    assert segment[0] == "s1"
    assert segment[1] == 0
    assert segment[2] == 1
    assert json.loads(segment[3]) == ["baifengyuan", "muwanhe"]


def test_segments_only_skips_attribution():
    conn = _refine_db()
    fake = FakeLLM(
        {
            "segments": [
                {
                    "start": 0,
                    "end": 1,
                    "summary": "两人对话",
                    "location": "家",
                    "time": "晚上",
                    "participants": ["baifengyuan", "muwanhe"],
                }
            ]
        }
    )

    stats = refine_attributions(
        conn, fake, "fake-model", limit=1, segments_only=True
    )

    assert stats["mode"] == "segments_only"
    assert stats["updated"] == 0
    assert stats["segments"] == 1
    row = conn.execute(
        "SELECT method FROM utterances WHERE id = 's1:q000'"
    ).fetchone()
    assert row == ("turn",)
