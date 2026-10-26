from __future__ import annotations

import json
import sqlite3
from collections import Counter

from ..characters import character_by_alias
from ..providers.llm import LLMProvider
from ..schemas import Character
from ..storage.extraction_db import insert_llm_run, load_characters

SYSTEM_PROMPT = """你是中文长篇小说的叙事分析器。只输出 JSON，不要解释。

角色 ID：
- baifengyuan = 白风远（第一人称“我”，叙述者）
- muwanhe = 沐婉荷（母亲，别名：婉荷、妈妈、母亲）
- father = 父亲（别名：爸、爸爸、老白）
- unknown = 无法确定

任务：
1. 把场景按时间、地点、在场人物或话题变化切分为 segments；行号使用输入中的编号。
2. 对列出的低置信度引语判断 speaker 和 addressee，只能使用上述 ID。

规则：
- 只依据输入文本，不要根据“应该是”猜测；
- 证据不足时 speaker/addressee 用 unknown；
- 引语可能来自旁白中的引用、诗词或作者的话，这种情况 speaker 用 unknown；
- 如果说话人是父亲或其他非主要角色，使用 father 或 unknown；绝不能把他们的台词分配给 baifengyuan 或 muwanhe。

输出格式：
{"segments":[{"start":0,"end":5,"summary":"...","location":"...","time":"...","participants":["baifengyuan","muwanhe"]}],
 "attributions":[{"index":0,"speaker":"muwanhe","addressee":"baifengyuan","confidence":0.9}]}
"""


SEGMENTS_SYSTEM_PROMPT = """你是中文长篇小说的叙事分析器。只输出 JSON，不要解释。

任务：把场景按时间、地点、在场人物或话题变化切分为 segments；行号使用输入中的编号。

规则：
- 只依据输入文本，不要根据“应该是”猜测；
- 只输出 segments，不要输出 attributions。

输出格式：
{"segments":[{"start":0,"end":5,"summary":"...","location":"...","time":"...","participants":["baifengyuan","muwanhe"]}]}
"""


def _normalize_id(value: object, characters: list[Character]) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in ("", "unknown", "不确定", "未知", "none", "null", "None"):
        return None
    if text in ("baifengyuan", "muwanhe"):
        return text
    character = character_by_alias(characters, text)
    return character.id if character else None


