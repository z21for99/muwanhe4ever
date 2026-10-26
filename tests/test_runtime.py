import sqlite3

from muwanhe.providers.embedding import EmbeddingError, FakeEmbeddingProvider
from muwanhe.providers.llm import FakeLLM
from muwanhe.runtime.engine import CharacterEngine
from muwanhe.storage.extraction_db import init_extraction_db
from muwanhe.storage.fts_store import init_fts_db
from muwanhe.storage.vector_store import (
    EmbeddingRecord,
    init_vector_db,
    upsert_embeddings,
)


def test_engine_reply_uses_style_and_evidence(tmp_path):
    profile = tmp_path / "profile.md"
    profile.write_text("她怕黑。", encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    init_extraction_db(conn)
    conn.execute(
        "INSERT INTO style_samples "
        "(id, mode_id, utterance_id, text, context, markedness, tags) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("s1", "m1", "u1", "吃饭了吗？", "ctx", "special", "{}"),
    )
    conn.commit()
    init_vector_db(conn)
    upsert_embeddings(
        conn,
        [
            EmbeddingRecord(
                id="scene:s1",
                kind="scene",
                ref_id="s1",
                text="雨夜，白风远回到家。",
                vector=[1.0, 0.0, 0.0, 0.0],
                model="fake",
                dim=4,
            )
        ],
    )

    llm = FakeLLM(text="妈在呢。")
    engine = CharacterEngine(
        conn,
        llm,
        FakeEmbeddingProvider(dimensions=4),
        profile_path=profile,
    )

    reply = engine.reply("我回来了")

    assert reply == "妈在呢。"
    system = llm.chat_calls[0][0]["content"]
    assert "雨夜" in system
    assert "吃饭了吗？" in system
    assert "她怕黑。" in system
    assert "白风远本人" in system
    assert "全书结尾之后" in system


class BrokenEmbedder:
    dimensions = 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingError("quota exhausted")


def test_engine_falls_back_to_fts():
    conn = sqlite3.connect(":memory:")
    init_extraction_db(conn)
    init_fts_db(conn)
    conn.execute(
        "INSERT INTO docs_fts (doc_id, kind, ref_id, text) "
        "VALUES (?, ?, ?, ?)",
        ("scene:s1", "scene", "s1", "雨夜回家"),
    )
    conn.commit()

    llm = FakeLLM(text="妈在呢。")
    engine = CharacterEngine(conn, llm, BrokenEmbedder())

    reply = engine.reply("雨夜")

    assert reply == "妈在呢。"
    assert "雨夜回家" in llm.chat_calls[0][0]["content"]
