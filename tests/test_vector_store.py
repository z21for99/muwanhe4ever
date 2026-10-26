import sqlite3

from muwanhe.storage.vector_store import (
    EmbeddingRecord,
    count_embeddings,
    init_vector_db,
    search,
    upsert_embeddings,
)


def test_upsert_and_search():
    conn = sqlite3.connect(":memory:")
    init_vector_db(conn)
    upsert_embeddings(
        conn,
        [
            EmbeddingRecord(
                id="scene:a",
                kind="scene",
                ref_id="a",
                text="apple",
                vector=[1.0, 0.0, 0.0],
                model="fake",
                dim=3,
            ),
            EmbeddingRecord(
                id="scene:b",
                kind="scene",
                ref_id="b",
                text="banana",
                vector=[0.0, 1.0, 0.0],
                model="fake",
                dim=3,
            ),
            EmbeddingRecord(
                id="segment:c",
                kind="segment",
                ref_id="c",
                text="cherry",
                vector=[0.0, 0.0, 1.0],
                model="fake",
                dim=3,
            ),
        ],
    )

    hits = search(conn, [1.0, 0.0, 0.0], top_k=2)

    assert hits[0].ref_id == "a"
    assert hits[0].score == 1.0
    assert count_embeddings(conn) == 3
    assert count_embeddings(conn, "segment") == 1

    segment_hits = search(conn, [0.0, 0.0, 1.0], kind="segment", top_k=5)
    assert [hit.ref_id for hit in segment_hits] == ["c"]
