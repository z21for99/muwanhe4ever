from __future__ import annotations

import sqlite3

from ..providers.embedding import EmbeddingProvider
from ..providers.llm import LLMProvider
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
    ):
        self.conn = conn
        self.llm = llm
        self.embedder = embedder
        self.top_k = top_k
        self.style_limit = style_limit

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

    def reply(
        self,
        user_message: str,
        history: list[dict] | None = None,
    ) -> str:
        vector = self.embedder.embed([user_message])[0]
        hits = search(self.conn, vector, top_k=self.top_k)
        messages = build_messages(
            CHARACTER_CORE,
            self._load_style_samples(),
            hits,
            history or [],
            user_message,
        )
        return self.llm.complete(messages)
