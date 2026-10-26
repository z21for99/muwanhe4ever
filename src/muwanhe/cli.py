from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from .compiler.extract import extract_scenes
from .compiler.parse import parse_file
from .compiler.scenes import build_scenes
from .storage.db import init_db, save_parse_result
from .storage.extraction_db import (
    init_extraction_db,
    load_characters,
    save_extraction,
    seed_characters,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="muwanhe")
    sub = parser.add_subparsers(dest="command", required=True)

    parse = sub.add_parser("parse", help="parse a source text into SQLite")
    parse.add_argument("--input", required=True, help="path to the source .txt")
    parse.add_argument("--db", default="data/muwanhe.db", help="SQLite output path")
    parse.add_argument(
        "--volume-order",
        default=None,
        help="comma-separated volume titles in reading order",
    )

    extract = sub.add_parser("extract", help="extract dialogue from parsed scenes")
    extract.add_argument("--db", default="data/muwanhe.db", help="SQLite path")
    extract.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max number of scenes to process",
    )
    return parser


def _parse(args: argparse.Namespace) -> int:
    volume_order = None
    if args.volume_order:
        volume_order = [
            item.strip()
            for item in args.volume_order.split(",")
            if item.strip()
        ]

    result = parse_file(Path(args.input), volume_order=volume_order)
    result.scenes = build_scenes(result.chapters)

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        init_db(conn)
        run_id = save_parse_result(conn, result)
    finally:
        conn.close()

    summary = {
        "run_id": run_id,
        "source": result.source,
        "chars": result.chars,
        "lines": result.lines,
        "volumes": len(result.volumes),
        "chapters": len(result.chapters),
        "parts": sum(len(chapter.parts) for chapter in result.chapters),
        "scenes": len(result.scenes),
        "anomalies": result.anomalies,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _extract(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    conn = sqlite3.connect(db_path)
    try:
        init_extraction_db(conn)
        seed_characters(conn)
        characters = load_characters(conn)
        utterances, stats = extract_scenes(conn, characters, args.limit)
        run_id = save_extraction(conn, utterances, stats, args.limit)
    finally:
        conn.close()

    summary = {"run_id": run_id, **stats}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "parse":
        return _parse(args)
    if args.command == "extract":
        return _extract(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
