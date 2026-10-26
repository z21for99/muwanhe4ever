# Novel Ingestion Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse `花嫁(2).txt` (1,082,507 chars, 4 volumes) into normalized volumes / chapters / parts / scenes, persist them in SQLite, and expose a `muwanhe parse` CLI.

**Architecture:** A pure-Python offline compiler slice. The parser reads UTF-8 text, recognizes volume/chapter headings (including `（1）` / `（上）` parts), groups parts into chapters, splits chapter text on `****` / `——` separators into scenes, writes everything to SQLite, and prints a JSON summary. No LLM or network calls in this plan.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite (stdlib `sqlite3`), pytest, argparse.

---

## Known source facts (2026-10-26)

| item | value |
|---|---|
| file | `花嫁(2).txt` |
| chars | 1,082,507 |
| volumes | 4: 窃脂篇 / 拾棘篇 / 阴雷篇 / 洊雷篇 |
| unique chapters | 31: 10 / 10 / 5 / 6 |
| chapter parts | 35 |
| source order | 窃脂 → 拾棘 → 阴雷 → 洊雷 |
| notes | Volume order differs from the old 3-volume file; `阴雷` may be a flashback. This plan stores file order only; `story_time` comes in a later plan. |

`花嫁(2).txt` is local-only and ignored by `/花嫁*.txt`. Do not commit it.

## File structure

```text
pyproject.toml
src/muwanhe/__init__.py
src/muwanhe/config.py
src/muwanhe/schemas.py
src/muwanhe/compiler/__init__.py
src/muwanhe/compiler/headings.py
src/muwanhe/compiler/parse.py
src/muwanhe/compiler/scenes.py
src/muwanhe/storage/__init__.py
src/muwanhe/storage/db.py
src/muwanhe/cli.py
tests/test_config.py
tests/test_headings.py
tests/test_parse.py
tests/test_scenes.py
tests/test_db.py
tests/test_cli.py
tests/test_real_source.py
```

---

### Task 1: Scaffold package and config

**Files:**
- Create: `pyproject.toml`
- Create: `src/muwanhe/__init__.py`
- Create: `src/muwanhe/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from muwanhe.config import Settings


def test_settings_from_args():
    s = Settings.from_args("book.txt", "out.db")
    assert s.source_path == Path("book.txt")
    assert s.db_path == Path("out.db")
    assert s.encoding == "utf-8"
```

- [ ] **Step 2: Run it to verify it fails**

Run:

```powershell
python -m pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'muwanhe'`.

- [ ] **Step 3: Write minimal implementation**

`pyproject.toml`:

```toml
[project]
name = "muwanhe"
version = "0.1.0"
description = "Local-first character runtime for a long-form novel"
requires-python = ">=3.11"
dependencies = ["pydantic>=2.7"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
```

`src/muwanhe/__init__.py`:

```python
__version__ = "0.1.0"
```

`src/muwanhe/config.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    source_path: Path
    db_path: Path = Path("data/muwanhe.db")
    encoding: str = "utf-8"

    @classmethod
    def from_args(cls, source: str, db: str = "data/muwanhe.db") -> "Settings":
        return cls(source_path=Path(source), db_path=Path(db))
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest tests/test_config.py -v
```

Expected: `1 passed`.

If editable install fails, set `$env:PYTHONPATH="src"` and rerun pytest; the `pythonpath` ini option also covers it.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml src/muwanhe/__init__.py src/muwanhe/config.py tests/test_config.py
git commit -m "chore: scaffold muwanhe package"
```

---

### Task 2: Heading parser

**Files:**
- Create: `src/muwanhe/compiler/__init__.py`
- Create: `src/muwanhe/compiler/headings.py`
- Test: `tests/test_headings.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from muwanhe.compiler.headings import cn_num_to_int, parse_heading


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("一", 1),
        ("十", 10),
        ("十一", 11),
        ("二十", 20),
        ("一百零二", 102),
        ("1", 1),
        ("10", 10),
    ],
)
def test_cn_num_to_int(raw, expected):
    assert cn_num_to_int(raw) == expected


