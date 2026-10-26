from __future__ import annotations

import json
import time
import uuid
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from .web import INDEX_HTML
from .storage.session_db import SessionStore


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


def _chunk(
    completion_id: str,
    created: int,
    content: str,
    finish_reason: str | None = None,
) -> str:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": "muwanhe",
        "choices": [
            {
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def create_app(
    engine: ReplyEngine,
    sessions: SessionStore | None = None,
) -> FastAPI:
    app = FastAPI(title="muwanhe", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

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
    def chat(request: ChatRequest) -> Any:
        if not request.messages:
            raise HTTPException(status_code=400, detail="messages is empty")

        user_message = request.messages[-1].get("content", "")
        client_history = [
            {"role": message.get("role"), "content": message.get("content")}
            for message in request.messages[:-1]
            if message.get("role") in ("user", "assistant")
            and message.get("content")
        ]
        session_id = request.user or "local"
        if sessions and not client_history:
            history = sessions.history(session_id)
        else:
            history = client_history
        reply = engine.reply(str(user_message), history)
        if sessions:
            sessions.append_exchange(session_id, str(user_message), reply)
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())

        if request.stream:
            def generate():
                for start in range(0, len(reply), 4):
                    yield _chunk(completion_id, created, reply[start : start + 4])
                yield _chunk(completion_id, created, "", "stop")
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
            )

        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
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
