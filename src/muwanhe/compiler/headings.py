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