def test_volume_heading():
    h = parse_heading("第一卷 窃脂篇", 1)
    assert h is not None
    assert h.kind == "volume"
    assert h.index == 1
    assert h.title == "窃脂篇"


def test_chapter_part_heading():
    h = parse_heading("第9章 （1）", 2)
    assert h is not None
    assert h.kind == "chapter"
    assert h.index == 9
    assert h.part == "1"
    assert h.title == ""


def test_chapter_title_and_part_heading():
    h = parse_heading("第10章 （White night）（上）", 3)
    assert h is not None
    assert h.kind == "chapter"
    assert h.index == 10
    assert h.part == "上"


def test_separator_heading():
    h = parse_heading("********************", 4)
    assert h is not None
    assert h.kind == "separator"


def test_plain_text_is_not_heading():
    assert parse_heading("市一中果然不是一般学校。", 5) is None
```

- [ ] **Step 2: Run it to verify it fails**

```powershell
python -m pytest tests/test_headings.py -v
```

Expected: `ModuleNotFoundError: No module named 'muwanhe.compiler'`.

- [ ] **Step 3: Write minimal implementation**

`src/muwanhe/compiler/__init__.py`: empty file.

`src/muwanhe/compiler/headings.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass

VOLUME_RE = re.compile(r"^第([一二三四五六七八九十百千零〇0-9]+)卷\s*(.*)$")
CHAPTER_RE = re.compile(r"^第([一二三四五六七八九十百千零〇0-9]+)章\s*(.*)$")
PART_RE = re.compile(r"[（(]\s*([0-9一二三四五六七八九十上中下]+)\s*[）)]\s*$")
SEPARATOR_RE = re.compile(r"^[\*\-—]{4,}$")

CN_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}


@dataclass(frozen=True)
class Heading:
    kind: str
    index: int | None
    title: str
    part: str | None
    line_no: int
    raw: str


def cn_num_to_int(value: str) -> int:
    s = value.strip()
    if s.isdigit():
        return int(s)
    total = 0
    current = 0
    for ch in s:
        if ch in CN_DIGITS:
            current = CN_DIGITS[ch]
        elif ch in CN_UNITS:
            unit = CN_UNITS[ch]
            if current == 0:
                current = 1
            total += current * unit
            current = 0
        else:
            raise ValueError(f"not a Chinese numeral: {value!r}")
    return total + current


def parse_heading(line: str, line_no: int) -> Heading | None:
    text = line.strip()
    if not text:
        return None
    if SEPARATOR_RE.match(text):
        return Heading("separator", None, "", None, line_no, text)

    m = VOLUME_RE.match(text)
    if m:
        return Heading(
            "volume",
            cn_num_to_int(m.group(1)),
            m.group(2).strip(),
            None,
            line_no,
            text,
        )

    m = CHAPTER_RE.match(text)
    if m:
        rest = m.group(2).strip()
        part = None
        pm = PART_RE.search(rest)
        if pm:
            part = pm.group(1)
            rest = rest[: pm.start()].strip()
        return Heading(
            "chapter",
            cn_num_to_int(m.group(1)),
            rest,
            part,
            line_no,
            text,
        )

    return None
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
python -m pytest tests/test_headings.py -v
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```powershell
git add src/muwanhe/compiler/__init__.py src/muwanhe/compiler/headings.py tests/test_headings.py
git commit -m "feat: parse volume and chapter headings"
```

---

### Task 3: Volume / chapter / part parser

