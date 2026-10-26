import sqlite3

from muwanhe.storage.session_db import SessionStore, init_session_db


def test_append_and_history():
    conn = sqlite3.connect(":memory:")
    init_session_db(conn)
    store = SessionStore(conn)

    store.append_exchange("s1", "A", "B")
    store.append("s1", "user", "C")

    assert store.history("s1") == [
        {"role": "user", "content": "A"},
        {"role": "assistant", "content": "B"},
        {"role": "user", "content": "C"},
    ]
    assert store.history("s1", limit=1) == [{"role": "user", "content": "C"}]
    assert store.history("missing") == []
