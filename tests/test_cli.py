import json
import sqlite3
from pathlib import Path

from muwanhe.cli import main


def test_cli_parse(tmp_path: Path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("第一卷 甲篇\n第1章\nhello\n", encoding="utf-8")
    db = tmp_path / "book.db"

    assert main(["parse", "--input", str(source), "--db", str(db)]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["volumes"] == 1
    assert out["chapters"] == 1
    assert out["parts"] == 1
    assert out["scenes"] == 1

    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0] == 1


def test_cli_reorders_volumes(tmp_path: Path, capsys):
    source = tmp_path / "book.txt"
    source.write_text(
        "第一卷 甲篇\n第1章\na\n第二卷 乙篇\n第1章\nb\n",
        encoding="utf-8",
    )
    db = tmp_path / "book.db"

    assert main(
        [
            "parse",
            "--input",
            str(source),
            "--db",
            str(db),
            "--volume-order",
            "乙篇,甲篇",
        ]
    ) == 0

    conn = sqlite3.connect(db)
    titles = [
        row[0]
        for row in conn.execute(
            "SELECT title FROM volumes ORDER BY volume_index"
        )
    ]
    assert titles == ["乙篇", "甲篇"]
