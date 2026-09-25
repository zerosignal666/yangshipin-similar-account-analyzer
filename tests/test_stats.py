"""快照统计、量化区间与稳健趋势测试。"""

import pytest

from src.analysis.stats import (
    change_interval, compare_snapshots, detect_spikes, theil_sen_slope,
)


def _account(cp_id, name, fans, plays, videos, unit="个"):
    return {
        "cp_id": cp_id,
        "name": name,
        "fans_base": fans,
        "play_base": plays,
        "video_cnt": videos,
        "fans_unit": unit,
        "play_unit": unit,
    }


def test_change_interval_distinguishes_signal_from_rounding_noise():
    assert change_interval(10_000, "万", 10_600, "万") == (600, -400, 1_600, "uncertain")
    assert change_interval(10_000, "万", 12_000, "万") == (2_000, 1_000, 3_000, "confirmed")
    assert change_interval(100_000_000, "亿", 110_000_000, "亿") == (
        10_000_000, 0, 20_000_000, "uncertain"
    )


def test_compare_snapshots_reports_growth_new_and_gone_accounts():
    before = [
        _account("1", "甲大学", 10, 100, 2),
        _account("2", "乙大学", 20, 200, 4),
    ]
    after = [
        _account("1", "甲大学", 15, 160, 3),
        _account("3", "丙大学", 30, 300, 6),
    ]
    result = compare_snapshots(before, after, "before", "after")
    assert result["summary"]["fans_chg"] == 5
    assert result["summary"]["play_chg"] == 60
    assert result["summary"]["video_chg"] == 1
    assert result["summary"]["acct_chg"] == 0
    assert result["new"] == [{"cp_id": "3", "name": "丙大学"}]
    assert result["gone"] == [{"cp_id": "2", "name": "乙大学"}]


def test_compare_snapshots_handles_an_empty_side():
    result = compare_snapshots([], [_account("1", "甲大学", 10, 100, 2)])
    assert result["new"] == [{"cp_id": "1", "name": "甲大学"}]
    assert result["gone"] == []


def test_theil_sen_returns_robust_line_not_ols_intercept():
    timestamps = [0, 1, 2, 3, 4, 5]
    values = [100, 110, 120, 130, 140, 1_000]
    robust, ols, intercept = theil_sen_slope(timestamps, values)
    assert robust == pytest.approx(10)
    assert ols > robust
    assert intercept == pytest.approx(100)


def test_detect_spikes_finds_large_deviation():
    timestamps = list(range(20))
    values = [float(value) for value in timestamps]
    values[10] = 100.0
    spikes = detect_spikes(timestamps, values, robust_slope=1.0, intercept=0.0)
    assert spikes[0][:3] == (10, 10.0, 100.0)
