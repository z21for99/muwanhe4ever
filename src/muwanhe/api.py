from __future__ import annotations

import time
import uuid
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class ChatRequest(BaseModel):
    model: str = "muwanhe"
    messages: list[dict[str, Any]]
    stream: bool = False
    user: str | None = None


class ReplyEngine(Protocol):
    def reply(
        self,
        user_message: str,
        history: list[dict] | None = None,
    ) -> str: ...


def create_app(engine: ReplyEngine) -> FastAPI:
    app = FastAPI(title="muwanhe", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/v1/models")
    def models() -> dict:
        return {
            "object": "list",
            "data": [
                {
                    "id": "muwanhe",
                    "object": "model",
                    "owned_by": "local",
                }
            ],
        }

    @app.post("/v1/chat/completions")
    def chat(request: ChatRequest) -> dict:
        if request.stream:
            raise HTTPException(status_code=400, detail="streaming not implemented yet")
        if not request.messages:
            raise HTTPException(status_code=400, detail="messages is empty")

        user_message = request.messages[-1].get("content", "")
        history = [
            {"role": message.get("role"), "content": message.get("content")}
            for message in request.messages[:-1]
            if message.get("role") in ("user", "assistant")
            and message.get("content")
        ]
        reply = engine.reply(str(user_message), history)
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "muwanhe",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": reply},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    return app
