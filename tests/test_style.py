import sqlite3

from muwanhe.compiler.style import _is_explicit_cue, build_style_bank, tag_utterance
from muwanhe.storage.extraction_db import init_extraction_db


def test_tag_anger():
    tags = tag_utterance("你滚！", "baifengyuan")

    assert tags["scene_type"] == "对儿子"
    assert tags["emotion"] == "anger"
    assert tags["intent"] == "拒绝"
    assert tags["power"] == "长辈"
    assert tags["markedness"] == "special"


def test_tag_tender():
    tags = tag_utterance("吃饭了吗？", "baifengyuan")

    assert tags["emotion"] == "tender"
    assert tags["intent"] == "关心"


def test_build_style_bank():
    conn = sqlite3.connect(":memory:")
    init_extraction_db(conn)
    conn.execute(
        "INSERT INTO extraction_runs (scene_limit, created_at, stats) "
        "VALUES (1, 'now', '{}')"
    )
    for index, text in enumerate(["你滚！", "吃饭了吗？", "没事，不用管我。"]):
        conn.execute(
            "INSERT INTO utterances "
            "(id, run_id, scene_id, speaker_id, addressee_id, text, context, "
            "quote_start, quote_end, method, confidence, is_dialogue) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"u{index}",
                1,
                "s1",
                "muwanhe",
                "baifengyuan",
                text,
                "ctx",
                index,
                index + 1,
                "cue",
                0.9,
                1,
            ),
        )
    conn.commit()

    stats = build_style_bank(conn, min_samples=1, precision=False)

    assert stats["muwanhe_utterances"] == 3
    assert stats["modes"] == 3
    assert stats["samples"] == 3
    assert stats["precision"] is False
    assert conn.execute("SELECT COUNT(*) FROM style_samples").fetchone()[0] == 3


def test_is_explicit_cue():
    assert _is_explicit_cue("母亲说：", "", "", "")
    assert not _is_explicit_cue("她轻声说：", "", "", "")
    assert _is_explicit_cue("", "", "母亲的声音", "")
