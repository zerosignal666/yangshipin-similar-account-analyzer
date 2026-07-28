"""统计分析 —— 单快照分析 + 双快照对比 + 趋势回归"""
import pandas as pd
import numpy as np
from datetime import datetime


def to_dataframe(data: list[dict]) -> pd.DataFrame:
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    for col in ["fans_raw", "fans_base", "play_raw", "play_base", "video_cnt"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def compute_stats(df: pd.DataFrame) -> dict:
    if df.empty: return {}
    return {
        "total": len(df),
        "fans": {"sum": float(df["fans_base"].sum()), "mean": float(df["fans_base"].mean()),
                 "median": float(df["fans_base"].median()), "max": float(df["fans_base"].max()),
                 "min": float(df["fans_base"].min()), "std": float(df["fans_base"].std())},
        "plays": {"sum": float(df["play_base"].sum()), "mean": float(df["play_base"].mean()),
                  "median": float(df["play_base"].median()), "max": float(df["play_base"].max()),
                  "min": float(df["play_base"].min()), "std": float(df["play_base"].std())},
        "videos": {"sum": int(df["video_cnt"].sum()), "mean": float(df["video_cnt"].mean()),
                   "median": float(df["video_cnt"].median()), "max": int(df["video_cnt"].max()),
                   "min": int(df["video_cnt"].min()), "std": float(df["video_cnt"].std())},
    }


def top_n(df: pd.DataFrame, col: str = "fans_base", n: int = 10) -> pd.DataFrame:
    if df.empty: return df
    return df.nlargest(n, col)[["name", col, "fans_unit", "play_base", "play_unit", "video_cnt"]]


def compare_snapshots(data_a: list, data_b: list, name_a="A", name_b="B") -> dict:
    df_a = to_dataframe(data_a).set_index("cp_id")
    df_b = to_dataframe(data_b).set_index("cp_id")
    if df_a.empty and df_b.empty: return {}

    cmp = pd.DataFrame(index=df_b.index.union(df_a.index))
    cmp["name"] = df_b["name"].combine_first(df_a["name"])
    # Preserve unit info for interval calculation
    for src, label in [(df_a, name_a), (df_b, name_b)]:
        for col in ["fans_unit", "play_unit"]:
            if col in src.columns:
                cmp[f"{col}_{label}"] = src[col]
    for col, label in [("fans_base", "fans"), ("play_base", "play"), ("video_cnt", "video")]:
        cmp[f"{label}_{name_a}"] = df_a[col]
        cmp[f"{label}_{name_b}"] = df_b[col]
        cmp[f"{label}_chg"] = cmp[f"{label}_{name_b}"] - cmp[f"{label}_{name_a}"]
        cmp[f"{label}_rate"] = np.where(
            cmp[f"{label}_{name_a}"] > 0,
            cmp[f"{label}_chg"] / cmp[f"{label}_{name_a}"] * 100, np.nan)

    new = [{"cp_id": c, "name": df_b.loc[c, "name"]} for c in df_b.index.difference(df_a.index)]
    gone = [{"cp_id": c, "name": df_a.loc[c, "name"]} for c in df_a.index.difference(df_b.index)]

    # 播放量增长 / 新发视频数 (视频增长>0时才有效)
    cmp["play_per_video"] = np.where(cmp["video_chg"] > 0,
                                     cmp["play_chg"] / cmp["video_chg"], np.nan)

    fans_growth = cmp.nlargest(20, "fans_chg")[["name", "fans_chg", "fans_rate"]].dropna(subset=["fans_chg"]).to_dict("records")
    play_growth = cmp.nlargest(20, "play_chg")[["name", "play_chg", "play_rate"]].dropna(subset=["play_chg"]).to_dict("records")
    video_growth = cmp.nlargest(20, "video_chg")[["name", "video_chg"]].dropna(subset=["video_chg"]).to_dict("records")
    ppv_growth = cmp.nlargest(20, "play_per_video")[["name", "play_chg", "video_chg", "play_per_video"]].dropna(subset=["play_per_video"]).to_dict("records")

    summary = {
        f"fans_{name_a}": float(df_a["fans_base"].sum()) if not df_a.empty else 0,
        f"fans_{name_b}": float(df_b["fans_base"].sum()) if not df_b.empty else 0,
        f"play_{name_a}": float(df_a["play_base"].sum()) if not df_a.empty else 0,
        f"play_{name_b}": float(df_b["play_base"].sum()) if not df_b.empty else 0,
        f"video_{name_a}": int(df_a["video_cnt"].sum()) if not df_a.empty else 0,
        f"video_{name_b}": int(df_b["video_cnt"].sum()) if not df_b.empty else 0,
        "fans_chg": float(cmp["fans_chg"].sum()),
        "play_chg": float(cmp["play_chg"].sum()),
        "video_chg": int(cmp["video_chg"].sum()),
        "acct_chg": len(new) - len(gone),
    }
    return {"new": new, "gone": gone, "fans_growth": fans_growth,
            "play_growth": play_growth, "video_growth": video_growth,
            "ppv_growth": ppv_growth, "summary": summary, "all": cmp.to_dict("records")}


# ── 量化误差与趋势分析 ──────────────────────────

QUANTIZATION_HALF = {"万": 500, "亿": 5000, "个": 0, "": 0}


def _quant_half(unit):
    """给定显示单位，返回量化误差半宽（±值）"""
    return QUANTIZATION_HALF.get(unit, 0)


def change_interval(val_a, unit_a, val_b, unit_b):
    """计算变化量的置信区间 [low, high]，考虑显示量化误差。

    返回: (change, low, high, confidence)
      confidence: "confirmed" | "uncertain"
    """
    chg = val_b - val_a
    # 两个独立量化误差求和
    margin = _quant_half(unit_a) + _quant_half(unit_b)
    low = chg - margin
    high = chg + margin
    if low > 0 or high < 0:
        confidence = "confirmed"
    else:
        confidence = "uncertain"
    return chg, low, high, confidence


def theil_sen_slope(timestamps, values):
    """Theil-Sen 稳健回归：所有两点间斜率的中位数。

    timestamps: float 或 datetime（按秒计的时间戳列表）
    values: 粉丝数列表（base unit）
    """
    if len(timestamps) < 2:
        return None, None, None
    ts = np.asarray(timestamps, dtype=float)
    vs = np.asarray(values, dtype=float)
    n = len(ts)
    slopes = []
    for i in range(n):
        for j in range(i + 1, n):
            if ts[j] != ts[i]:
                slopes.append((vs[j] - vs[i]) / (ts[j] - ts[i]))
    if not slopes:
        return None, None, None
    robust_slope = np.median(slopes)
    # OLS slope for comparison
    A = np.vstack([ts, np.ones(n)]).T
    ols_slope, intercept = np.linalg.lstsq(A, vs, rcond=None)[0]
    return robust_slope, ols_slope, intercept


def detect_spikes(timestamps, values, robust_slope, intercept=None):
    """检测偏离稳健趋势线的异常点（疑似病毒传播）。

    返回: [(index, timestamp, value, deviation), ...]
    按偏差绝对值降序排列。
    """
    if robust_slope is None:
        return []
    ts = np.asarray(timestamps, dtype=float)
    vs = np.asarray(values, dtype=float)
    if intercept is None:
        intercept = np.median(vs) - robust_slope * np.median(ts)
    # 预测值 (Theil-Sen 回归线)
    predicted = robust_slope * ts + intercept
    deviations = vs - predicted
    sigma = np.std(deviations)
    if sigma < 1e-9:
        return []
    spike_indices = np.where(np.abs(deviations) > 2 * sigma)[0]
    spikes = []
    for i in spike_indices:
        spikes.append((int(i), float(ts[i]), float(vs[i]), float(deviations[i])))
    spikes.sort(key=lambda x: abs(x[3]), reverse=True)
    return spikes
