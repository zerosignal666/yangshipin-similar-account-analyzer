"""学校内容爆发分析 —— 从相邻快照估算播放效率与异常区间。"""

from datetime import datetime

import numpy as np

from .stats import change_interval


def _as_datetime(value) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))


def analyze_school_bursts(
    points: list[dict], expected_snapshot_count: int | None = None,
    mad_multiplier: float = 3.0,
) -> dict:
    ordered = sorted(points, key=lambda item: _as_datetime(item["created_at"]))
    if len(ordered) < 2:
        return {"points": ordered, "intervals": [], "summary": {}, "baseline": {}}

    intervals = []
    for start, end in zip(ordered, ordered[1:]):
        start_at = _as_datetime(start["created_at"])
        end_at = _as_datetime(end["created_at"])
        elapsed_days = max((end_at - start_at).total_seconds() / 86400, 0.0)
        missing_snapshots = max(
            int(end.get("snapshot_index", 0)) - int(start.get("snapshot_index", 0)) - 1,
            0,
        ) if "snapshot_index" in start and "snapshot_index" in end else 0
        play_growth, play_low, play_high, play_confidence = change_interval(
            float(start["play_base"] or 0), start.get("play_unit", ""),
            float(end["play_base"] or 0), end.get("play_unit", ""),
        )
        video_growth = int(end["video_cnt"] or 0) - int(start["video_cnt"] or 0)
        efficiency = play_growth / video_growth if video_growth > 0 and play_growth >= 0 else None
        efficiency_low = max(0.0, play_low) / video_growth if video_growth > 0 else None
        efficiency_high = max(0.0, play_high) / video_growth if video_growth > 0 else None
        daily_play = play_growth / elapsed_days if elapsed_days > 0 else None
        intervals.append({
            "start_at": start_at,
            "end_at": end_at,
            "start_name": start.get("snapshot_name", ""),
            "end_name": end.get("snapshot_name", ""),
            "days": elapsed_days,
            "missing_snapshots": missing_snapshots,
            "play_growth": play_growth,
            "play_growth_low": play_low,
            "play_growth_high": play_high,
            "play_confidence": play_confidence,
            "video_growth": video_growth,
            "play_per_video": efficiency,
            "play_per_video_low": efficiency_low,
            "play_per_video_high": efficiency_high,
            "daily_play_growth": daily_play,
            "is_burst": False,
            "status": "normal",
        })

    efficiencies = np.asarray([
        item["play_per_video"] for item in intervals
        if item["play_per_video"] is not None
        and item["missing_snapshots"] == 0
        and item["days"] > 0
    ], dtype=float)
    median = float(np.median(efficiencies)) if efficiencies.size else None
    mad = float(np.median(np.abs(efficiencies - median))) if efficiencies.size else None
    threshold = None
    if efficiencies.size >= 3:
        spread = 1.4826 * mad
        flat_factor = 1 + 0.8 * mad_multiplier / 3
        threshold = median + mad_multiplier * spread if spread > 0 else max(median * flat_factor, 1.0)

    for item in intervals:
        efficiency = item["play_per_video"]
        if item["play_growth_high"] < 0 or item["video_growth"] < 0:
            item["status"] = "correction"
        elif item["missing_snapshots"] or item["days"] <= 0:
            item["status"] = "gap"
        elif item["video_growth"] == 0 and item["play_growth"] > 0:
            item["status"] = "carryover"
        elif threshold is not None and efficiency is not None and item["play_per_video_low"] > threshold:
            item["status"] = "burst"
            item["is_burst"] = True
        elif item["play_growth"] == 0 and item["video_growth"] == 0:
            item["status"] = "quiet"

    first, last = ordered[0], ordered[-1]
    total_play, total_play_low, total_play_high, total_play_confidence = change_interval(
        float(first["play_base"] or 0), first.get("play_unit", ""),
        float(last["play_base"] or 0), last.get("play_unit", ""),
    )
    total_videos = int(last["video_cnt"] or 0) - int(first["video_cnt"] or 0)
    peak = max(
        (item for item in intervals if item["play_per_video"] is not None),
        key=lambda item: item["play_per_video"], default=None,
    )
    summary = {
        "start_at": _as_datetime(first["created_at"]),
        "end_at": _as_datetime(last["created_at"]),
        "days": max((_as_datetime(last["created_at"]) - _as_datetime(first["created_at"])).total_seconds() / 86400, 0.0),
        "snapshot_count": len(ordered),
        "interval_count": len(intervals),
        "total_play_growth": total_play,
        "total_play_growth_low": total_play_low,
        "total_play_growth_high": total_play_high,
        "total_play_confidence": total_play_confidence,
        "total_video_growth": total_videos,
        "overall_play_per_video": total_play / total_videos if total_videos > 0 else None,
        "daily_play_growth": total_play / max((_as_datetime(last["created_at"]) - _as_datetime(first["created_at"])).total_seconds() / 86400, 1),
        "burst_count": sum(item["is_burst"] for item in intervals),
        "carryover_count": sum(item["status"] == "carryover" for item in intervals),
        "gap_count": sum(item["status"] == "gap" for item in intervals),
        "data_coverage": len(ordered) / max(expected_snapshot_count or len(ordered), 1),
        "peak_interval": peak,
    }
    return {
        "points": ordered,
        "intervals": intervals,
        "summary": summary,
        "baseline": {
            "median": median, "mad": mad, "threshold": threshold,
            "mad_multiplier": mad_multiplier,
        },
    }


