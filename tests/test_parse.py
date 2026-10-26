from pathlib import Path

from muwanhe.compiler.parse import parse_file

SAMPLE = """第一卷 甲篇
第1章
a1
第2章 （1）
b1
第2章 （2）
b2
第二卷 乙篇
第1章 标题
c1
"""

REORDER_SAMPLE = """第一卷 甲篇
第1章
a
第二卷 乙篇
第1章
b
第三卷 丙篇
第1章
c
"""


def test_parse_groups_parts(tmp_path: Path):
    p = tmp_path / "sample.txt"
    p.write_text(SAMPLE, encoding="utf-8")

    result = parse_file(p)

    assert len(result.volumes) == 2
    assert [v.title for v in result.volumes] == ["甲篇", "乙篇"]
    assert len(result.chapters) == 3
    assert [len(c.parts) for c in result.chapters] == [1, 2, 1]
    assert result.chapters[1].parts[0].text == "b1"
    assert result.chapters[1].parts[1].text == "b2"
    assert result.chapters[2].title == "标题"
    assert result.anomalies == []


def test_parse_reorders_volumes(tmp_path: Path):
    p = tmp_path / "reorder.txt"
    p.write_text(REORDER_SAMPLE, encoding="utf-8")

    result = parse_file(p, volume_order=["丙篇", "甲篇", "乙篇"])

    assert [v.title for v in result.volumes] == ["丙篇", "甲篇", "乙篇"]
    assert [v.index for v in result.volumes] == [1, 2, 3]
    assert [v.source_index for v in result.volumes] == [3, 1, 2]
    assert [c.parts[0].text for c in result.chapters] == ["c", "a", "b"]
    assert [c.volume_index for c in result.chapters] == [1, 2, 3]
