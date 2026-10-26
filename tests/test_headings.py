import pytest

from muwanhe.compiler.headings import cn_num_to_int, parse_heading


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("一", 1),
        ("十", 10),
        ("十一", 11),
        ("二十", 20),
        ("一百零二", 102),
        ("1", 1),
        ("10", 10),
    ],
)
def test_cn_num_to_int(raw, expected):
    assert cn_num_to_int(raw) == expected


def test_volume_heading():
    h = parse_heading("第一卷 窃脂篇", 1)
    assert h is not None
    assert h.kind == "volume"
    assert h.index == 1
    assert h.title == "窃脂篇"


def test_chapter_part_heading():
    h = parse_heading("第9章 （1）", 2)
    assert h is not None
    assert h.kind == "chapter"
    assert h.index == 9
    assert h.part == "1"
    assert h.title == ""


def test_chapter_title_and_part_heading():
    h = parse_heading("第10章 （White night）（上）", 3)
    assert h is not None
    assert h.kind == "chapter"
    assert h.index == 10
    assert h.part == "上"


def test_separator_heading():
    h = parse_heading("********************", 4)
    assert h is not None
    assert h.kind == "separator"


def test_plain_text_is_not_heading():
    assert parse_heading("市一中果然不是一般学校。", 5) is None
