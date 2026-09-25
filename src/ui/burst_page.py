"""全高校爆款监测工作区 —— 区间筛选、信号排名与单校下钻。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ..analysis.burst import analyze_all_school_bursts
from ..models.database import get_all_snapshots, get_setting, get_snapshot_data, set_setting
from ..models.schema import auto_unit
from .burst_window import BurstAnalysisWindow
from .theme import palette
from .widgets import Card, MetricCard, PageHeader, SectionTitle, UnitStepper


def _snapshot_label(snapshot: dict) -> str:
    return f"{snapshot['name']} · {snapshot['created_at'][:16]}"


def _compact(value) -> str:
    if value is None: return "—"
    number, unit = auto_unit(abs(value))
    sign = "-" if value < 0 else "+" if value > 0 else ""
    return f"{sign}{number:,.1f}{unit}"


class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        mine = self.data(Qt.ItemDataRole.UserRole)
        theirs = other.data(Qt.ItemDataRole.UserRole)
        if mine is not None and theirs is not None: return mine < theirs
        return super().__lt__(other)


class BurstMonitorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.snapshots = []
        self.result = None
        self._series = []
        self._schools = {}
        self._build()
        self.refresh_snapshots()

    def _build(self):
        self.setObjectName("Page")
        box = QVBoxLayout(self); box.setContentsMargins(28, 24, 28, 28); box.setSpacing(18)
        box.addWidget(PageHeader(
            "05 · PULSE WATCH", "全高校爆款监测",
            "同时扫描账号列表中的全部高校，以发布效率异常定位值得回看的内容爆发时段。",
        ))

        controls = Card(); grid = QGridLayout(); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(10)
        self.combo_start = QComboBox(); self.combo_end = QComboBox()
        self.combo_start.setMinimumWidth(270); self.combo_end.setMinimumWidth(270)
        self.threshold = UnitStepper(
            0.5, 10.0, float(get_setting("burst_mad_multiplier", "3")), 0.5, 1, "倍",
        )
        self.threshold.setToolTip("数值越小越容易进入疑似列表；默认 3.0。")
        self.run_button = QPushButton("扫描全部高校"); self.run_button.setObjectName("BurstButton")
        grid.addWidget(QLabel("起始快照（日期）"), 0, 0); grid.addWidget(self.combo_start, 0, 1)
        grid.addWidget(QLabel("结束快照（日期）"), 0, 2); grid.addWidget(self.combo_end, 0, 3)
        grid.addWidget(QLabel("筛选门槛"), 1, 0); grid.addWidget(self.threshold, 1, 1)
        threshold_note = QLabel("越小越容易发现线索 · 默认 3.0")
        threshold_note.setObjectName("Muted"); grid.addWidget(threshold_note, 1, 2)
        grid.addWidget(self.run_button, 1, 3)
        principle = QLabel(
            "系统会先估算每所学校平时的单条视频播放波动。门槛 3.0 表示只有明显超出常态的区间才会进入疑似列表；调低会发现更多线索，也可能增加误报。"
        )
        principle.setObjectName("InfoCallout"); principle.setWordWrap(True)
        grid.addWidget(principle, 2, 0, 1, 4)
        controls.box.addLayout(grid); box.addWidget(controls)

        metrics = QHBoxLayout(); metrics.setSpacing(12)
        self.school_metric = MetricCard("纳入高校")
        self.suspect_metric = MetricCard("疑似爆款高校")
        self.interval_metric = MetricCard("异常区间")
        self.quality_metric = MetricCard("完整数据")
        for card in [self.school_metric, self.suspect_metric, self.interval_metric, self.quality_metric]:
            metrics.addWidget(card, 1)
        box.addLayout(metrics)

        signal = Card(); signal.box.addWidget(SectionTitle(
            "爆发信号带", "按异常强度展示最值得回看的高校；它是筛查线索，不是具体作品归因。",
        ))
        self.signal_strip = QLabel("选择两个快照后扫描全部高校")
        self.signal_strip.setObjectName("SignalStrip"); self.signal_strip.setWordWrap(True)
        signal.box.addWidget(self.signal_strip); box.addWidget(signal)

        ranking = Card(); head = QHBoxLayout()
        head.addWidget(SectionTitle(
            "全高校排名",
            "双击一行查看该校的全部观察区间；日均播放使用真实间隔天数，覆盖率反映数据缺失。",
        ), 1)
        self.search = QLineEdit(); self.search.setPlaceholderText("筛选学校")
        self.search.setClearButtonEnabled(True); self.search.setMaximumWidth(240)
        self.detail_button = QPushButton("查看学校详情"); self.detail_button.setEnabled(False)
        head.addWidget(self.search); head.addWidget(self.detail_button); ranking.box.addLayout(head)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "排名", "学校", "覆盖率", "播放增长", "新增视频", "单条效率", "日均播放", "异常区间", "判断",
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True); self.table.setMinimumHeight(430)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader(); header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        ranking.box.addWidget(self.table); box.addWidget(ranking)

        self.run_button.clicked.connect(self.analyze)
        self.threshold.valueChanged.connect(self._threshold_changed)
        self.search.textChanged.connect(self._filter_rows)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self._open_detail())
        self.detail_button.clicked.connect(self._open_detail)

    def refresh_snapshots(self):
        start_id = self.combo_start.currentData(); end_id = self.combo_end.currentData()
        self.snapshots = get_all_snapshots(); self.combo_start.clear(); self.combo_end.clear()
        for snapshot in self.snapshots:
            label = _snapshot_label(snapshot)
            self.combo_start.addItem(label, snapshot["id"]); self.combo_end.addItem(label, snapshot["id"])
        if start_id is not None:
            index = self.combo_start.findData(start_id)
            if index >= 0: self.combo_start.setCurrentIndex(index)
        if end_id is not None:
            index = self.combo_end.findData(end_id)
            if index >= 0: self.combo_end.setCurrentIndex(index)
        if len(self.snapshots) >= 2 and start_id is None:
            self.combo_start.setCurrentIndex(len(self.snapshots) - 1)
            self.combo_end.setCurrentIndex(0)

    def analyze(self):
        start = next((item for item in self.snapshots if item["id"] == self.combo_start.currentData()), None)
        end = next((item for item in self.snapshots if item["id"] == self.combo_end.currentData()), None)
        if not start or not end or start["id"] == end["id"]:
            QMessageBox.information(self, "选择区间", "请选择两个不同的快照作为监测区间。")
            return
        start, end = sorted([start, end], key=lambda item: item["created_at"])
        selected = [
            item for item in sorted(self.snapshots, key=lambda item: item["created_at"])
            if start["created_at"] <= item["created_at"] <= end["created_at"]
        ]
        self._series = [{**item, "accounts": get_snapshot_data(item["id"])} for item in selected]
        self._apply_analysis()

    def _apply_analysis(self):
        self.result = analyze_all_school_bursts(self._series, self.threshold.value())
        self._schools = {item["key"]: item for item in self.result["schools"]}
        self._render_summary(); self._populate_table()

    def _threshold_changed(self, value: float):
        set_setting("burst_mad_multiplier", f"{value:g}")
        if self._series: self._apply_analysis()

    def _render_summary(self):
        summary = self.result["summary"]
        complete = summary["school_count"] - summary["partial_school_count"]
        days = max((summary["end_at"] - summary["start_at"]).total_seconds() / 86400, 0)
        self.school_metric.set_data(str(summary["school_count"]), f"{summary['snapshot_count']} 个快照 · {days:.0f} 天")
        self.suspect_metric.set_data(
            str(summary["suspected_school_count"]), f"当前门槛 {summary['mad_multiplier']:.1f} 倍稳健波动",
        )
        self.interval_metric.set_data(str(summary["burst_interval_count"]), "建议回看对应发布时间段")
        self.quality_metric.set_data(str(complete), f"另有 {summary['partial_school_count']} 所存在缺口")
        suspected = [item for item in self.result["schools"] if item["burst_count"]]
        if not suspected:
            self.signal_strip.setText("本区间未发现越过稳健阈值且排除取整误差的爆发信号。")
            return
        c = palette(bool(getattr(self.window(), "is_dark", False)))
        labels = []
        for item in suspected[:6]:
            strongest = item["strongest_interval"]
            labels.append(
                f'<span style="color:{c["warning"]};font-weight:700">● {item["name"]}</span> '
                f'<span style="color:{c["muted"]}">{strongest["start_at"]:%m/%d}–{strongest["end_at"]:%m/%d} · '
                f'{_compact(strongest["play_per_video_low"])}+/条</span>'
            )
        self.signal_strip.setText("&nbsp;&nbsp;&nbsp;&nbsp;".join(labels))

    def _populate_table(self):
        self.table.setSortingEnabled(False); self.table.setRowCount(len(self.result["schools"]))
        c = palette(bool(getattr(self.window(), "is_dark", False)))
        for row, school in enumerate(self.result["schools"]):
            values = [
                (str(row + 1), row + 1),
                (school["name"], school["name"]),
                (f"{school['coverage']:.0%}", school["coverage"]),
                (_compact(school.get("total_play_growth")), school.get("total_play_growth", float("-inf"))),
                (f"{school.get('total_video_growth', 0):+,}", school.get("total_video_growth", 0)),
                (_compact(school.get("overall_play_per_video")), school.get("overall_play_per_video") or float("-inf")),
                (_compact(school.get("daily_play_growth")), school.get("daily_play_growth", float("-inf"))),
                (str(school["burst_count"]), school["burst_count"]),
                (school["assessment"], school["signal_score"]),
            ]
            for column, (text, sort_value) in enumerate(values):
                item = NumericItem(text); item.setData(Qt.ItemDataRole.UserRole, sort_value)
                item.setData(Qt.ItemDataRole.UserRole + 1, school["key"])
                if column != 1: item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if school["burst_count"]: item.setForeground(QColor(c["warning"]))
                elif school["coverage"] < 1: item.setForeground(QColor(c["muted"]))
                self.table.setItem(row, column, item)
        self.table.setSortingEnabled(True); self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        self._filter_rows(); self.detail_button.setEnabled(False)

    def _filter_rows(self):
        query = self.search.text().strip().lower()
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 1).text().lower()
            self.table.setRowHidden(row, bool(query and query not in name))

    def _selection_changed(self):
        self.detail_button.setEnabled(bool(self.table.selectedItems()))

    def _open_detail(self):
        row = self.table.currentRow()
        if row < 0: return
        key = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole + 1)
        school = self._schools.get(key)
        if not school or school["snapshot_count"] < 2:
            QMessageBox.information(self, "数据不足", "该学校在所选区间不足两个有效快照，无法生成详情。")
            return
        BurstAnalysisWindow(self, school["name"], school["analysis"])

    def theme_changed(self):
        if self.result:
            self._render_summary(); self._populate_table()
