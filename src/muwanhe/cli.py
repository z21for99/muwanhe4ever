from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import uvicorn

from .api import create_app
from .compiler.eval_attribution import evaluate_attribution, load_gold
from .compiler.eval_retrieval import evaluate_retrieval, evaluate_retrieval_fts
from .compiler.extract import extract_scenes
from .compiler.index import index_documents
from .compiler.parse import parse_file
from .compiler.refine import refine_attributions
from .compiler.scenes import build_scenes
from .compiler.style import build_style_bank
from .providers.embedding import (
    EmbeddingError,
    EmbeddingSettings,
    QwenEmbeddingProvider,
)
from .providers.llm import LLMError, LLMSettings, OpenAICompatLLM
from .runtime.engine import CharacterEngine
from .storage.db import init_db, save_parse_result
from .storage.extraction_db import (
    init_extraction_db,
    load_characters,
    save_extraction,
    seed_characters,
)
from .storage.fts_store import init_fts_db, rebuild_fts, search_fts
from .storage.session_db import SessionStore, init_session_db
from .storage.vector_store import init_vector_db
from .storage.vector_store import search as search_embeddings


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
    extract.add_argument(
        "--strict",
        action="store_true",
        help="only keep cue/voice/vocative attributions; mark the rest unverified",
    )

    refine = sub.add_parser(
        "refine",
        help="LLM refine low-confidence speaker attribution",
    )
    refine.add_argument("--db", default="data/muwanhe.db", help="SQLite path")
    refine.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max number of scenes to process",
    )
    refine.add_argument("--model", default=None, help="override LLM model")
    refine.add_argument(
        "--segments-only",
        action="store_true",
        help="only produce scene segments, do not update attributions",
    )
    refine.add_argument("--offset", type=int, default=0)

    index = sub.add_parser("index", help="embed scenes/segments into the vector store")
    index.add_argument("--db", default="data/muwanhe.db", help="SQLite path")
    index.add_argument(
        "--kind",
        choices=["all", "scene", "segment"],
        default="all",
    )
    index.add_argument("--limit", type=int, default=None)
    index.add_argument("--offset", type=int, default=0)
    index.add_argument("--model", default=None, help="override embedding model")
    index.add_argument("--dim", type=int, default=None, help="override dimensions")

    search_cmd = sub.add_parser("search", help="semantic search over indexed docs")
    search_cmd.add_argument("--db", default="data/muwanhe.db", help="SQLite path")
    search_cmd.add_argument("--query", required=True)
    search_cmd.add_argument(
        "--kind",
        choices=["scene", "segment"],
        default=None,
    )
    search_cmd.add_argument("--top-k", type=int, default=5)

    style = sub.add_parser("style", help="build the style bank from strict utterances")
    style.add_argument("--db", default="data/muwanhe.db", help="SQLite path")
    style.add_argument("--min-samples", type=int, default=3)
    style.add_argument(
        "--all",
        action="store_true",
        help="include vocative and all cue methods (lower precision)",
    )
    style.add_argument(
        "--window",
        type=int,
        default=8,
        help="adjacent cue window in characters",
    )

    chat = sub.add_parser("chat", help="one-shot character reply")
    chat.add_argument("--db", default="data/muwanhe.db", help="SQLite path")
    chat.add_argument("--message", required=True)
    chat.add_argument("--model", default=None, help="override LLM model")
    chat.add_argument("--top-k", type=int, default=3)
    chat.add_argument("--style-limit", type=int, default=5)

    serve = sub.add_parser("serve", help="serve the OpenAI-compatible local API")
    serve.add_argument("--db", default="data/muwanhe.db", help="SQLite path")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--model", default=None, help="override LLM model")

    eval_retrieval = sub.add_parser(
        "eval-retrieval",
        help="leave-one-out scene retrieval evaluation",
    )
    eval_retrieval.add_argument("--db", default="data/muwanhe.db")
    eval_retrieval.add_argument("--limit", type=int, default=20)
    eval_retrieval.add_argument("--top-k", type=int, default=5)
    eval_retrieval.add_argument("--model", default=None)
    eval_retrieval.add_argument(
        "--mode",
        choices=["vector", "fts"],
        default="vector",
    )

    index_fts = sub.add_parser("index-fts", help="build the SQLite FTS5 index")
    index_fts.add_argument("--db", default="data/muwanhe.db")

    search_fts_cmd = sub.add_parser("search-fts", help="keyword search over FTS5")
    search_fts_cmd.add_argument("--db", default="data/muwanhe.db")
    search_fts_cmd.add_argument("--query", required=True)
    search_fts_cmd.add_argument(
        "--kind",
        choices=["scene", "segment"],
        default=None,
    )
    search_fts_cmd.add_argument("--top-k", type=int, default=5)

    eval_attr = sub.add_parser(
        "eval-attribution",
        help="evaluate speaker attribution against a gold file",
    )
    eval_attr.add_argument("--db", default="data/muwanhe.db")
    eval_attr.add_argument(
        "--gold",
        default="eval/attribution_gold.json",
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
        utterances, stats = extract_scenes(
            conn, characters, args.limit, strict=args.strict
        )
        run_id = save_extraction(conn, utterances, stats, args.limit)
    finally:
        conn.close()

    summary = {"run_id": run_id, **stats}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _refine(args: argparse.Namespace) -> int:
    try:
        settings = LLMSettings.from_env()
    except LLMError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    if args.model:
        settings = replace(settings, model=args.model)

    conn = sqlite3.connect(Path(args.db))
    try:
        init_extraction_db(conn)
        stats = refine_attributions(
            conn,
            OpenAICompatLLM(settings),
            settings.model,
            args.limit,
            segments_only=args.segments_only,
            offset=args.offset,
        )
    finally:
        conn.close()

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def _index(args: argparse.Namespace) -> int:
    try:
        settings = EmbeddingSettings.from_env()
    except LLMError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    if args.model:
        settings = replace(settings, model=args.model)
    if args.dim:
        settings = replace(settings, dimensions=args.dim)

    conn = sqlite3.connect(Path(args.db))
    try:
        init_extraction_db(conn)
        init_vector_db(conn)
        kinds = ("scene", "segment") if args.kind == "all" else (args.kind,)
        stats = index_documents(
            conn,
            QwenEmbeddingProvider(settings),
            settings.model,
            kinds,
            args.limit,
            args.offset,
        )
    except EmbeddingError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    finally:
        conn.close()

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def _search(args: argparse.Namespace) -> int:
    try:
        settings = EmbeddingSettings.from_env()
    except LLMError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2

    conn = sqlite3.connect(Path(args.db))
    try:
        init_vector_db(conn)
        provider = QwenEmbeddingProvider(settings)
        try:
            vector = provider.embed([args.query])[0]
        except EmbeddingError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return 2
        hits = search_embeddings(conn, vector, args.kind, args.top_k)
    finally:
        conn.close()

    print(
        json.dumps(
            [
                {
                    "id": hit.id,
                    "kind": hit.kind,
                    "ref_id": hit.ref_id,
                    "score": round(hit.score, 4),
                    "text": hit.text[:200],
                }
                for hit in hits
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _style(args: argparse.Namespace) -> int:
    conn = sqlite3.connect(Path(args.db))
    try:
        init_extraction_db(conn)
        stats = build_style_bank(
            conn,
            args.min_samples,
            precision=not args.all,
            window=args.window,
        )
    finally:
        conn.close()

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def _profile_path() -> Path | None:
    path = Path("data/muwanhe_profile.md")
    return path if path.exists() else None


def _chat(args: argparse.Namespace) -> int:
    try:
        llm_settings = LLMSettings.from_env()
        embedding_settings = EmbeddingSettings.from_env()
    except LLMError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    if args.model:
        llm_settings = replace(llm_settings, model=args.model)

    conn = sqlite3.connect(Path(args.db))
    try:
        init_extraction_db(conn)
        init_vector_db(conn)
        init_fts_db(conn)
        engine = CharacterEngine(
            conn,
            OpenAICompatLLM(llm_settings),
            QwenEmbeddingProvider(embedding_settings),
            top_k=args.top_k,
            style_limit=args.style_limit,
            profile_path=_profile_path(),
        )
        try:
            reply = engine.reply(args.message)
        except (EmbeddingError, LLMError) as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return 2
    finally:
        conn.close()

    print(reply)
    return 0


def _serve(args: argparse.Namespace) -> int:
    try:
        llm_settings = LLMSettings.from_env()
        embedding_settings = EmbeddingSettings.from_env()
    except LLMError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    if args.model:
        llm_settings = replace(llm_settings, model=args.model)

    conn = sqlite3.connect(Path(args.db), check_same_thread=False)
    init_extraction_db(conn)
    init_vector_db(conn)
    init_fts_db(conn)
    init_session_db(conn)
    engine = CharacterEngine(
        conn,
        OpenAICompatLLM(llm_settings),
        QwenEmbeddingProvider(embedding_settings),
        profile_path=_profile_path(),
    )
    uvicorn.run(
        create_app(engine, sessions=SessionStore(conn)),
        host=args.host,
        port=args.port,
    )
    return 0


def _eval_retrieval(args: argparse.Namespace) -> int:
    if args.mode == "fts":
        conn = sqlite3.connect(Path(args.db))
        try:
            init_fts_db(conn)
            stats = evaluate_retrieval_fts(conn, args.limit, args.top_k)
        finally:
            conn.close()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    try:
        settings = EmbeddingSettings.from_env()
    except LLMError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    if args.model:
        settings = replace(settings, model=args.model)

    conn = sqlite3.connect(Path(args.db))
    try:
        init_vector_db(conn)
        stats = evaluate_retrieval(
            conn,
            QwenEmbeddingProvider(settings),
            args.limit,
            args.top_k,
        )
    except EmbeddingError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    finally:
        conn.close()

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def _index_fts(args: argparse.Namespace) -> int:
    conn = sqlite3.connect(Path(args.db))
    try:
        init_extraction_db(conn)
        init_fts_db(conn)
        stats = rebuild_fts(conn)
    finally:
        conn.close()

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def _search_fts(args: argparse.Namespace) -> int:
    conn = sqlite3.connect(Path(args.db))
    try:
        init_fts_db(conn)
        hits = search_fts(conn, args.query, args.kind, args.top_k)
    finally:
        conn.close()

    print(
        json.dumps(
            [
                {
                    "id": hit.id,
                    "kind": hit.kind,
                    "ref_id": hit.ref_id,
                    "score": hit.score,
                    "text": hit.text[:200],
                }
                for hit in hits
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _eval_attribution(args: argparse.Namespace) -> int:
    items = load_gold(args.gold)
    conn = sqlite3.connect(Path(args.db))
    try:
        init_extraction_db(conn)
        stats = evaluate_attribution(conn, items)
    finally:
        conn.close()

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "parse":
        return _parse(args)
    if args.command == "extract":
        return _extract(args)
    if args.command == "refine":
        return _refine(args)
    if args.command == "index":
        return _index(args)
    if args.command == "search":
        return _search(args)
    if args.command == "style":
        return _style(args)
    if args.command == "chat":
        return _chat(args)
    if args.command == "serve":
        return _serve(args)
    if args.command == "eval-retrieval":
        return _eval_retrieval(args)
    if args.command == "index-fts":
        return _index_fts(args)
    if args.command == "search-fts":
        return _search_fts(args)
    if args.command == "eval-attribution":
        return _eval_attribution(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
