import json
from pathlib import Path

from muwanhe.cli import main


def test_cli_extract(tmp_path: Path, capsys):
    source = tmp_path / "book.txt"
    source.write_text(
        "第一卷 甲篇\n第1章\n“你好。”我说。\n她轻声道：“过来。”\n",
        encoding="utf-8",
    )
    db = tmp_path / "book.db"

    assert main(["parse", "--input", str(source), "--db", str(db)]) == 0
    capsys.readouterr()

    assert main(["extract", "--db", str(db), "--limit", "5"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["utterances"] == 2
    assert out["by_speaker"]["muwanhe"] == 1
