import sqlite3

from muwanhe.characters import character_by_alias
from muwanhe.storage.extraction_db import (
    init_extraction_db,
    load_characters,
    seed_characters,
)


def test_seed_and_load():
    conn = sqlite3.connect(":memory:")
    init_extraction_db(conn)
    seed_characters(conn)

    characters = load_characters(conn)

    assert len(characters) == 3
    assert character_by_alias(characters, "妈妈").id == "muwanhe"
    assert character_by_alias(characters, "风远").id == "baifengyuan"
    assert character_by_alias(characters, "父亲").id == "father"
    assert character_by_alias(characters, "陌生人") is None
