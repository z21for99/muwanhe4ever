from __future__ import annotations

from .schemas import Character

NARRATOR_ID = "baifengyuan"
MUWANHE_ID = "muwanhe"
FATHER_ID = "father"

DEFAULT_CHARACTERS = [
    Character(
        id=NARRATOR_ID,
        name="白风远",
        aliases=["白风远", "风远", "我"],
        is_narrator=True,
    ),
    Character(
        id=MUWANHE_ID,
        name="沐婉荷",
        aliases=["沐婉荷", "婉荷", "母亲", "妈妈"],
        is_narrator=False,
    ),
    Character(
        id=FATHER_ID,
        name="父亲",
        aliases=["父亲", "爸爸", "爸", "老白"],
        is_narrator=False,
    ),
]


def character_by_alias(characters: list[Character], name: str) -> Character | None:
    for character in characters:
        if name == character.name or name in character.aliases:
            return character
    return None