def analyze_all_school_bursts(snapshots: list[dict], mad_multiplier: float = 3.0) -> dict:
    ordered = sorted(snapshots, key=lambda item: _as_datetime(item["created_at"]))
    if len(ordered) < 2:
        return {"schools": [], "summary": {"snapshot_count": len(ordered)}}

    histories: dict[str, dict] = {}
    for snapshot_index, snapshot in enumerate(ordered):
        for account in snapshot.get("accounts", snapshot.get("data", [])):
            key = str(account.get("cp_id") or account.get("name", ""))
            if not key: continue
            history = histories.setdefault(key, {"name": account.get("name", key), "points": []})
            history["name"] = account.get("name") or history["name"]
            history["points"].append({
                "snapshot_name": snapshot.get("name", ""),
                "snapshot_index": snapshot_index,
                "created_at": snapshot["created_at"],
                "play_base": account.get("play_base", 0),
                "play_unit": account.get("play_unit", ""),
                "video_cnt": account.get("video_cnt", 0),
            })

    schools = []
    for key, history in histories.items():
        analysis = analyze_school_bursts(history["points"], len(ordered), mad_multiplier)
        summary = analysis["summary"]
        if not summary:
            schools.append({
                "key": key, "name": history["name"], "analysis": analysis,
                "snapshot_count": len(history["points"]), "coverage": len(history["points"]) / len(ordered),
                "burst_count": 0, "signal_score": 0.0, "assessment": "数据不足",
            })
            continue
        bursts = [item for item in analysis["intervals"] if item["is_burst"]]
        strongest = max(bursts, key=lambda item: item["play_per_video_low"], default=None)
        threshold = analysis["baseline"]["threshold"]
        signal_score = (
            strongest["play_per_video_low"] / max(threshold, 1.0)
            if strongest and threshold is not None else 0.0
        )
        if bursts:
            assessment = "疑似爆款"
        elif summary["data_coverage"] < 1 or summary["gap_count"]:
            assessment = "数据有缺口"
        elif threshold is None:
            assessment = "样本不足"
        else:
            assessment = "常规波动"
        schools.append({
            "key": key,
            "name": history["name"],
            "analysis": analysis,
            "snapshot_count": summary["snapshot_count"],
            "coverage": summary["data_coverage"],
            "total_play_growth": summary["total_play_growth"],
            "total_play_growth_low": summary["total_play_growth_low"],
            "total_video_growth": summary["total_video_growth"],
            "overall_play_per_video": summary["overall_play_per_video"],
            "daily_play_growth": summary["daily_play_growth"],
            "burst_count": summary["burst_count"],
            "signal_score": signal_score,
            "strongest_interval": strongest,
            "assessment": assessment,
        })

    schools.sort(key=lambda item: (
        item["burst_count"], item["signal_score"], item.get("daily_play_growth", float("-inf"))
    ), reverse=True)
    analyzable = [item for item in schools if item["snapshot_count"] >= 2]
    suspected = [item for item in schools if item["burst_count"] > 0]
    return {
        "schools": schools,
        "summary": {
            "snapshot_count": len(ordered),
            "school_count": len(schools),
            "analyzable_count": len(analyzable),
            "suspected_school_count": len(suspected),
            "burst_interval_count": sum(item["burst_count"] for item in schools),
            "partial_school_count": sum(item["coverage"] < 1 for item in schools),
            "mad_multiplier": mad_multiplier,
            "start_at": _as_datetime(ordered[0]["created_at"]),
            "end_at": _as_datetime(ordered[-1]["created_at"]),
        },
    }
