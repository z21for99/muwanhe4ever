from pathlib import Path

from muwanhe.config import Settings


def test_settings_from_args():
    s = Settings.from_args("book.txt", "out.db")
    assert s.source_path == Path("book.txt")
    assert s.db_path == Path("out.db")
    assert s.encoding == "utf-8"