**Files:**
- Create: `src/muwanhe/schemas.py`
- Create: `src/muwanhe/compiler/parse.py`
- Test: `tests/test_parse.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from muwanhe.compiler.parse import parse_file

SAMPLE = """第一卷 甲篇
第1章
a1
第2章 （1）
b1
第2章 （2）
b2
第二卷 乙篇
第1章 标题
c1
"""


def test_parse_groups_parts(tmp_path: Path):
    p = tmp_path / "sample.txt"
    p.write_text(SAMPLE, encoding="utf-8")

    result = parse_file(p)

    assert len(result.volumes) == 2
    assert [v.title for v in result.volumes] == ["甲篇", "乙篇"]
    assert len(result.chapters) == 3
    assert [len(c.parts) for c in result.chapters] == [1, 2, 1]
    assert result.chapters[1].parts[0].text == "b1"
    assert result.chapters[1].parts[1].text == "b2"
    assert result.chapters[2].title == "标题"
    assert result.anomalies == []
```

- [ ] **Step 2: Run it to verify it fails**

```powershell
python -m pytest tests/test_parse.py -v
```

Expected: `ModuleNotFoundError: No module named 'muwanhe.schemas'`.

- [ ] **Step 3: Write minimal implementation**

`src/muwanhe/schemas.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class Volume(BaseModel):
    index: int
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
```

`src/muwanhe/compiler/parse.py`:

```python
from __future__ import annotations

from pathlib import Path

from ..schemas import Chapter, ChapterPart, ParseResult, Volume
from .headings import parse_heading


def parse_file(path: Path, encoding: str = "utf-8") -> ParseResult:
    text = path.read_text(encoding=encoding)
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
                current_volume = Volume(index=0, title="(untitled)", start_line=line_no)
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
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
python -m pytest tests/test_parse.py -v
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```powershell
git add src/muwanhe/schemas.py src/muwanhe/compiler/parse.py tests/test_parse.py
git commit -m "feat: group chapter parts from source text"
```

---

### Task 4: Scene splitter

**Files:**
- Create: `src/muwanhe/compiler/scenes.py`
- Test: `tests/test_scenes.py`

- [ ] **Step 1: Write the failing test**

```python
from muwanhe.compiler.scenes import build_scenes
from muwanhe.schemas import Chapter, ChapterPart


def test_split_on_separator():
    part = ChapterPart(
        part=None,
        title="",
        start_line=1,
        end_line=5,
        text="a\n********************\nb\n********************\nc",
    )
    chapter = Chapter(index=1, title="", volume_index=1, parts=[part])

    scenes = build_scenes([chapter])

    assert [s.text for s in scenes] == ["a", "b", "c"]
    assert [s.scene_index for s in scenes] == [0, 1, 2]


def test_no_separator_yields_one_scene():
    part = ChapterPart(
        part=None,
        title="",
        start_line=10,
        end_line=11,
        text="only one block",
    )
    chapter = Chapter(index=2, title="", volume_index=1, parts=[part])

    scenes = build_scenes([chapter])

    assert len(scenes) == 1
    assert scenes[0].text == "only one block"
    assert scenes[0].id == "v01c02p0s00"
```

- [ ] **Step 2: Run it to verify it fails**

```powershell
python -m pytest tests/test_scenes.py -v
```

Expected: `ModuleNotFoundError: No module named 'muwanhe.compiler.scenes'`.

- [ ] **Step 3: Write minimal implementation**

`src/muwanhe/compiler/scenes.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
python -m pytest tests/test_scenes.py -v
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```powershell
git add src/muwanhe/compiler/scenes.py tests/test_scenes.py
git commit -m "feat: split chapters into scenes on separators"
```

---

### Task 5: SQLite store

**Files:**
- Create: `src/muwanhe/storage/__init__.py`
- Create: `src/muwanhe/storage/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

from muwanhe.schemas import Chapter, ChapterPart, ParseResult, Scene, Volume
from muwanhe.storage.db import init_db, save_parse_result, stats


def test_save_and_stats():
    conn = sqlite3.connect(":memory:")
    init_db(conn)

    result = ParseResult(
        source="book.txt",
        chars=10,
        lines=3,
        volumes=[Volume(index=1, title="甲篇", start_line=1)],
        chapters=[
            Chapter(
                index=1,
                title="",
                volume_index=1,
                parts=[
                    ChapterPart(
                        part=None,
                        title="",
                        start_line=2,
                        end_line=2,
                        text="hello",
                    )
                ],
            )
        ],
        scenes=[
            Scene(
                id="v01c01p0s00",
                volume_index=1,
                chapter_index=1,
                part=None,
                scene_index=0,
                start_line=2,
                end_line=2,
                text="hello",
            )
        ],
    )

    run_id = save_parse_result(conn, result)

    assert run_id == 1
    assert stats(conn) == {"volumes": 1, "chapters": 1, "parts": 1, "scenes": 1}
```

