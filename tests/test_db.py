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
        volumes=[Volume(index=1, source_index=1, title="甲篇", start_line=1)],
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
