"""学校与全高校爆款监测的区间计算、排名和稳健异常识别测试。"""

from src.analysis.burst import analyze_all_school_bursts, analyze_school_bursts


def _point(day, plays, videos, unit=""):
    return {
        "created_at": f"2026-01-{day:02d}T00:00:00",
        "snapshot_name": f"snapshot-{day}",
        "play_base": plays,
        "play_unit": unit,
        "video_cnt": videos,
    }


def test_marks_efficiency_spike_as_suspected_burst():
    result = analyze_school_bursts([
        _point(1, 0, 0),
        _point(2, 100, 1),
        _point(3, 220, 2),
        _point(4, 310, 3),
        _point(5, 1_310, 4),
    ])
    assert [item["status"] for item in result["intervals"]] == [
        "normal", "normal", "normal", "burst"
    ]
    assert result["summary"]["burst_count"] == 1
    assert result["summary"]["peak_interval"]["play_per_video"] == 1_000
    assert result["baseline"]["median"] == 110


def test_distinguishes_carryover_growth_and_data_correction():
    result = analyze_school_bursts([
        _point(1, 1_000, 10),
        _point(2, 1_300, 10),
        _point(3, 1_200, 9),
    ])
    assert result["intervals"][0]["status"] == "carryover"
    assert result["intervals"][0]["play_per_video"] is None
    assert result["intervals"][1]["status"] == "correction"


def test_sorts_points_and_summarizes_selected_range():
    result = analyze_school_bursts([
        _point(4, 900, 15),
        _point(1, 100, 10),
        _point(2, 300, 12),
    ])
    summary = result["summary"]
    assert summary["snapshot_count"] == 3
    assert summary["interval_count"] == 2
    assert summary["total_play_growth"] == 800
    assert summary["total_video_growth"] == 5
    assert summary["overall_play_per_video"] == 160


def test_returns_empty_analysis_when_range_has_one_snapshot():
    result = analyze_school_bursts([_point(1, 100, 10)])
    assert result["intervals"] == []
    assert result["summary"] == {}


def test_rounding_uncertainty_prevents_false_burst_signal():
    points = [
        _point(1, 0, 0, "万"),
        _point(2, 100, 1, "万"),
        _point(3, 220, 2, "万"),
        _point(4, 310, 3, "万"),
        _point(5, 1_310, 4, "万"),
    ]
    result = analyze_school_bursts(points)
    assert result["intervals"][-1]["play_per_video"] == 1_000
    assert result["intervals"][-1]["play_per_video_low"] == 0
    assert result["intervals"][-1]["is_burst"] is False


def _snapshot(day, accounts):
    return {
        "name": f"snapshot-{day}",
        "created_at": f"2026-01-{day:02d}T00:00:00",
        "accounts": accounts,
    }


def _account(cp_id, name, plays, videos, unit=""):
    return {
        "cp_id": cp_id, "name": name, "play_base": plays,
        "play_unit": unit, "video_cnt": videos,
    }


def test_analyzes_and_ranks_all_schools_in_selected_snapshots():
    snapshots = []
    plays_a = [0, 100, 220, 310, 1_310]
    plays_b = [0, 100, 200, 300, 400]
    for day, (play_a, play_b) in enumerate(zip(plays_a, plays_b), start=1):
        snapshots.append(_snapshot(day, [
            _account("a", "甲大学", play_a, day - 1),
            _account("b", "乙大学", play_b, day - 1),
        ]))

    result = analyze_all_school_bursts(snapshots)
    assert [item["name"] for item in result["schools"]] == ["甲大学", "乙大学"]
    assert result["schools"][0]["assessment"] == "疑似爆款"
    assert result["schools"][0]["burst_count"] == 1
    assert result["summary"]["school_count"] == 2
    assert result["summary"]["suspected_school_count"] == 1


def test_missing_snapshot_interval_is_not_reported_as_burst():
    snapshots = [
        _snapshot(1, [_account("a", "甲大学", 0, 0)]),
        _snapshot(2, []),
        _snapshot(3, [_account("a", "甲大学", 100, 1)]),
        _snapshot(4, [_account("a", "甲大学", 200, 2)]),
        _snapshot(5, [_account("a", "甲大学", 300, 3)]),
        _snapshot(6, [_account("a", "甲大学", 2_000, 4)]),
    ]
    school = analyze_all_school_bursts(snapshots)["schools"][0]
    assert school["coverage"] == 5 / 6
    assert school["analysis"]["intervals"][0]["status"] == "gap"
    assert school["analysis"]["intervals"][0]["is_burst"] is False


def test_uses_real_elapsed_days_for_daily_growth():
    result = analyze_all_school_bursts([
        _snapshot(1, [_account("a", "甲大学", 100, 10)]),
        _snapshot(11, [_account("a", "甲大学", 1_100, 12)]),
    ])
    school = result["schools"][0]
    assert school["daily_play_growth"] == 100
    assert school["analysis"]["intervals"][0]["days"] == 10


def test_user_mad_threshold_changes_burst_filtering():
    points = [
        _point(1, 0, 0),
        _point(2, 100, 1),
        _point(3, 220, 2),
        _point(4, 310, 3),
        _point(5, 610, 4),
    ]
    sensitive = analyze_school_bursts(points, mad_multiplier=3.0)
    strict = analyze_school_bursts(points, mad_multiplier=10.0)
    assert sensitive["summary"]["burst_count"] == 1
    assert strict["summary"]["burst_count"] == 0
    assert strict["baseline"]["threshold"] > sensitive["baseline"]["threshold"]
