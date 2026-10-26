from fastapi.testclient import TestClient

from muwanhe.api import create_app


class FakeEngine:
    def reply(self, user_message: str, history: list[dict] | None = None) -> str:
        return f"echo:{user_message}"


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
