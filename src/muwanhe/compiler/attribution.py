from __future__ import annotations

import re
from dataclasses import dataclass

from ..characters import FATHER_ID, MUWANHE_ID, NARRATOR_ID, character_by_alias
from ..schemas import Character
from .dialogue import Quote

NAME_PATTERN = r"(我|她|他|母亲|妈妈|父亲|爸爸|爸|沐婉荷|婉荷|白风远|风远)"
NAME_RE = re.compile(NAME_PATTERN)
SPEECH_RE = re.compile(
    r"(说|道|问|喊|叫|骂|笑|哭|吼|嘟囔|嘀咕|解释|反问|叹气)"
)
ADDRESSEE_PAIR_RE = re.compile(
    NAME_PATTERN + r"(?:对|跟|向)" + NAME_PATTERN + r"(?:说|道)"
)
ADDRESSEE_RE = re.compile(r"(?:对|跟|向)" + NAME_PATTERN + r"(?:说|道)")


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
    if name == "他":
        return FATHER_ID
    character = character_by_alias(characters, name)
    return character.id if character else None


def _cue_name(text: str, last: bool = True) -> str | None:
    matches = list(NAME_RE.finditer(text))
    if not matches:
        return None
    candidates = reversed(matches) if last else matches
    for match in candidates:
        tail = text[match.end() : match.end() + 8]
        if SPEECH_RE.search(tail):
            return match.group(1)
    return None


def attribute_quote(
    quote: Quote,
    scene_text: str,
    characters: list[Character],
    previous_speaker: str | None,
    present: list[str],
) -> Attribution:
    before = scene_text[max(0, quote.start - 40) : quote.start]
    after = scene_text[quote.end : quote.end + 20]

    pair = ADDRESSEE_PAIR_RE.search(before)
    if pair:
        speaker = _resolve(pair.group(1), characters)
        addressee = _resolve(pair.group(2), characters)
        return Attribution(speaker, addressee, "cue", 0.9 if speaker else 0.0)

    name = _cue_name(before) or _cue_name(after, last=False)
    if name:
        speaker = _resolve(name, characters)
        method = "cue"
        confidence = 0.9 if speaker else 0.0
    elif len(present) >= 2:
        if previous_speaker:
            speaker = next(
                (item for item in present if item != previous_speaker), None
            )
            method = "turn"
            confidence = 0.4 if speaker else 0.0
        else:
            speaker = NARRATOR_ID if NARRATOR_ID in present else None
            method = "default"
            confidence = 0.2 if speaker else 0.0
    else:
        speaker = None
        method = "unknown"
        confidence = 0.0

    addressee = None
    addressee_match = ADDRESSEE_RE.search(before)
    if addressee_match:
        addressee = _resolve(addressee_match.group(1), characters)
    if addressee is None and speaker and len(present) >= 2:
        addressee = next((item for item in present if item != speaker), None)
    if addressee == speaker:
        addressee = None

    return Attribution(speaker, addressee, method, confidence)
