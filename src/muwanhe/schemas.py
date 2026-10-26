from __future__ import annotations

from pydantic import BaseModel, Field


class Volume(BaseModel):
    index: int
    source_index: int
    title: str
    start_line: int


class ChapterPart(BaseModel):
    part: str | None = None
    title: str = ""
    start_line: int
    end_line: int
    text: str


class Chapter(BaseModel):
    index: int
    title: str
    volume_index: int
    parts: list[ChapterPart] = Field(default_factory=list)


class Scene(BaseModel):
    id: str
    volume_index: int
    chapter_index: int
    part: str | None
    scene_index: int
    start_line: int
    end_line: int
    text: str


class ParseResult(BaseModel):
    source: str
    chars: int
    lines: int
    volumes: list[Volume]
    chapters: list[Chapter]
    scenes: list[Scene] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
