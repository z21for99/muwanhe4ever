from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openai import BadRequestError, OpenAI


class LLMError(RuntimeError):
    pass


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def extract_json(text: str) -> dict | list:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            return json.loads(cleaned[start : end + 1])
        raise


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.0
    timeout: float = 180.0

    @classmethod
    def from_env(cls) -> "LLMSettings":
        load_env_file()
        api_key = os.getenv("LLM_API_KEY") or os.getenv("ARK_API_KEY", "")
        base_url = os.getenv("LLM_BASE_URL") or os.getenv("ARK_BASE_URL", "")
        model = os.getenv("LLM_MODEL", "")
        if not api_key or not base_url or not model:
            raise LLMError(
                "LLM is not configured: set LLM_API_KEY/LLM_BASE_URL/LLM_MODEL "
                "(or ARK_API_KEY/ARK_BASE_URL)"
            )
        return cls(api_key=api_key, base_url=base_url, model=model)


class LLMProvider(Protocol):
    def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
    ) -> dict | list: ...

    def complete(
        self,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> str: ...


class OpenAICompatLLM:
    def __init__(self, settings: LLMSettings):
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout,
        )

    def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
    ) -> dict | list:
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": self.settings.temperature,
            "max_tokens": max_tokens,
        }
        try:
            response = self.client.chat.completions.create(
                **payload,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except BadRequestError:
            response = self.client.chat.completions.create(**payload)

        content = response.choices[0].message.content or ""
        try:
            return extract_json(content)
        except Exception as exc:
            raise LLMError(f"invalid JSON from model: {content[:300]}") from exc

    def complete(
        self,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> str:
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "max_tokens": max_tokens,
        }
        try:
            response = self.client.chat.completions.create(
                **payload,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except BadRequestError:
            response = self.client.chat.completions.create(**payload)
        return response.choices[0].message.content or ""


class FakeLLM:
    def __init__(self, response: dict | list | None = None, text: str = "fake reply"):
        self.response = response if response is not None else {}
        self.text = text
        self.calls: list[tuple[str, str]] = []
        self.chat_calls: list[list[dict]] = []

    def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
    ) -> dict | list:
        self.calls.append((system, user))
        return self.response

    def complete(
        self,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> str:
        self.chat_calls.append(messages)
        return self.text
