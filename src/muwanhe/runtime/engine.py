from __future__ import annotations

import sqlite3
from pathlib import Path

from ..providers.embedding import EmbeddingError, EmbeddingProvider
from ..providers.llm import LLMProvider
from ..storage.fts_store import search_fts
from ..storage.vector_store import search
from .prompt import CHARACTER_CORE, build_messages


class CharacterEngine:
    def __init__(
        self,
        conn: sqlite3.Connection,
        llm: LLMProvider,
        embedder: EmbeddingProvider,
        top_k: int = 3,
        style_limit: int = 5,
        profile_path: str | Path | None = None,
    ):
        self.conn = conn
        self.llm = llm
        self.embedder = embedder
        self.top_k = top_k
        self.style_limit = style_limit
        self.profile_path = Path(profile_path) if profile_path else None

    def _load_profile(self) -> str:
        if self.profile_path and self.profile_path.exists():
            return self.profile_path.read_text(encoding="utf-8").strip()
        return ""

    def _load_style_samples(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT text, context, mode_id FROM style_samples "
            "ORDER BY markedness DESC, id LIMIT ?",
            (self.style_limit,),
        ).fetchall()
        return [
            {"text": row[0], "context": row[1], "mode_id": row[2]}
            for row in rows
        ]

    def _retrieve(self, user_message: str) -> list:
        vector_hits = []
        try:
            vector = self.embedder.embed([user_message])[0]
            vector_hits = search(self.conn, vector, top_k=self.top_k)
        except EmbeddingError:
            vector_hits = []

        try:
            fts_hits = search_fts(self.conn, user_message, top_k=self.top_k)
        except sqlite3.OperationalError:
            fts_hits = []

        seen: set[str] = set()
        hits = []
        for hit in vector_hits + fts_hits:
            if hit.id in seen:
                continue
            seen.add(hit.id)
            hits.append(hit)
        return hits[: self.top_k]

    def reply(
        self,
        user_message: str,
        history: list[dict] | None = None,
    ) -> str:
        hits = self._retrieve(user_message)
        messages = build_messages(
            CHARACTER_CORE,
            self._load_style_samples(),
            hits,
            history or [],
            user_message,
            profile=self._load_profile(),
        )
        return self.llm.complete(messages)
