from pathlib import Path

import pytest

from muwanhe.compiler.parse import parse_file

SOURCE = Path("花嫁(2).txt")


@pytest.mark.skipif(not SOURCE.exists(), reason="local source text not present")
def test_real_source_shape():
    result = parse_file(
        SOURCE,
        volume_order=["阴雷篇", "窃脂篇", "拾棘篇", "洊雷篇"],
    )

    assert len(result.volumes) == 4
    assert [v.title for v in result.volumes] == [
        "阴雷篇",
        "窃脂篇",
        "拾棘篇",
        "洊雷篇",
    ]
    assert [v.source_index for v in result.volumes] == [3, 1, 2, 4]
    assert len(result.chapters) == 31
    assert sum(len(c.parts) for c in result.chapters) == 35
    assert result.chars == 1082507
    assert result.anomalies == []
