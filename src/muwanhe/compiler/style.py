from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict

from ..characters import FATHER_ID, NARRATOR_ID
from .attribution import _local_after, _local_before

ANGER_WORDS = (
    "滚",
    "闭嘴",
    "凭什么",
    "烦",
    "恨",
    "吼",
    "骂",
    "生气",
    "不要脸",
    "混蛋",
)
SAD_WORDS = ("哭", "委屈", "对不起", "求", "怕", "难受", "疼", "命苦")
TENDER_WORDS = (
    "吃",
    "睡",
    "冷",
    "伞",
    "衣服",
    "回来",
    "慢点",
    "小心",
    "别累",
    "早点",
    "饭",
)
AWKWARD_WORDS = ("不好意思", "犹豫", "沉默", "低声", "没事", "不用", "算了")
EXPLAIN_WORDS = ("因为", "所以", "不是", "只是", "其实")

EXPLICIT_NAMES = ("母亲", "妈妈", "沐婉荷", "婉荷")
EXPLICIT_VERBS = (
    "说",
    "道",
    "问",
    "喊",
    "叫",
    "骂",
    "笑",
    "哭",
    "吼",
    "回答",
    "解释",
    "低声",
)
VOICE_NAMES = ("母亲", "沐婉荷", "婉荷")
NEGATIVE_ADDRESS_MARKERS = ("沐总", "沐姐", "婉荷姐")


def _match(text: str, words: tuple[str, ...]) -> list[str]:
    return [word for word in words if word in text]


def tag_utterance(text: str, addressee_id: str | None) -> dict:
    if addressee_id == NARRATOR_ID:
        scene_type = "对儿子"
        power = "长辈"
    elif addressee_id == FATHER_ID:
        scene_type = "对丈夫"
        power = "平辈"
    else:
        scene_type = "对他人"
        power = "未知"

    anger = _match(text, ANGER_WORDS)
    sad = _match(text, SAD_WORDS)
    tender = _match(text, TENDER_WORDS)
    awkward = _match(text, AWKWARD_WORDS)
    explain = _match(text, EXPLAIN_WORDS)

    if anger:
        emotion = "anger"
    elif sad:
        emotion = "sad"
    elif tender:
        emotion = "tender"
    elif awkward:
        emotion = "awkward"
    else:
        emotion = "neutral"

    if any(word in text for word in ("滚", "不用", "不要", "别管")):
        intent = "拒绝"
    elif any(word in text for word in ("求", "帮", "救")):
        intent = "求助"
    elif tender:
        intent = "关心"
    elif awkward:
        intent = "掩饰"
    elif explain:
        intent = "解释"
    else:
        intent = "日常"

    markedness = (
        "special"
        if len(text) <= 12 or any(mark in text for mark in ("！", "？", "…"))
        else "normal"
    )
    tags = anger + sad + tender + awkward + explain
    return {
        "scene_type": scene_type,
        "emotion": emotion,
        "intent": intent,
        "power": power,
        "markedness": markedness,
        "tags": tags,
    }


def _has_negative_address(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith(("妈，", "妈。", "妈？", "妈！")):
        return True
    return any(marker in stripped for marker in NEGATIVE_ADDRESS_MARKERS)


def _is_explicit_cue(
    before: str,
    after: str,
    voice_before: str,
    voice_after: str,
) -> bool:
    window = before + after
    if any(
        name + verb in window
        for name in EXPLICIT_NAMES
        for verb in EXPLICIT_VERBS
    ):
        return True

    voice_window = voice_before + voice_after
    return any(
        re.search(name + r".{0,6}(?:声音|嗓音|语气)", voice_window)
        for name in VOICE_NAMES
    )


def build_style_bank(
    conn: sqlite3.Connection,
    min_samples: int = 3,
    precision: bool = True,
    window: int = 8,
) -> dict:
    row = conn.execute("SELECT MAX(id) FROM extraction_runs").fetchone()
    extraction_run = row[0] if row else None
    if extraction_run is None:
        return {
            "extraction_run": None,
            "muwanhe_utterances": 0,
            "modes": 0,
            "samples": 0,
            "precision": precision,
        }

    if precision:
        sql = (
            "SELECT u.id, u.text, u.context, u.addressee_id, "
            "u.quote_start, u.quote_end, s.text "
            "FROM utterances u "
            "JOIN scenes s ON s.id = u.scene_id "
            "AND s.run_id = (SELECT MAX(id) FROM parse_runs) "
            "WHERE u.run_id = ? AND u.speaker_id = 'muwanhe'"
        )
        raw_rows = conn.execute(sql, (extraction_run,)).fetchall()
        rows = []
        for item in raw_rows:
            scene_text = item[6]
            before = _local_before(scene_text, item[4], limit=window)
            after = _local_after(scene_text, item[5], limit=window)
            voice_before = _local_before(
                scene_text, item[4], limit=max(window, 20)
            )
            voice_after = _local_after(
                scene_text, item[5], limit=max(window, 20)
            )
            if _is_explicit_cue(before, after, voice_before, voice_after):
                if _has_negative_address(item[1]):
                    continue
                rows.append(item[:4])
    else:
        sql = (
            "SELECT id, text, context, addressee_id FROM utterances "
            "WHERE run_id = ? AND speaker_id = 'muwanhe' "
            "AND method IN ('cue', 'vocative', 'voice')"
        )
        rows = conn.execute(sql, (extraction_run,)).fetchall()

    groups: dict[tuple[str, str], list[tuple[tuple, dict]]] = defaultdict(list)
    for utterance in rows:
        tags = tag_utterance(utterance[1], utterance[3])
        groups[(tags["scene_type"], tags["emotion"])].append((utterance, tags))

    conn.execute("DELETE FROM style_samples")
    conn.execute("DELETE FROM style_modes")

    modes = 0
    samples = 0
    by_emotion: Counter[str] = Counter()

    for (scene_type, emotion), items in sorted(
        groups.items(), key=lambda pair: -len(pair[1])
    ):
        if len(items) < min_samples:
            continue

        addressees = Counter(item[0][3] for item in items)
        addressee_id = addressees.most_common(1)[0][0]
        intents = Counter(item[1]["intent"] for item in items)
        mode_id = f"mode:{scene_type}:{emotion}"
        description = (
            f"{len(items)} 条样本；典型意图：{intents.most_common(1)[0][0]}"
        )
        conn.execute(
            "INSERT OR REPLACE INTO style_modes "
            "(id, name, addressee_id, scene_type, emotion, description, sample_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                mode_id,
                f"{scene_type}·{emotion}",
                addressee_id,
                scene_type,
                emotion,
                description,
                len(items),
            ),
        )

        selected = sorted(
            items,
            key=lambda item: (
                item[1]["markedness"] != "special",
                abs(len(item[0][1]) - 20),
            ),
        )[:8]
        for utterance, tags in selected:
            conn.execute(
                "INSERT OR REPLACE INTO style_samples "
                "(id, mode_id, utterance_id, text, context, markedness, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    f"sample:{utterance[0]}",
                    mode_id,
                    utterance[0],
                    utterance[1],
                    utterance[2],
                    tags["markedness"],
                    json.dumps(tags, ensure_ascii=False),
                ),
            )
            samples += 1
        modes += 1
        by_emotion[emotion] += len(items)

    conn.commit()
    return {
        "extraction_run": extraction_run,
        "muwanhe_utterances": len(rows),
        "modes": modes,
        "samples": samples,
        "by_emotion": dict(by_emotion),
        "precision": precision,
        "window": window,
    }
