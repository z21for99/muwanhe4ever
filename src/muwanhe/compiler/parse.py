from __future__ import annotations

from pathlib import Path

from ..schemas import Chapter, ChapterPart, ParseResult, Volume
from .headings import parse_heading


def parse_file(
    path: Path,
    encoding: str = "utf-8",
    volume_order: list[str] | None = None,
) -> ParseResult:
    with path.open("r", encoding=encoding, newline="") as handle:
        text = handle.read()
    lines = text.splitlines()

    volumes: list[Volume] = []
    chapters: list[Chapter] = []
    anomalies: list[str] = []

    current_volume: Volume | None = None
    current_chapter: Chapter | None = None
    part_start: int | None = None
    part_title = ""
    part_name: str | None = None
    part_lines: list[str] = []

    def flush_part(end_line: int) -> None:
        nonlocal part_start, part_title, part_name, part_lines
        if current_chapter is None or part_start is None:
            part_lines = []
            return
        body = "\n".join(part_lines).strip("\n")
        current_chapter.parts.append(
            ChapterPart(
                part=part_name,
                title=part_title,
                start_line=part_start,
                end_line=max(part_start, end_line),
                text=body,
            )
        )
        part_start = None
        part_title = ""
        part_name = None
        part_lines = []

    for line_no, raw in enumerate(lines, start=1):
        heading = parse_heading(raw, line_no)
        if heading is None:
            if part_start is not None:
                part_lines.append(raw)
            continue

        if heading.kind == "volume":
            flush_part(line_no - 1)
            current_chapter = None
            volume = Volume(
                index=heading.index or 0,
                source_index=heading.index or 0,
                title=heading.title,
                start_line=line_no,
            )
            if any(v.index == volume.index for v in volumes):
                anomalies.append(
                    f"duplicate volume index {volume.index} at line {line_no}"
                )
            volumes.append(volume)
            current_volume = volume
            continue

        if heading.kind == "chapter":
            flush_part(line_no - 1)
            if current_volume is None:
                anomalies.append(f"chapter before volume at line {line_no}")
                current_volume = Volume(
                    index=0,
                    source_index=0,
                    title="(untitled)",
                    start_line=line_no,
                )
                volumes.append(current_volume)

            chapter_index = heading.index or 0
            if current_chapter is None or current_chapter.index != chapter_index:
                current_chapter = Chapter(
                    index=chapter_index,
                    title=heading.title,
                    volume_index=current_volume.index,
                )
                chapters.append(current_chapter)
            elif heading.title and not current_chapter.title:
                current_chapter.title = heading.title

            part_start = line_no + 1
            part_title = heading.title
            part_name = heading.part
            part_lines = []
            continue

        # separator: keep it in the part text so the scene splitter sees it
        if part_start is not None:
            part_lines.append(raw)

    flush_part(len(lines))
    _apply_volume_order(volumes, chapters, volume_order, anomalies)

    if not volumes:
        anomalies.append("no volume headings found")
    if not chapters:
        anomalies.append("no chapter headings found")

    return ParseResult(
        source=str(path),
        chars=len(text),
        lines=len(lines),
        volumes=volumes,
        chapters=chapters,
        anomalies=anomalies,
    )


def _apply_volume_order(
    volumes: list[Volume],
    chapters: list[Chapter],
    volume_order: list[str] | None,
    anomalies: list[str],
) -> None:
    if not volume_order:
        return

    if len(set(volume_order)) != len(volume_order):
        anomalies.append(f"volume_order has duplicates: {volume_order}")
        return

    by_title = {volume.title: volume for volume in volumes}
    if len(by_title) != len(volumes) or any(
        title not in by_title for title in volume_order
    ):
        anomalies.append(f"volume_order mismatch: {volume_order}")
        return
    if len(volume_order) != len(volumes):
        anomalies.append(f"volume_order mismatch: {volume_order}")
        return

    ordered = [by_title[title] for title in volume_order]
    mapping = {
        volume.source_index: index
        for index, volume in enumerate(ordered, start=1)
    }

    for volume in volumes:
        volume.index = mapping[volume.source_index]

    for chapter in chapters:
        if chapter.volume_index not in mapping:
            anomalies.append(
                f"chapter volume {chapter.volume_index} missing from volume_order"
            )
            continue
        chapter.volume_index = mapping[chapter.volume_index]

    volumes.sort(key=lambda volume: volume.index)
    chapters.sort(key=lambda chapter: (chapter.volume_index, chapter.index))