def _normalize_participants(value: object, characters: list[Character]) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.replace("、", ",").split(",")]
    elif isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = [str(value).strip()]
    result: list[str] = []
    for item in items:
        normalized = _normalize_id(item, characters)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def refine_attributions(
    conn: sqlite3.Connection,
    llm: LLMProvider,
    model: str,
    limit: int | None = None,
    segments_only: bool = False,
) -> dict:
    extraction_run = conn.execute("SELECT MAX(id) FROM extraction_runs").fetchone()[0]
    parse_run = conn.execute("SELECT MAX(id) FROM parse_runs").fetchone()[0]
    if extraction_run is None or parse_run is None:
        return {"error": "missing parse or extraction run"}

    characters = load_characters(conn)
    if segments_only:
        scene_rows = conn.execute(
            "SELECT id, text, volume_index, chapter_index, scene_index "
            "FROM scenes WHERE run_id = ? "
            "ORDER BY volume_index, chapter_index, scene_index LIMIT ?",
            (parse_run, limit if limit is not None else -1),
        ).fetchall()
    else:
        scene_rows = conn.execute(
            "SELECT DISTINCT s.id, s.text, s.volume_index, s.chapter_index, s.scene_index "
            "FROM utterances u "
            "JOIN scenes s ON s.id = u.scene_id AND s.run_id = ? "
            "WHERE u.run_id = ? AND u.method IN ('turn', 'unknown') "
            "ORDER BY s.volume_index, s.chapter_index, s.scene_index "
            "LIMIT ?",
            (parse_run, extraction_run, limit if limit is not None else -1),
        ).fetchall()

    llm_run_id = insert_llm_run(conn, model=model, scene_limit=limit, stats={})
    stats: dict = {
        "llm_run_id": llm_run_id,
        "scenes": 0,
        "offered": 0,
        "updated": 0,
        "segments": 0,
        "by_speaker": {},
        "errors": [],
        "mode": "segments_only" if segments_only else "attribution",
    }
    speakers: Counter[str] = Counter()

    for scene_id, scene_text, _volume, _chapter, _scene in scene_rows:
        stats["scenes"] += 1
        lines = scene_text.splitlines()
        if not lines:
            continue

        if segments_only:
            utterances = []
        else:
            utterances = conn.execute(
                "SELECT id, text, speaker_id, method, confidence, context FROM utterances "
                "WHERE scene_id = ? AND run_id = ? AND method IN ('turn', 'unknown') "
                "ORDER BY quote_start LIMIT 60",
                (scene_id, extraction_run),
            ).fetchall()
            if not utterances:
                continue

        numbered = "\n".join(f"[{index}] {line}" for index, line in enumerate(lines))
        if segments_only:
            user_prompt = (
                f"场景 {scene_id}，共 {len(lines)} 行：\n\n{numbered}\n\n"
                "请输出 segments。"
            )
            system_prompt = SEGMENTS_SYSTEM_PROMPT
        else:
            quote_block = "\n".join(
                f"- q{index}: {row[1].replace(chr(10), ' ')[:120]} | "
                f"当前: {row[3]} -> {row[2] or 'unknown'} | "
                f"上下文: {row[5].replace(chr(10), ' ')[:200]}"
                for index, row in enumerate(utterances)
            )
            user_prompt = (
                f"场景 {scene_id}，共 {len(lines)} 行：\n\n{numbered}\n\n"
                f"低置信度引语：\n{quote_block}\n\n"
                "请输出 segments 和 attributions。"
            )
            system_prompt = SYSTEM_PROMPT

        try:
            response = llm.complete_json(
                system_prompt, user_prompt, max_tokens=6000
            )
        except Exception as exc:  # noqa: BLE001 - keep one bad scene from aborting the run
            stats["errors"].append(f"{scene_id}: {type(exc).__name__}: {exc}")
            continue

        if not isinstance(response, dict):
            stats["errors"].append(f"{scene_id}: response is not an object")
            continue

        stats["offered"] += len(utterances)

        for item in response.get("attributions", []):
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            if not isinstance(index, int) or not 0 <= index < len(utterances):
                continue
            speaker = _normalize_id(item.get("speaker"), characters)
            addressee = _normalize_id(item.get("addressee"), characters)
            try:
                confidence = float(item.get("confidence", 0.8))
            except (TypeError, ValueError):
                confidence = 0.8
            confidence = max(0.0, min(1.0, confidence))
            conn.execute(
                "UPDATE utterances SET speaker_id = ?, addressee_id = ?, "
                "method = 'llm', confidence = ?, is_dialogue = ? WHERE id = ?",
                (
                    speaker,
                    addressee,
                    confidence,
                    int(speaker is not None),
                    utterances[index][0],
                ),
            )
            stats["updated"] += 1
            speakers[speaker or "unknown"] += 1

        for segment_index, segment in enumerate(response.get("segments", [])):
            if not isinstance(segment, dict):
                continue
            start = segment.get("start")
            end = segment.get("end")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or start < 0
                or end < start
                or end >= len(lines)
            ):
                continue
            text = "\n".join(lines[start : end + 1]).strip()
            if not text:
                continue
            participants = _normalize_participants(
                segment.get("participants"), characters
            )
            conn.execute(
                "INSERT OR REPLACE INTO segments "
                "(id, llm_run_id, scene_id, segment_index, start_line, end_line, "
                "text, summary, location, story_time, participants) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"{llm_run_id}:{scene_id}:s{segment_index:02d}",
                    llm_run_id,
                    scene_id,
                    segment_index,
                    start,
                    end,
                    text,
                    str(segment.get("summary", "")),
                    segment.get("location"),
                    segment.get("time"),
                    json.dumps(participants, ensure_ascii=False),
                ),
            )
            stats["segments"] += 1

    stats["by_speaker"] = dict(speakers)
    conn.execute(
        "UPDATE llm_runs SET stats = ? WHERE id = ?",
        (json.dumps(stats, ensure_ascii=False), llm_run_id),
    )
    conn.commit()
    return stats