- [ ] **Step 2: Run it to verify it fails**

```powershell
python -m pytest tests/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'muwanhe.storage'`.

- [ ] **Step 3: Write minimal implementation**

`src/muwanhe/storage/__init__.py`: empty file.

`src/muwanhe/storage/db.py`:

```python
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ..schemas import ParseResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS parse_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  chars INTEGER NOT NULL,
  lines INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS volumes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  volume_index INTEGER NOT NULL,
  title TEXT NOT NULL,
  start_line INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS chapters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  volume_index INTEGER NOT NULL,
  chapter_index INTEGER NOT NULL,
  title TEXT NOT NULL,
  part TEXT,
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenes (
  id TEXT NOT NULL,
  run_id INTEGER NOT NULL,
  volume_index INTEGER NOT NULL,
  chapter_index INTEGER NOT NULL,
  part TEXT,
  scene_index INTEGER NOT NULL,
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  text TEXT NOT NULL,
  PRIMARY KEY (run_id, id)
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def save_parse_result(conn: sqlite3.Connection, result: ParseResult) -> int:
    cur = conn.execute(
        "INSERT INTO parse_runs (source, chars, lines, created_at) VALUES (?, ?, ?, ?)",
        (
            result.source,
            result.chars,
            result.lines,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    run_id = int(cur.lastrowid)

    for volume in result.volumes:
        conn.execute(
            "INSERT INTO volumes (run_id, volume_index, title, start_line) "
            "VALUES (?, ?, ?, ?)",
            (run_id, volume.index, volume.title, volume.start_line),
        )

    for chapter in result.chapters:
        for part in chapter.parts:
            conn.execute(
                "INSERT INTO chapters "
                "(run_id, volume_index, chapter_index, title, part, start_line, end_line, text) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    chapter.volume_index,
                    chapter.index,
                    part.title or chapter.title,
                    part.part,
                    part.start_line,
                    part.end_line,
                    part.text,
                ),
            )

    for scene in result.scenes:
        conn.execute(
            "INSERT INTO scenes "
            "(id, run_id, volume_index, chapter_index, part, scene_index, "
            "start_line, end_line, text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scene.id,
                run_id,
                scene.volume_index,
                scene.chapter_index,
                scene.part,
                scene.scene_index,
                scene.start_line,
                scene.end_line,
                scene.text,
            ),
        )

    conn.commit()
    return run_id


def stats(conn: sqlite3.Connection) -> dict[str, int]:
    row = conn.execute("SELECT MAX(id) FROM parse_runs").fetchone()
    run_id = row[0] if row else None
    if run_id is None:
        return {"volumes": 0, "chapters": 0, "parts": 0, "scenes": 0}

    volumes = conn.execute(
        "SELECT COUNT(*) FROM volumes WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    chapters = conn.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT DISTINCT volume_index, chapter_index FROM chapters WHERE run_id = ?"
        ")",
        (run_id,),
    ).fetchone()[0]
    parts = conn.execute(
        "SELECT COUNT(*) FROM chapters WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    scenes = conn.execute(
        "SELECT COUNT(*) FROM scenes WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    return {
        "volumes": int(volumes),
        "chapters": int(chapters),
        "parts": int(parts),
        "scenes": int(scenes),
    }
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
python -m pytest tests/test_db.py -v
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```powershell
git add src/muwanhe/storage/__init__.py src/muwanhe/storage/db.py tests/test_db.py
git commit -m "feat: persist parse results in sqlite"
```

---

### Task 6: `muwanhe parse` CLI

**Files:**
- Create: `src/muwanhe/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
import json
import sqlite3
from pathlib import Path

