from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from openai import APIStatusError, OpenAI, RateLimitError

from .llm import LLMError, load_env_file


class EmbeddingError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmbeddingSettings:
    api_key: str
    base_url: str
    model: str
    dimensions: int = 1024

    @classmethod
    def from_env(cls) -> "EmbeddingSettings":
        load_env_file()
        api_key = os.getenv("QWEN_API_KEY", "")
        base_url = os.getenv(
            "QWEN_BASE_URL",
            "https://maas.qianwenaiapi.com/compatible-mode/v1",
        )
        model = os.getenv(
            "QWEN_EMBEDDING_MODEL",
            "qwen3.7-text-embedding-flash",
        )
        dimensions = int(os.getenv("QWEN_EMBEDDING_DIM", "1024"))
        if not api_key:
            raise LLMError("QWEN_API_KEY is not configured")
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            dimensions=dimensions,
        )


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class QwenEmbeddingProvider:
    def __init__(self, settings: EmbeddingSettings):
        self.settings = settings
        self.dimensions = settings.dimensions
        self.client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=120.0,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 20):
            batch = texts[start : start + 20]
            try:
                response = self.client.embeddings.create(
                    model=self.settings.model,
                    input=batch,
                    dimensions=self.settings.dimensions,
                    encoding_format="float",
                )
            except RateLimitError as exc:
                raise EmbeddingError(
                    "Qwen embedding quota/rate limit exceeded; "
                    "enable billing or wait for the quota to reset"
                ) from exc
            except APIStatusError as exc:
                raise EmbeddingError(
                    f"Qwen embedding API error: HTTP {exc.status_code}"
                ) from exc
            vectors.extend(item.embedding for item in response.data)
        return vectors


class FakeEmbeddingProvider:
    def __init__(self, dimensions: int = 8):
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for index, character in enumerate(text):
                vector[index % self.dimensions] += (ord(character) % 17) / 17.0
            if not any(vector):
                vector[0] = 1.0
            vectors.append(vector)
        return vectors
