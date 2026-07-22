"""统计分析 —— 单快照分析 + 双快照对比"""
import pandas as pd
import numpy as np


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
    for col, label in [("fans_base", "fans"), ("play_base", "play"), ("video_cnt", "video")]:
        cmp[f"{label}_{name_a}"] = df_a[col]
        cmp[f"{label}_{name_b}"] = df_b[col]
        cmp[f"{label}_chg"] = cmp[f"{label}_{name_b}"] - cmp[f"{label}_{name_a}"]
        cmp[f"{label}_rate"] = np.where(
            cmp[f"{label}_{name_a}"] > 0,
            cmp[f"{label}_chg"] / cmp[f"{label}_{name_a}"] * 100, np.nan)

    new = [{"cp_id": c, "name": df_b.loc[c, "name"]} for c in df_b.index.difference(df_a.index)]
    gone = [{"cp_id": c, "name": df_a.loc[c, "name"]} for c in df_a.index.difference(df_b.index)]

    fans_growth = cmp.nlargest(20, "fans_chg")[["name", "fans_chg", "fans_rate"]].dropna(subset=["fans_chg"]).to_dict("records")
    play_growth = cmp.nlargest(20, "play_chg")[["name", "play_chg", "play_rate"]].dropna(subset=["play_chg"]).to_dict("records")
    video_growth = cmp.nlargest(20, "video_chg")[["name", "video_chg"]].dropna(subset=["video_chg"]).to_dict("records")

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
            "play_growth": play_growth, "video_growth": video_growth, "summary": summary}
