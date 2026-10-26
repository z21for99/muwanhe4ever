from __future__ import annotations

from ..schemas import Chapter, ChapterPart, Scene
from .headings import SEPARATOR_RE


def build_scenes(chapters: list[Chapter]) -> list[Scene]:
    scenes: list[Scene] = []
    for chapter in chapters:
        for part in chapter.parts:
            scenes.extend(_split_part(chapter, part))
    return scenes


def _split_part(chapter: Chapter, part: ChapterPart) -> list[Scene]:
    lines = part.text.splitlines()
    segments: list[tuple[int, int, str]] = []
    current: list[str] = []
    start = part.start_line

    for offset, line in enumerate(lines):
        if SEPARATOR_RE.match(line.strip()):
            if current:
                segments.append(
                    (start, part.start_line + offset - 1, "\n".join(current))
                )
                current = []
            start = part.start_line + offset + 1
        else:
            if not current:
                start = part.start_line + offset
            current.append(line)

    if current:
        segments.append(
            (start, part.start_line + len(lines) - 1, "\n".join(current))
        )
    if not segments:
        segments = [(part.start_line, part.end_line, part.text)]

    scenes: list[Scene] = []
    for index, (seg_start, seg_end, text) in enumerate(segments):
        body = text.strip("\n")
        if not body.strip():
            continue
        scenes.append(
            Scene(
                id=f"v{chapter.volume_index:02d}c{chapter.index:02d}"
                f"p{part.part or '0'}s{index:02d}",
                volume_index=chapter.volume_index,
                chapter_index=chapter.index,
                part=part.part,
                scene_index=index,
                start_line=seg_start,
                end_line=seg_end,
                text=body,
            )
        )
    return scenes
