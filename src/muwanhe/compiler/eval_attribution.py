from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path


def load_gold(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["items"] if isinstance(data, dict) else data


def evaluate_attribution(
    conn: sqlite3.Connection,
    items: list[dict],
) -> dict:
    extraction_run = conn.execute("SELECT MAX(id) FROM extraction_runs").fetchone()[0]
    if extraction_run is None:
        return {"total": 0, "correct": 0, "accuracy": 0.0}

    total = 0
    correct = 0
    predicted = 0
    by_method: dict[str, Counter] = {}

    for item in items:
        expected = item.get("expected")
        row = conn.execute(
            "SELECT speaker_id, method FROM utterances "
            "WHERE id = ? AND run_id = ?",
            (item.get("utterance_id"), extraction_run),
        ).fetchone()
        got = row[0] if row else None
        method = row[1] if row else "missing"

        total += 1
        if got == expected:
            correct += 1
        if got:
            predicted += 1

        bucket = by_method.setdefault(method, Counter())
        bucket["total"] += 1
        if got == expected:
            bucket["correct"] += 1

    return {
        "extraction_run": extraction_run,
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "coverage": round(predicted / total, 4) if total else 0.0,
        "precision": round(correct / predicted, 4) if predicted else 0.0,
        "by_method": {
            method: {
                "total": counts["total"],
                "correct": counts["correct"],
            }
            for method, counts in by_method.items()
        },
    }
