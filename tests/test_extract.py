import sqlite3

from muwanhe.compiler.extract import extract_scenes
from muwanhe.storage.db import init_db
from muwanhe.storage.extraction_db import (
    init_extraction_db,
    load_characters,
    save_extraction,
    seed_characters,
)


def _scene_db(
    text: str = "“你好。”我说。\n她轻声道：“过来。”",
) -> sqlite3.Connection:
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
            "v01c01p0s00",
            1,
            1,
            1,
            None,
            0,
            1,
            3,
            text,
        ),
    )
    conn.commit()
    init_extraction_db(conn)
    seed_characters(conn)
    return conn


def test_extract_and_save():
    conn = _scene_db()
    characters = load_characters(conn)

    utterances, stats = extract_scenes(conn, characters)

    assert len(utterances) == 2
    assert utterances[0].speaker_id == "baifengyuan"
    assert utterances[1].speaker_id == "muwanhe"
    assert stats["utterances"] == 2
    assert stats["by_speaker"]["muwanhe"] == 1
    assert stats["by_method"]["cue"] == 2

    run_id = save_extraction(conn, utterances, stats)

    assert run_id == 1
    assert conn.execute("SELECT COUNT(*) FROM utterances").fetchone()[0] == 2


def test_strict_marks_unverified():
    conn = _scene_db("“没有线索的引语。”")
    characters = load_characters(conn)

    utterances, stats = extract_scenes(conn, characters, strict=True)

    assert len(utterances) == 1
    assert utterances[0].speaker_id is None
    assert utterances[0].method == "unverified"
    assert stats["by_method"]["unverified"] == 1
