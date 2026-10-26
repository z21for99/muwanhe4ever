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