from muwanhe.cli import main


def test_cli_parse(tmp_path: Path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("第一卷 甲篇\n第1章\nhello\n", encoding="utf-8")
    db = tmp_path / "book.db"

    assert main(["parse", "--input", str(source), "--db", str(db)]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["volumes"] == 1
    assert out["chapters"] == 1
    assert out["parts"] == 1
    assert out["scenes"] == 1

    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0] == 1
```

- [ ] **Step 2: Run it to verify it fails**

```powershell
python -m pytest tests/test_cli.py -v
```

Expected: `ModuleNotFoundError: No module named 'muwanhe.cli'`.

- [ ] **Step 3: Write minimal implementation**

`src/muwanhe/cli.py`:

```python
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from .compiler.parse import parse_file
from .compiler.scenes import build_scenes
from .storage.db import init_db, save_parse_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="muwanhe")
    sub = parser.add_subparsers(dest="command", required=True)

    parse = sub.add_parser("parse", help="parse a source text into SQLite")
    parse.add_argument("--input", required=True, help="path to the source .txt")
    parse.add_argument("--db", default="data/muwanhe.db", help="SQLite output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "parse":
        return 1

    result = parse_file(Path(args.input))
    result.scenes = build_scenes(result.chapters)

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        init_db(conn)
        run_id = save_parse_result(conn, result)
    finally:
        conn.close()

    summary = {
        "run_id": run_id,
        "source": result.source,
        "chars": result.chars,
        "lines": result.lines,
        "volumes": len(result.volumes),
        "chapters": len(result.chapters),
        "parts": sum(len(chapter.parts) for chapter in result.chapters),
        "scenes": len(result.scenes),
        "anomalies": result.anomalies,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
python -m pytest tests/test_cli.py -v
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```powershell
git add src/muwanhe/cli.py tests/test_cli.py
git commit -m "feat: add parse CLI"
```

---

### Task 7: Real source verification

**Files:**
- Create: `tests/test_real_source.py`

- [ ] **Step 1: Write the local-only test**

```python
from pathlib import Path

import pytest

from muwanhe.compiler.parse import parse_file

SOURCE = Path("花嫁(2).txt")


@pytest.mark.skipif(not SOURCE.exists(), reason="local source text not present")
def test_real_source_shape():
    result = parse_file(SOURCE)

    assert len(result.volumes) == 4
    assert [v.title for v in result.volumes] == [
        "窃脂篇",
        "拾棘篇",
        "阴雷篇",
        "洊雷篇",
    ]
    assert len(result.chapters) == 31
    assert sum(len(c.parts) for c in result.chapters) == 35
    assert result.chars == 1082507
    assert result.anomalies == []
```

- [ ] **Step 2: Run the local test**

```powershell
python -m pytest tests/test_real_source.py -v
```

Expected on this machine: `1 passed`. On a machine without the source: `1 skipped`.

- [ ] **Step 3: Run the CLI on the real source**

```powershell
python -m muwanhe.cli parse --input "花嫁(2).txt" --db "data/muwanhe.db"
```

Expected JSON fields:

```json
{
  "source": "花嫁(2).txt",
  "chars": 1082507,
  "volumes": 4,
  "chapters": 31,
  "parts": 35,
  "anomalies": []
}
```

The `scenes` value is whatever the separator splitter produces; record it in the handoff notes, not in a committed data file.

- [ ] **Step 4: Commit the local-only test**

```powershell
git add tests/test_real_source.py
git commit -m "test: add local source shape check"
```

If the source test fails, do not adjust the expected numbers blindly: inspect the heading lines first, then update the parser or the expectation with evidence.

---

## Self-review checklist

- [ ] Every task has a failing test first, then implementation, then a passing run.
- [ ] All file paths are exact and match the file-structure section.
- [ ] `Chapter.parts`, `Scene` fields, and SQLite columns use the same names.
- [ ] The parser does not assume file order equals story time; that is a later plan.
- [ ] `花嫁(2).txt` is not committed.
