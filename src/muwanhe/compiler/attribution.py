from __future__ import annotations

import re
from dataclasses import dataclass

from ..characters import FATHER_ID, MUWANHE_ID, NARRATOR_ID, character_by_alias
from ..schemas import Character
from .dialogue import OPENERS, Quote

CLOSERS = {closer for closer in OPENERS.values()}

NAME_PATTERN = r"(我|她|母亲|妈妈|父亲|爸爸|爸|沐婉荷|婉荷|白风远|风远)"
NAME_RE = re.compile(NAME_PATTERN)
SPEECH_RE = re.compile(
    r"(说|道|问|喊|叫|骂|笑|哭|吼|嘟囔|嘀咕|解释|反问|叹气|"
    r"敷衍|回答|回应|开口|低语|呢喃|插嘴|打断|补充|自语|喃喃)"
)
ADDRESSEE_PAIR_RE = re.compile(
    NAME_PATTERN + r"(?:对|跟|向)" + NAME_PATTERN + r"(?:说|道)"
)
ADDRESSEE_RE = re.compile(r"(?:对|跟|向)" + NAME_PATTERN + r"(?:说|道)")
VOICE_RE = re.compile(
    r"(父亲|母亲|沐婉荷|婉荷|白风远|风远).{0,12}(?:声音|嗓音|语气)"
)


@dataclass(frozen=True)
class Attribution:
    speaker_id: str | None
    addressee_id: str | None
    method: str
    confidence: float


def scene_present(text: str) -> list[str]:
    present = [NARRATOR_ID]
    if any(alias in text for alias in ("沐婉荷", "婉荷", "母亲", "妈妈")):
        present.append(MUWANHE_ID)
    if any(alias in text for alias in ("父亲", "爸")):
        present.append(FATHER_ID)
    return present


def _resolve(name: str | None, characters: list[Character]) -> str | None:
    if not name:
        return None
    if name == "我":
        return NARRATOR_ID
    if name == "她":
        return MUWANHE_ID
    if name in ("母亲", "妈妈"):
        return MUWANHE_ID
    if name in ("父亲", "爸爸", "爸"):
        return FATHER_ID
    character = character_by_alias(characters, name)
    return character.id if character else None


def _local_before(text: str, start: int, limit: int = 60) -> str:
    segment = text[max(0, start - limit) : start]
    last = max((segment.rfind(closer) for closer in CLOSERS), default=-1)
    return segment[last + 1 :] if last != -1 else segment


def _local_after(text: str, end: int, limit: int = 30) -> str:
    window = text[end : end + limit]
    cut = len(window)
    for opener in OPENERS:
        position = window.find(opener)
        if position != -1:
            cut = min(cut, position)
    return window[:cut]


def _cue_name(text: str, last: bool = True) -> str | None:
    matches = list(NAME_RE.finditer(text))
    if not matches:
        return None
    candidates = reversed(matches) if last else matches
    for match in candidates:
        prefix = text[max(0, match.start() - 1) : match.start()]
        if prefix and prefix in "和跟对向被让给":
            continue
        tail = text[match.end() : match.end() + 8]
        if SPEECH_RE.search(tail):
            return match.group(1)
    return None


def _voice_name(text: str) -> str | None:
    match = VOICE_RE.search(text)
    return match.group(1) if match else None


def _vocative(text: str) -> str | None:
    stripped = text.strip()
    if stripped.startswith("儿子"):
        return NARRATOR_ID
    if stripped.startswith(("风远", "白风远")):
        return NARRATOR_ID
    if stripped.startswith(("妈", "母亲", "婉荷", "沐婉荷")):
        return MUWANHE_ID
    if stripped.startswith(("爸", "父亲")):
        return FATHER_ID
    return None


def _default_addressee(
    speaker: str | None,
    present: list[str],
    previous_speaker: str | None,
) -> str | None:
    if speaker == FATHER_ID and MUWANHE_ID in present:
        return MUWANHE_ID
    if speaker == NARRATOR_ID and MUWANHE_ID in present:
        return MUWANHE_ID
    if speaker == MUWANHE_ID:
        if previous_speaker in (FATHER_ID, NARRATOR_ID):
            return previous_speaker
        if NARRATOR_ID in present:
            return NARRATOR_ID
    return None


def attribute_quote(
    quote: Quote,
    scene_text: str,
    characters: list[Character],
    previous_speaker: str | None,
    present: list[str],
    active_pair: tuple[str, str] | None = None,
) -> Attribution:
    before = _local_before(scene_text, quote.start)
    after = _local_after(scene_text, quote.end)

    voice = _voice_name(before) or _voice_name(after)
    if voice:
        speaker = _resolve(voice, characters)
        addressee = _default_addressee(speaker, present, previous_speaker)
        return Attribution(speaker, addressee, "voice", 0.85 if speaker else 0.0)

    pair = ADDRESSEE_PAIR_RE.search(before)
    if pair:
        speaker = _resolve(pair.group(1), characters)
        addressee = _resolve(pair.group(2), characters)
        return Attribution(speaker, addressee, "cue", 0.9 if speaker else 0.0)

    name = _cue_name(before) or _cue_name(after, last=False)
    if name:
        speaker = _resolve(name, characters)
        addressee = None
        addressee_match = ADDRESSEE_RE.search(before)
        if addressee_match:
            addressee = _resolve(addressee_match.group(1), characters)
        if addressee is None:
            addressee = _default_addressee(speaker, present, previous_speaker)
        return Attribution(speaker, addressee, "cue", 0.9 if speaker else 0.0)

    vocative = _vocative(quote.text)
    if vocative:
        if vocative == NARRATOR_ID:
            speaker = (
                MUWANHE_ID
                if MUWANHE_ID in present
                else FATHER_ID if FATHER_ID in present else None
            )
        elif vocative == MUWANHE_ID:
            speaker = NARRATOR_ID if NARRATOR_ID in present else None
        else:
            speaker = (
                NARRATOR_ID
                if NARRATOR_ID in present
                else MUWANHE_ID if MUWANHE_ID in present else None
            )
        return Attribution(
            speaker,
            vocative,
            "vocative",
            0.7 if speaker else 0.0,
        )

    if previous_speaker and active_pair and previous_speaker in active_pair:
        speaker = (
            active_pair[1]
            if previous_speaker == active_pair[0]
            else active_pair[0]
        )
        method = "turn"
        confidence = 0.55
    elif previous_speaker and len(present) >= 2:
        speaker = next(
            (item for item in present if item != previous_speaker), None
        )
        method = "turn"
        confidence = 0.4 if speaker else 0.0
    else:
        speaker = None
        method = "unknown"
        confidence = 0.0

    addressee = _default_addressee(speaker, present, previous_speaker)
    if addressee == speaker:
        addressee = None
    return Attribution(speaker, addressee, method, confidence)
