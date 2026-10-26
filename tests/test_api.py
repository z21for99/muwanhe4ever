import sqlite3

from fastapi.testclient import TestClient

from muwanhe.api import create_app
from muwanhe.storage.session_db import SessionStore, init_session_db


class FakeEngine:
    def reply(self, user_message: str, history: list[dict] | None = None) -> str:
        return f"echo:{user_message}"


class RecordingEngine:
    def __init__(self):
        self.calls: list[tuple[str, list[dict] | None]] = []

    def reply(self, user_message: str, history: list[dict] | None = None) -> str:
        self.calls.append((user_message, history))
        return f"reply:{user_message}"


def test_health_and_models():
    client = TestClient(create_app(FakeEngine()))

    assert client.get("/health").json() == {"status": "ok"}
    models = client.get("/v1/models").json()
    assert models["data"][0]["id"] == "muwanhe"


def test_chat_completion():
    client = TestClient(create_app(FakeEngine()))

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "muwanhe",
            "messages": [{"role": "user", "content": "我回来了"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "echo:我回来了"


def test_web_page():
    client = TestClient(create_app(FakeEngine()))

    response = client.get("/")

    assert response.status_code == 200
    assert "沐婉荷" in response.text
    assert "/v1/chat/completions" in response.text
    assert "重新开始" in response.text
    assert "/api/session/" in response.text


def test_streaming_chat():
    client = TestClient(create_app(FakeEngine()))

    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "muwanhe",
            "messages": [{"role": "user", "content": "我回来了"}],
            "stream": True,
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "data: " in body
    assert "[DONE]" in body
    assert "echo" in body


def test_session_history_is_reused():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    init_session_db(conn)
    engine = RecordingEngine()
    client = TestClient(create_app(engine, sessions=SessionStore(conn)))

    client.post(
        "/v1/chat/completions",
        json={
            "model": "muwanhe",
            "user": "u1",
            "messages": [{"role": "user", "content": "A"}],
        },
    )
    client.post(
        "/v1/chat/completions",
        json={
            "model": "muwanhe",
            "user": "u1",
            "messages": [{"role": "user", "content": "B"}],
        },
    )

    assert engine.calls[1][1] == [
        {"role": "user", "content": "A"},
        {"role": "assistant", "content": "reply:A"},
    ]


def test_session_endpoints():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    init_session_db(conn)
    client = TestClient(create_app(FakeEngine(), sessions=SessionStore(conn)))

    client.post(
        "/v1/chat/completions",
        json={
            "model": "muwanhe",
            "user": "u2",
            "messages": [{"role": "user", "content": "A"}],
        },
    )

    messages = client.get("/api/session/u2").json()["messages"]
    assert messages[0]["content"] == "A"
    assert messages[1]["content"] == "echo:A"

    assert client.delete("/api/session/u2").json() == {"ok": True}
    assert client.get("/api/session/u2").json()["messages"] == []
