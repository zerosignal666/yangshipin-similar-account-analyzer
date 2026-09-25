"""学校爆款证据详情窗口 —— 展示区间播放脉冲、发片量与单条效率。"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QScrollArea,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..analysis.charts import get_cjk_font, setup_font
from ..models.schema import auto_unit
from .chart_windows import attach_bar_hover, style_figure
from .theme import palette
from .widgets import Card, MetricCard, SectionTitle


STATUS_TEXT = {
    "burst": "疑似爆款",
    "carryover": "存量传播",
    "correction": "数据回调",
    "quiet": "无变化",
    "normal": "常规波动",
    "gap": "快照缺口",
}


def _compact(value) -> str:
    if value is None: return "—"
    number, unit = auto_unit(abs(value))
    sign = "-" if value < 0 else ""
    return f"{sign}{number:,.1f}{unit}"


class BurstAnalysisWindow(QDialog):
    def __init__(self, parent, school_name: str, result: dict):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(f"爆款观察 · {school_name}")
        self.resize(1180, 860)
        self.setMinimumSize(920, 680)
        self._result = result
        self._figure = None
        self._build(school_name)
        self.show()

    def _is_dark(self) -> bool:
        parent = self.parent()
        return bool(getattr(parent.window() if parent else None, "is_dark", False))

    def _build(self, school_name: str):
        summary = self._result["summary"]
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); content.setObjectName("Page")
        box = QVBoxLayout(content); box.setContentsMargins(26, 22, 26, 26); box.setSpacing(16)

        eyebrow = QLabel("CONTENT PULSE · 爆款观察"); eyebrow.setObjectName("Eyebrow")
        title = QLabel(school_name); title.setObjectName("PageTitle")
        subtitle = QLabel(
            f"{summary['start_at']:%Y-%m-%d} 至 {summary['end_at']:%Y-%m-%d} · "
            f"{summary['snapshot_count']} 个快照 / {summary['interval_count']} 个观察区间"
        ); subtitle.setObjectName("PageSubtitle")
        box.addWidget(eyebrow); box.addWidget(title); box.addWidget(subtitle)

        metrics = QHBoxLayout(); metrics.setSpacing(10)
        cards = [
            MetricCard("累计播放增长", _compact(summary["total_play_growth"]), f"{summary['days']:.0f} 天区间"),
            MetricCard("新增视频", f"{summary['total_video_growth']:+,}", "区间端点差值"),
            MetricCard("整体单条效率", _compact(summary["overall_play_per_video"]), "播放增长 / 新增视频"),
            MetricCard("疑似爆款区间", str(summary["burst_count"]), f"存量传播 {summary['carryover_count']} 段"),
        ]
        for card in cards: metrics.addWidget(card, 1)
        box.addLayout(metrics)

        callout = QLabel(self._conclusion())
        callout.setObjectName("BurstCallout"); callout.setWordWrap(True)
        box.addWidget(callout)

        chart = Card(); chart.box.addWidget(SectionTitle(
            "内容脉冲", f"上图比较播放增量与新增视频；下图衡量每条新增视频对应的播放增量。当前筛选门槛为平时稳健波动的 {self._result['baseline'].get('mad_multiplier', 3):.1f} 倍；判定已扣除取整误差。"
        ))
        self._figure = self._create_figure()
        canvas = FigureCanvasQTAgg(self._figure); attach_bar_hover(canvas, self)
        canvas.setMinimumHeight(650); canvas.draw()
        chart.box.addWidget(canvas); chart.box.addWidget(NavigationToolbar2QT(canvas, self))
        box.addWidget(chart)

        detail = Card(); detail.box.addWidget(SectionTitle(
            "区间明细", "“存量传播”表示没有新增视频但播放仍增长；快照缺口不参与爆款判定，“数据回调”通常来自平台修正。"
        ))
        table = self._create_table(); detail.box.addWidget(table); box.addWidget(detail)
        scroll.setWidget(content)
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.addWidget(scroll)

    def _conclusion(self) -> str:
        summary = self._result["summary"]
        peak = summary["peak_interval"]
        if summary["burst_count"]:
            bursts = [item for item in self._result["intervals"] if item["is_burst"]]
            strongest = max(bursts, key=lambda item: item["play_per_video"])
            return (
                f"发现 {summary['burst_count']} 个疑似爆款区间。最强信号出现在 "
                f"{strongest['start_at']:%m/%d}–{strongest['end_at']:%m/%d}，"
                f"每条新增视频对应 {_compact(strongest['play_per_video'])} 播放增量。"
                "建议回看该时段发布内容，结合单条作品数据确认。"
            )
        if self._result["baseline"]["threshold"] is None:
            return "有效发片区间不足 3 段，暂不自动判定爆款；图表仍可用于观察播放增长和发布节奏。"
        if peak:
            return (
                f"本区间未出现明显偏离稳健基线的单条效率峰值。最高区间为 "
                f"{peak['start_at']:%m/%d}–{peak['end_at']:%m/%d}，"
                f"每条新增视频对应 {_compact(peak['play_per_video'])} 播放增量。"
            )
        return "所选区间没有可计算的新增视频效率；请检查是否存在至少两个包含该学校的快照。"

    def _create_figure(self):
        setup_font(); fp = get_cjk_font(); c = palette(self._is_dark())
        rows = self._result["intervals"]
        x = np.arange(len(rows)); labels = [f"{r['start_at']:%m/%d}→{r['end_at']:%m/%d}" for r in rows]
        play = [r["play_growth"] for r in rows]; videos = [r["video_growth"] for r in rows]
        colors = [c["warning"] if r["is_burst"] else c["danger"] if r["status"] == "correction" else c["signal"] for r in rows]

        fig, (top, bottom) = plt.subplots(2, 1, figsize=(11, 7.2), dpi=100, gridspec_kw={"height_ratios": [1.15, 1]})
        top.bar(x, play, color=colors, alpha=0.9, label="播放增量")
        top.axhline(0, color=c["line"], linewidth=0.9)
        top.set_ylabel("播放增量", fontproperties=fp)
        top.set_title("播放增长脉冲 × 新增视频节奏", fontsize=12, fontweight="bold", fontproperties=fp)
        top.set_xticks(x); top.set_xticklabels(labels, rotation=32, ha="right", fontsize=8, fontproperties=fp)
        video_axis = top.twinx()
        video_axis.plot(x, videos, color=c["primary"], marker="o", linewidth=2, label="新增视频")
        video_axis.set_ylabel("新增视频", fontproperties=fp, color=c["primary"])
        video_axis.tick_params(axis="y", colors=c["primary"])

        efficiencies = [r["play_per_video"] or 0 for r in rows]
        bottom.bar(x, efficiencies, color=colors, alpha=0.9)
        baseline = self._result["baseline"]
        if baseline["median"] is not None:
            bottom.axhline(baseline["median"], color=c["muted"], linestyle="--", linewidth=1.3, label="常态中位数")
        if baseline["threshold"] is not None:
            bottom.axhline(baseline["threshold"], color=c["warning"], linestyle=":", linewidth=2, label="疑似爆款阈值")
        bottom.set_ylabel("播放增长 / 新增视频", fontproperties=fp)
        bottom.set_title("单条新增视频效率", fontsize=12, fontweight="bold", fontproperties=fp)
        bottom.set_xticks(x); bottom.set_xticklabels(labels, rotation=32, ha="right", fontsize=8, fontproperties=fp)
        if baseline["median"] is not None: bottom.legend(prop=fp, loc="upper left")

        style_figure(fig, self.parent())
        video_axis.set_facecolor("none")
        for spine in video_axis.spines.values(): spine.set_color(c["line"])
        fig.tight_layout(pad=1.5)
        return fig

    def _create_table(self) -> QTableWidget:
        rows = self._result["intervals"]
        table = QTableWidget(len(rows), 6)
        table.setHorizontalHeaderLabels(["观察区间", "天数", "播放增长", "视频增长", "单条效率", "判断"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True); table.setMinimumHeight(min(420, 88 + len(rows) * 36))
        c = palette(self._is_dark())
        for row_index, item in enumerate(rows):
            values = [
                f"{item['start_at']:%Y-%m-%d} → {item['end_at']:%Y-%m-%d}",
                f"{item['days']:.1f}",
                f"{item['play_growth']:+,.0f}",
                f"{item['video_growth']:+,}",
                _compact(item["play_per_video"]),
                STATUS_TEXT[item["status"]],
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column > 0: cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if item["is_burst"]: cell.setForeground(QColor(c["warning"]))
                elif item["status"] == "correction": cell.setForeground(QColor(c["danger"]))
                table.setItem(row_index, column, cell)
        header = table.horizontalHeader(); header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def closeEvent(self, event):
        if self._figure: plt.close(self._figure)
        super().closeEvent(event)
