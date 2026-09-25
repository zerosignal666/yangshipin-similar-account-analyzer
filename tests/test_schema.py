"""单位归一化与显示换算测试。"""

import pytest

from src.models.schema import auto_unit, format_value, normalize_value


@pytest.mark.parametrize(
    ("raw", "unit", "expected"),
    [(12, "", 12), (12, "个", 12), (1.2, "万", 12_000), (0.5, "亿", 50_000_000)],
)
def test_normalize_value(raw, unit, expected):
    assert normalize_value(raw, unit) == expected


def test_format_value_and_auto_unit_boundaries():
    assert format_value(25_000, "万") == (2.5, "万")
    assert auto_unit(9_999) == (9_999, "个")
    assert auto_unit(10_000) == (1, "万")
    assert auto_unit(100_000_000) == (1, "亿")
    assert format_value(0, "亿") == (0.0, "个")
