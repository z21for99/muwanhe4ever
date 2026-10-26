import json
import sqlite3

from muwanhe.compiler.eval_attribution import evaluate_attribution, load_gold
from muwanhe.storage.extraction_db import init_extraction_db


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_extraction_db(conn)
    conn.execute(
        "INSERT INTO extraction_runs (scene_limit, created_at, stats) "
        "VALUES (1, 'now', '{}')"
    )
    rows = [
        ("u1", "muwanhe", "cue"),
        ("u2", "father", "cue"),
        ("u3", None, "unverified"),
    ]
    for utterance_id, speaker, method in rows:
        conn.execute(
            "INSERT INTO utterances "
            "(id, run_id, scene_id, speaker_id, addressee_id, text, context, "
            "quote_start, quote_end, method, confidence, is_dialogue) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                utterance_id,
                1,
                "s1",
                speaker,
                None,
                "x",
                "ctx",
                1,
                2,
                method,
                0.9,
                1,
            ),
        )
    conn.commit()
    return conn


def test_evaluate_attribution():
    conn = _db()

    stats = evaluate_attribution(
        conn,
        [
            {"utterance_id": "u1", "expected": "muwanhe"},
            {"utterance_id": "u2", "expected": "muwanhe"},
        ],
    )

    assert stats["total"] == 2
    assert stats["correct"] == 1
    assert stats["accuracy"] == 0.5
    assert stats["coverage"] == 1.0
    assert stats["precision"] == 0.5


def test_unknown_expected_matches_unpredicted():
    conn = _db()

    stats = evaluate_attribution(
        conn,
        [
            {"utterance_id": "u1", "expected": "muwanhe"},
            {"utterance_id": "u3", "expected": "unknown"},
        ],
    )

    assert stats["total"] == 2
    assert stats["correct"] == 2
    assert stats["coverage"] == 0.5
    assert stats["precision"] == 1.0


def test_load_gold(tmp_path):
    path = tmp_path / "gold.json"
    path.write_text(
        json.dumps({"items": [{"utterance_id": "u1", "expected": "muwanhe"}]}),
        encoding="utf-8",
    )

    assert load_gold(path) == [{"utterance_id": "u1", "expected": "muwanhe"}]
