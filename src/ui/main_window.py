"""PySide6 主界面 —— 校园数据雷达。"""
import csv
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt, Signal, QStringListModel
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QCompleter, QDialog,
    QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from ..analysis.charts import bar_top_n, get_cjk_font, setup_font
from ..analysis.stats import (
    change_interval, compare_snapshots, compute_stats, to_dataframe,
)
from ..crawler.url_parser import parse_account_file
from ..models.database import (
    can_crawl, delete_snapshot, get_all_snapshots, get_last_crawl_time,
    get_setting, get_snapshot, get_snapshot_data, init_db, rename_snapshot,
    reset_crawl_log, set_setting,
)
from ..models.schema import DISPLAY_UNITS, auto_unit, format_value
from .chart_windows import (
    BarChartWindow, DashboardWindow, HistogramWindow, ScatterWindow, attach_bar_hover,
    style_figure,
)
from .burst_page import BurstMonitorPage
from .theme import apply_theme, palette
from .widgets import Card, MetricCard, PageHeader, SectionTitle, UnitStepper, clear_layout
from .workers import CrawlThread


def _snapshot_label(snapshot: dict) -> str:
    return f"{snapshot['name']} · {snapshot['created_at'][:16]}"


def _format_number(value: float) -> str:
    number, unit = auto_unit(value or 0)
    return f"{number:,.1f}{unit}"


def _primary(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("PrimaryButton")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def _page_layout(widget: QWidget) -> QVBoxLayout:
    widget.setObjectName("Page")
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(28, 24, 28, 28)
    layout.setSpacing(18)
    return layout


def _scroll_page(page: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(page)
    return scroll


class CrawlPage(QWidget):
    crawl_completed = Signal(int)

    def __init__(self):
        super().__init__()
        self._thread = None
        self._accounts = parse_account_file()
        self._paused = False
        box = _page_layout(self)
        box.addWidget(PageHeader(
            "01 · COLLECT", "采集中心", "连接央视频公开页面，按既定频率生成一份新的账号快照。"))

        metrics = QHBoxLayout(); metrics.setSpacing(12)
        self.account_metric = MetricCard("账号队列")
        self.last_metric = MetricCard("最近采集")
        self.limit_metric = MetricCard("频率窗口")
        self.interval_metric = MetricCard("请求间隔")
        for card in [self.account_metric, self.last_metric, self.limit_metric, self.interval_metric]:
            metrics.addWidget(card, 1)
        box.addLayout(metrics)

        signal = Card()
        signal.box.addWidget(SectionTitle("实时采集轨迹", "每个节点代表一段账号队列；青色表示已经完成。"))
        self.track = QLabel(); self.track.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.track.setMinimumHeight(44)
        signal.box.addWidget(self.track)
        self.progress = QProgressBar(); self.progress.setTextVisible(False)
        signal.box.addWidget(self.progress)
        self.progress_text = QLabel("等待开始")
        self.progress_text.setObjectName("Muted")
        signal.box.addWidget(self.progress_text)
        controls = QHBoxLayout()
        self.start_button = _primary("开始采集")
        self.pause_button = QPushButton("暂停")
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("DangerButton")
        self.pause_button.setEnabled(False); self.stop_button.setEnabled(False)
        controls.addWidget(self.start_button); controls.addWidget(self.pause_button)
        controls.addWidget(self.stop_button); controls.addStretch()
        signal.box.addLayout(controls)
        box.addWidget(signal)

        log_card = Card()
        log_card.box.addWidget(SectionTitle("运行记录", "错误会保留在这里，方便定位失败账号。"))
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMinimumHeight(210)
        log_card.box.addWidget(self.log)
        box.addWidget(log_card)
        box.addStretch()

        self.start_button.clicked.connect(self.start)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button.clicked.connect(self.stop)
        self.refresh()
        self._update_track(0, max(len(self._accounts), 1))

    def refresh(self):
        self._accounts = parse_account_file()
        last = get_last_crawl_time()
        days = get_setting("rate_limit_days", "7")
        count = get_setting("rate_limit_count", "2")
        self.account_metric.set_data(str(len(self._accounts)), "已载入账号")
        self.last_metric.set_data(last[:10] if last else "暂无", last[11:19] if last else "尚未生成快照")
        self.limit_metric.set_data(f"{days} 天 / {count} 次", "保护目标站点")
        self.interval_metric.set_data(f"{get_setting('request_interval', '3')} 秒", "单次请求间隔")

    def _append_log(self, message: str, level: str = "info"):
        colors = {"ok": "#2F9D6A", "error": "#D95858", "warn": "#D68B2C", "info": "#69758A"}
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f'<span style="color:{colors.get(level, colors["info"])}">[{stamp}] {message}</span>')

    def _update_track(self, current: int, total: int):
        ratio = current / total if total else 0
        complete = min(7, int(ratio * 7 + 0.001))
        c = palette(bool(getattr(self.window(), "is_dark", False)))
        nodes = []
        for index in range(7):
            color = c["signal"] if index < complete else c["line"]
            nodes.append(f'<span style="font-size:22px;color:{color}">●</span>')
        self.track.setText(f'<span style="color:{c["line"]}">━━</span>'.join(nodes))

    def start(self):
        if not self._accounts:
            QMessageBox.warning(self, "没有账号", "未找到账号列表，请检查“同类账号.txt”。")
            return
        days = int(get_setting("rate_limit_days", "7")); count = int(get_setting("rate_limit_count", "2"))
        allowed, reason = can_crawl(days, count)
        if not allowed:
            answer = QMessageBox.question(self, "频率限制", f"{reason}\n\n仍然开始本次采集？")
            if answer != QMessageBox.StandardButton.Yes: return
        self.log.clear(); self._append_log("开始建立新快照")
        name = f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._thread = CrawlThread(self._accounts, name)
        self._thread.log.connect(self._append_log)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished_crawl.connect(self._on_done)
        self._thread.failed.connect(self._on_failed)
        self.progress.setRange(0, len(self._accounts)); self.progress.setValue(0)
        self.start_button.setEnabled(False); self.pause_button.setEnabled(True); self.stop_button.setEnabled(True)
        self._paused = False; self.pause_button.setText("暂停")
        self._thread.start()

    def _on_progress(self, current: int, total: int, name: str, status: str, message: str):
        self.progress.setRange(0, total); self.progress.setValue(current)
        label = "完成" if status == "ok" else "失败"
        self.progress_text.setText(f"{current} / {total} · {label} · {name}  {message}")
        self._update_track(current, total)

    def _on_done(self, snapshot_id: int, total: int, success: int, failed: int):
        self._append_log(f"采集完成：成功 {success}，失败 {failed}，共 {total}", "ok" if failed == 0 else "warn")
        self.progress_text.setText(f"快照已保存 · 成功 {success} / {total}")
        self._finish_controls(); self.refresh(); self.crawl_completed.emit(snapshot_id)

    def _on_failed(self, message: str):
        self._append_log(message, "error"); self._finish_controls()
        QMessageBox.critical(self, "采集失败", message)

    def _finish_controls(self):
        self.start_button.setEnabled(True); self.pause_button.setEnabled(False); self.stop_button.setEnabled(False)
        self._paused = False; self.pause_button.setText("暂停")

    def toggle_pause(self):
        if not self._thread: return
        if self._paused:
            self._thread.resume(); self.pause_button.setText("暂停"); self._append_log("继续采集")
        else:
            self._thread.pause(); self.pause_button.setText("继续"); self._append_log("已暂停", "warn")
        self._paused = not self._paused

    def stop(self):
        if self._thread:
            self._thread.stop(); self._append_log("正在安全停止…", "warn")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.isRunning())

    def theme_changed(self):
        self._update_track(self.progress.value(), max(self.progress.maximum(), 1))


class SnapshotManagerDialog(QDialog):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理快照"); self.resize(640, 520)
        box = QVBoxLayout(self)
        box.addWidget(SectionTitle("快照管理", "重命名只改变显示名称；删除会同时移除该快照中的账号记录。"))
        self.list = QListWidget(); self.list.currentRowChanged.connect(self._show_detail)
        box.addWidget(self.list, 1)
        self.detail = QLabel(); self.detail.setObjectName("Muted"); self.detail.setWordWrap(True)
        box.addWidget(self.detail)
        actions = QHBoxLayout(); actions.addStretch()
        rename = QPushButton("重命名"); delete = QPushButton("删除"); delete.setObjectName("DangerButton")
        close = QPushButton("关闭")
        actions.addWidget(rename); actions.addWidget(delete); actions.addWidget(close); box.addLayout(actions)
        rename.clicked.connect(self._rename); delete.clicked.connect(self._delete); close.clicked.connect(self.accept)
        self._refresh()

    def _refresh(self):
        self.snapshots = get_all_snapshots(); self.list.clear()
        for snap in self.snapshots:
            self.list.addItem(f"{snap['name']}   ·   {snap['created_at'][:16]}   ·   {snap['success_count']}/{snap['total_count']}")
        if self.snapshots: self.list.setCurrentRow(0)

    def _show_detail(self, row: int):
        if row < 0 or row >= len(self.snapshots): self.detail.clear(); return
        snap = self.snapshots[row]; data = get_snapshot_data(snap["id"])
        leaders = "、".join(item["name"] for item in sorted(data, key=lambda x: x.get("fans_base", 0) or 0, reverse=True)[:5])
        self.detail.setText(
            f"创建于 {snap['created_at'][:19]} · 成功 {snap['success_count']} · 失败 {snap['fail_count']}\n"
            f"粉丝 TOP 5：{leaders or '暂无数据'}")

    def _rename(self):
        row = self.list.currentRow()
        if row < 0: return
        field = QLineEdit(self.snapshots[row]["name"])
        dialog = QDialog(self); dialog.setWindowTitle("重命名快照")
        box = QVBoxLayout(dialog); box.addWidget(QLabel("新的快照名称")); box.addWidget(field)
        save = _primary("保存名称"); box.addWidget(save); save.clicked.connect(dialog.accept)
        if dialog.exec() and field.text().strip():
            rename_snapshot(self.snapshots[row]["id"], field.text().strip())
            self._refresh(); self.changed.emit()

    def _delete(self):
        row = self.list.currentRow()
        if row < 0: return
        snap = self.snapshots[row]
        answer = QMessageBox.question(
            self, "确认删除", f"删除“{snap['name']}”及其中 {snap['total_count']} 条记录？\n此操作无法撤销。")
        if answer == QMessageBox.StandardButton.Yes:
            delete_snapshot(snap["id"]); self._refresh(); self.changed.emit()


class DataPage(QWidget):
    snapshots_changed = Signal()

    def __init__(self):
        super().__init__(); self.snapshots = []; self.data = []; self.visible = []
        self.sort_column = "fans_base"; self.sort_desc = True
        box = _page_layout(self)
        header = QHBoxLayout()
        header.addWidget(PageHeader("02 · SNAPSHOTS", "数据快照", "筛选、排序并导出任意一次采集结果。"), 1)
        manage = QPushButton("管理快照"); export = _primary("导出 CSV")
        header.addWidget(manage); header.addWidget(export); box.addLayout(header)
        tools = Card(); row = QHBoxLayout(); row.setSpacing(10)
        row.addWidget(QLabel("快照")); self.snapshot_combo = QComboBox(); self.snapshot_combo.setMinimumWidth(290)
        row.addWidget(self.snapshot_combo, 1)
        row.addWidget(QLabel("单位")); self.unit_combo = QComboBox(); self.unit_combo.addItems(DISPLAY_UNITS)
        self.unit_combo.setCurrentText(get_setting("display_unit", "万")); row.addWidget(self.unit_combo)
        row.addWidget(QLabel("搜索")); self.search = QLineEdit(); self.search.setPlaceholderText("输入学校名称")
        self.search.setClearButtonEnabled(True); self.search.setMaximumWidth(240); row.addWidget(self.search)
        tools.box.addLayout(row); box.addWidget(tools)
        self.status = QLabel(); self.status.setObjectName("Muted"); box.addWidget(self.status)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["#", "学校", "粉丝", "播放", "视频", "简介"])
        self.table.setAlternatingRowColors(True); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header_view = self.table.horizontalHeader(); header_view.setStretchLastSection(True)
        header_view.resizeSection(0, 48); header_view.resizeSection(1, 180)
        header_view.resizeSection(2, 120); header_view.resizeSection(3, 120); header_view.resizeSection(4, 80)
        self.table.setMinimumHeight(500); box.addWidget(self.table, 1)
        self.snapshot_combo.currentIndexChanged.connect(self._load_snapshot)
        self.unit_combo.currentTextChanged.connect(self._unit_changed)
        self.search.textChanged.connect(self._render)
        header_view.sectionClicked.connect(self._sort)
        manage.clicked.connect(self._manage); export.clicked.connect(self._export)
        self.refresh_snapshots()

    def refresh_snapshots(self, select_id=None):
        current_id = select_id or self.snapshot_combo.currentData()
        self.snapshots = get_all_snapshots(); self.snapshot_combo.blockSignals(True); self.snapshot_combo.clear()
        for snap in self.snapshots: self.snapshot_combo.addItem(_snapshot_label(snap), snap["id"])
        if current_id:
            index = self.snapshot_combo.findData(current_id)
            if index >= 0: self.snapshot_combo.setCurrentIndex(index)
        self.snapshot_combo.blockSignals(False); self._load_snapshot()

    def _load_snapshot(self):
        snapshot_id = self.snapshot_combo.currentData()
        self.data = get_snapshot_data(snapshot_id) if snapshot_id else []
        self._render()

    def _unit_changed(self, unit: str):
        set_setting("display_unit", unit); self._render()

    def _format(self, value):
        if value is None or value == 0: return "—"
        number, unit = format_value(value, self.unit_combo.currentText())
        precision = 0 if number >= 10000 else 1 if number >= 100 else 2 if number >= 1 else 4
        return f"{number:,.{precision}f} {unit}"

    def _render(self):
        query = self.search.text().strip().lower()
        self.visible = [item for item in self.data if not query or query in item.get("name", "").lower()]
        self.table.setSortingEnabled(False); self.table.setRowCount(len(self.visible))
        c = palette(bool(getattr(self.window(), "is_dark", False)))
        for row, item in enumerate(self.visible):
            values = [str(row + 1), item["name"], self._format(item.get("fans_base")),
                      self._format(item.get("play_base")), str(item.get("video_cnt", 0)), item.get("description", "")]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column in [0, 2, 3, 4]: cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if item.get("name") == "武汉科技大学":
                    cell.setForeground(QColor(c["danger"])); font = cell.font(); font.setBold(True); cell.setFont(font)
                self.table.setItem(row, column, cell)
        self.status.setText(f"显示 {len(self.visible)} / {len(self.data)} 条记录")

    def _sort(self, section: int):
        columns = {0: "fans_base", 1: "name", 2: "fans_base", 3: "play_base", 4: "video_cnt"}
        key = columns.get(section)
        if not key: return
        if self.sort_column == key: self.sort_desc = not self.sort_desc
        else: self.sort_column = key; self.sort_desc = key != "name"
        if key == "name": self.data.sort(key=lambda item: item.get(key, "").lower(), reverse=self.sort_desc)
        else: self.data.sort(key=lambda item: item.get(key, 0) or 0, reverse=self.sort_desc)
        self._render()

    def _export(self):
        snapshot_id = self.snapshot_combo.currentData()
        if not snapshot_id: return
        snap = get_snapshot(snapshot_id)
        path, _ = QFileDialog.getSaveFileName(self, "导出快照", f"ysp_{snap['name']}.csv", "CSV (*.csv)")
        if not path: return
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file); writer.writerow(["#", "学校", "粉丝", "播放", "视频", "简介", "CPID"])
            for index, item in enumerate(self.data):
                writer.writerow([index + 1, item["name"], item.get("fans_base"), item.get("play_base"),
                                 item.get("video_cnt"), item.get("description", ""), item.get("cp_id", "")])
        QMessageBox.information(self, "导出完成", f"文件已保存到：\n{path}")

    def _manage(self):
        dialog = SnapshotManagerDialog(self); dialog.changed.connect(self._manager_changed); dialog.exec()

    def _manager_changed(self):
        self.refresh_snapshots(); self.snapshots_changed.emit()


class AnalysisPage(QWidget):
    def __init__(self):
        super().__init__(); self.snapshots = []; self.df = None; self.preview_figure = None
        box = _page_layout(self)
        box.addWidget(PageHeader("03 · EXPLORE", "单次分析", "从一个快照读取分布、排名与账号之间的关系。"))
        controls = Card(); row = QHBoxLayout(); row.setSpacing(10)
        row.addWidget(QLabel("快照")); self.snapshot_combo = QComboBox(); self.snapshot_combo.setMinimumWidth(290); row.addWidget(self.snapshot_combo, 1)
        row.addWidget(QLabel("TOP")); self.top_n = QSpinBox(); self.top_n.setRange(5, 100); self.top_n.setValue(15); row.addWidget(self.top_n)
        row.addWidget(QLabel("重点学校")); self.highlight = QLineEdit("武汉科技大学"); row.addWidget(self.highlight)
        analyze = _primary("生成分析"); row.addWidget(analyze); controls.box.addLayout(row); box.addWidget(controls)
        metrics = QHBoxLayout(); metrics.setSpacing(12)
        self.account_metric = MetricCard("账号数"); self.fans_metric = MetricCard("粉丝总量")
        self.plays_metric = MetricCard("播放总量"); self.videos_metric = MetricCard("视频总量")
        for item in [self.account_metric, self.fans_metric, self.plays_metric, self.videos_metric]: metrics.addWidget(item, 1)
        box.addLayout(metrics)
        chart = Card(); chart.box.addWidget(SectionTitle("排名预览", "默认显示粉丝 TOP；下方按钮打开完整交互图表。"))
        self.preview = QVBoxLayout(); chart.box.addLayout(self.preview)
        actions = QHBoxLayout()
        for text, method in [("粉丝排名", self._fans), ("播放排名", self._plays),
                             ("粉丝分布", self._distribution), ("粉丝 × 播放", self._scatter),
                             ("打开仪表盘", self._dashboard)]:
            button = QPushButton(text); button.clicked.connect(method); actions.addWidget(button)
        actions.addStretch(); chart.box.addLayout(actions); box.addWidget(chart)
        box.addStretch(); analyze.clicked.connect(self.analyze); self.refresh_snapshots()

    def refresh_snapshots(self):
        selected = self.snapshot_combo.currentData(); self.snapshots = get_all_snapshots()
        self.snapshot_combo.clear()
        for snap in self.snapshots: self.snapshot_combo.addItem(_snapshot_label(snap), snap["id"])
        if selected:
            index = self.snapshot_combo.findData(selected)
            if index >= 0: self.snapshot_combo.setCurrentIndex(index)

    def analyze(self):
        snapshot_id = self.snapshot_combo.currentData()
        if not snapshot_id: return
        self.df = to_dataframe(get_snapshot_data(snapshot_id))
        if self.df.empty: return
        stats = compute_stats(self.df); highlight = self.highlight.text().strip()
        focus = self.df[self.df["name"] == highlight] if highlight else self.df.iloc[0:0]
        focus_note = ""
        if not focus.empty:
            row = focus.iloc[0]; rank = int((self.df["fans_base"] > row["fans_base"]).sum() + 1)
            focus_note = f"{highlight} 排名 #{rank}"
        self.account_metric.set_data(str(stats["total"]), focus_note)
        self.fans_metric.set_data(_format_number(stats["fans"]["sum"]), f"中位数 {stats['fans']['median']:,.0f}")
        self.plays_metric.set_data(_format_number(stats["plays"]["sum"]), f"中位数 {stats['plays']['median']:,.0f}")
        self.videos_metric.set_data(f"{stats['videos']['sum']:,}", f"平均 {stats['videos']['mean']:.1f}")
        self._render_preview()

    def _render_preview(self):
        clear_layout(self.preview)
        if self.preview_figure: plt.close(self.preview_figure)
        if self.df is None or self.df.empty:
            note = QLabel("选择快照后生成分析"); note.setObjectName("Muted"); self.preview.addWidget(note); return
        self.preview_figure = bar_top_n(self.df, "fans_base", self.top_n.value(), "粉丝排名", self.highlight.text().strip())
        style_figure(self.preview_figure, self)
        canvas = FigureCanvasQTAgg(self.preview_figure); canvas.setMinimumHeight(360); canvas.draw()
        attach_bar_hover(canvas, self)
        self.preview_canvas = canvas
        self.preview.addWidget(canvas)

    def _ready(self) -> bool:
        if self.df is None or self.df.empty:
            QMessageBox.information(self, "尚未分析", "请先选择快照并生成分析。")
            return False
        return True

    def _fans(self):
        if self._ready(): BarChartWindow(self, self.df, "fans_base", self.top_n.value(), "粉丝排名", self.highlight.text().strip())

    def _plays(self):
        if self._ready(): BarChartWindow(self, self.df, "play_base", self.top_n.value(), "播放排名", self.highlight.text().strip())

    def _distribution(self):
        if not self._ready(): return
        highlight = self.highlight.text().strip(); match = self.df[self.df["name"] == highlight]
        value = match.iloc[0]["fans_base"] if not match.empty else None
        HistogramWindow(self, self.df, "fans_base", "粉丝分布", 20, highlight, value)

    def _scatter(self):
        if self._ready(): ScatterWindow(self, self.df, "fans_base", "play_base", "粉丝", "播放", "粉丝与播放关系", self.highlight.text().strip())

    def _dashboard(self):
        if not self._ready(): return
        count = self.top_n.value()
        configs = [
            {"type": "bar", "col": "fans_base", "n": count, "title": "粉丝排名"},
            {"type": "bar", "col": "play_base", "n": count, "title": "播放排名"},
            {"type": "hist", "col": "fans_base", "bins": 20, "title": "粉丝分布"},
            {"type": "scatter", "x": "fans_base", "y": "play_base", "title": "粉丝 × 播放"},
        ]
        DashboardWindow(self, self.df, configs, self.highlight.text().strip())

    def theme_changed(self):
        if self.df is not None and not self.df.empty: self._render_preview()


class ComparePage(QWidget):
    def __init__(self):
        super().__init__(); self.snapshots = []; self.result = None; self.figures = []
        box = _page_layout(self)
        box.addWidget(PageHeader("04 · COMPARE", "对比分析", "比较两个时间点，查看全局增长排行与指定学校的量化误差。"))
        controls = Card(); row = QGridLayout(); row.setHorizontalSpacing(10); row.setVerticalSpacing(10)
        self.combo_a = QComboBox(); self.combo_b = QComboBox(); self.combo_a.setMinimumWidth(260); self.combo_b.setMinimumWidth(260)
        self.highlight = QLineEdit("武汉科技大学"); compare = _primary("开始对比")
        row.addWidget(QLabel("基准快照"), 0, 0); row.addWidget(self.combo_a, 0, 1)
        row.addWidget(QLabel("对比快照"), 0, 2); row.addWidget(self.combo_b, 0, 3)
        row.addWidget(QLabel("重点学校"), 1, 0); row.addWidget(self.highlight, 1, 1)
        row.addWidget(compare, 1, 3); controls.box.addLayout(row); box.addWidget(controls)
        metrics = QHBoxLayout(); metrics.setSpacing(12)
        self.fans_metric = MetricCard("粉丝变化"); self.plays_metric = MetricCard("播放变化")
        self.videos_metric = MetricCard("视频变化"); self.accounts_metric = MetricCard("账号变化")
        for item in [self.fans_metric, self.plays_metric, self.videos_metric, self.accounts_metric]: metrics.addWidget(item, 1)
        box.addLayout(metrics)
        inspect = Card(); inspect.box.addWidget(SectionTitle("学校检查器", "搜索任意学校，查看两个端点之间的变化及取整误差。"))
        search_row = QHBoxLayout(); self.school_search = QLineEdit(); self.school_search.setPlaceholderText("输入学校名称")
        self.school_search.setClearButtonEnabled(True)
        search_row.addWidget(self.school_search, 1); inspect.box.addLayout(search_row)
        self.school_detail = QLabel("完成一次对比后可搜索学校"); self.school_detail.setObjectName("Muted"); self.school_detail.setWordWrap(True)
        inspect.box.addWidget(self.school_detail); box.addWidget(inspect)
        charts = Card(); charts.box.addWidget(SectionTitle("增长信号", "浅色或跨越零点的变化可能来自“万”单位取整。"))
        self.chart_grid = QGridLayout(); self.chart_grid.setSpacing(10); charts.box.addLayout(self.chart_grid); box.addWidget(charts)
        box.addStretch()
        compare.clicked.connect(self.compare); self.school_search.textChanged.connect(self._show_school)
        self.refresh_snapshots()

    def refresh_snapshots(self):
        self.snapshots = get_all_snapshots(); self.combo_a.clear(); self.combo_b.clear()
        for snap in self.snapshots:
            label = _snapshot_label(snap); self.combo_a.addItem(label, snap["id"]); self.combo_b.addItem(label, snap["id"])
        if len(self.snapshots) >= 2: self.combo_a.setCurrentIndex(len(self.snapshots) - 1); self.combo_b.setCurrentIndex(0)

    def _snapshot(self, combo: QComboBox):
        snapshot_id = combo.currentData()
        snap = next((item for item in self.snapshots if item["id"] == snapshot_id), None)
        return snap, get_snapshot_data(snapshot_id) if snapshot_id else []

    def compare(self):
        snap_a, data_a = self._snapshot(self.combo_a); snap_b, data_b = self._snapshot(self.combo_b)
        if not data_a or not data_b: return
        if snap_a["id"] == snap_b["id"]:
            QMessageBox.warning(self, "快照重复", "请选择两个不同的快照。")
            return
        if snap_a["created_at"] > snap_b["created_at"]:
            snap_a, snap_b = snap_b, snap_a; data_a, data_b = data_b, data_a
        self.snap_a = snap_a; self.snap_b = snap_b
        self.result = compare_snapshots(data_a, data_b, snap_a["name"], snap_b["name"])
        summary = self.result["summary"]; days = self._time_span()
        self.fans_metric.set_data(f"{summary['fans_chg']:+,.0f}", f"{days} 天观察窗口")
        self.plays_metric.set_data(f"{summary['play_chg']:+,.0f}", "累计播放变化")
        self.videos_metric.set_data(f"{summary['video_chg']:+,}", "新增发布数量")
        self.accounts_metric.set_data(f"{summary['acct_chg']:+d}", f"新增 {len(self.result['new'])} · 消失 {len(self.result['gone'])}")
        names = sorted({item["name"] for item in self.result.get("all", [])})
        completer = QCompleter(QStringListModel(names, self), self.school_search)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive); completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.school_search.setCompleter(completer)
        self.school_search.setText(self.highlight.text().strip()); self._render_charts(); self._show_school()

    def _time_span(self) -> int:
        a = datetime.fromisoformat(self.snap_a["created_at"]); b = datetime.fromisoformat(self.snap_b["created_at"])
        return max(0, (b - a).days)

    def _show_school(self):
        if not self.result: return
        query = self.school_search.text().strip().lower()
        if not query: self.school_detail.setText("输入学校名称查看变化区间"); return
        item = next((row for row in self.result.get("all", []) if row.get("name", "").lower() == query), None)
        if item is None: item = next((row for row in self.result.get("all", []) if query in row.get("name", "").lower()), None)
        if item is None: self.school_detail.setText("没有匹配的学校"); return
        ua = item.get(f"fans_unit_{self.snap_a['name']}", "个"); ub = item.get(f"fans_unit_{self.snap_b['name']}", "个")
        pa = item.get(f"play_unit_{self.snap_a['name']}", "个"); pb = item.get(f"play_unit_{self.snap_b['name']}", "个")
        _, flo, fhi, fconf = change_interval(item.get(f"fans_{self.snap_a['name']}", 0), ua,
                                             item.get(f"fans_{self.snap_b['name']}", 0), ub)
        _, plo, phi, pconf = change_interval(item.get(f"play_{self.snap_a['name']}", 0), pa,
                                             item.get(f"play_{self.snap_b['name']}", 0), pb)
        self.school_detail.setText(
            f"{item['name']}\n粉丝 {item.get('fans_chg', 0):+,.0f} · 区间 {flo:+,.0f} ～ {fhi:+,.0f} · "
            f"{'已确认' if fconf == 'confirmed' else '仍在取整误差内'}\n"
            f"播放 {item.get('play_chg', 0):+,.0f} · 区间 {plo:+,.0f} ～ {phi:+,.0f} · "
            f"{'已确认' if pconf == 'confirmed' else '仍在取整误差内'}")

    def _render_charts(self):
        clear_layout(self.chart_grid)
        for fig in self.figures: plt.close(fig)
        self.figures = []
        c = palette(bool(getattr(self.window(), "is_dark", False)))
        specs = [
            (self.result["fans_growth"], "fans_chg", "粉丝增长", c["signal"]),
            (self.result["play_growth"], "play_chg", "播放增长", c["success"]),
            (self.result["video_growth"], "video_chg", "视频增长", c["primary"]),
            (self.result["ppv_growth"], "play_per_video", "单条新视频播放", c["warning"]),
        ]
        for index, (data, column, title, color) in enumerate(specs):
            fig = self._growth_figure(data, column, title, color); self.figures.append(fig)
            canvas = FigureCanvasQTAgg(fig); attach_bar_hover(canvas, self)
            canvas.setMinimumHeight(310); canvas.draw()
            self.chart_grid.addWidget(canvas, index // 2, index % 2)

    def _growth_figure(self, data, column, title, color):
        setup_font(); fp = get_cjk_font(); c = palette(bool(getattr(self.window(), "is_dark", False)))
        rows = sorted(data[:10], key=lambda item: item.get(column, 0) or 0)
        names = [item["name"] for item in rows]; values = [item.get(column, 0) or 0 for item in rows]
        colors = [c["danger"] if value < 0 else color for value in values]
        fig, ax = plt.subplots(figsize=(5.6, 3.5), dpi=100)
        ax.barh(range(len(names)), values, color=colors)
        ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=8, fontproperties=fp)
        ax.set_title(title, fontsize=12, fontweight="bold", fontproperties=fp)
        ax.axvline(0, color=c["line"], linewidth=0.8); style_figure(fig, self); fig.tight_layout(pad=1.2)
        return fig

    def theme_changed(self):
        if self.result: self._render_charts()


class SettingsPage(QWidget):
    saved = Signal()

    def __init__(self):
        super().__init__(); box = _page_layout(self)
        box.addWidget(PageHeader("06 · SETTINGS", "采集设置", "控制请求节奏与保护阈值；修改后立即用于下一次采集。"))
        card = Card(); card.box.addWidget(SectionTitle("网络与频率", "建议保留默认值，避免给目标站点造成压力。"))
        form = QFormLayout(); form.setVerticalSpacing(12)
        self.interval = UnitStepper(0.5, 120, 3, 0.5, 1, "秒")
        self.concurrency = UnitStepper(1, 10, 3, 1, 0, "个任务")
        self.timeout = UnitStepper(5, 180, 30, 5, 0, "秒")
        self.retries = UnitStepper(0, 10, 3, 1, 0, "次")
        self.days = UnitStepper(1, 365, 7, 1, 0, "天")
        self.count = UnitStepper(1, 100, 2, 1, 0, "次")
        for label, widget in [("请求间隔", self.interval), ("最大并发", self.concurrency), ("请求超时", self.timeout),
                              ("最大重试", self.retries), ("频率窗口", self.days), ("窗口内上限", self.count)]:
            form.addRow(label, widget)
        card.box.addLayout(form); save = _primary("保存设置"); save.clicked.connect(self._save); card.box.addWidget(save)
        box.addWidget(card)
        danger = Card(); danger.box.addWidget(SectionTitle("维护", "仅清除频率计数记录，不删除数据快照。"))
        reset = QPushButton("重置频率记录"); reset.setObjectName("DangerButton"); reset.clicked.connect(self._reset)
        danger.box.addWidget(reset); box.addWidget(danger); box.addStretch(); self._load()

    def _load(self):
        self.interval.setValue(float(get_setting("request_interval", "3")))
        self.concurrency.setValue(int(get_setting("max_concurrency", "3")))
        self.timeout.setValue(int(get_setting("timeout_seconds", "30")))
        self.retries.setValue(int(get_setting("max_retries", "3")))
        self.days.setValue(int(get_setting("rate_limit_days", "7")))
        self.count.setValue(int(get_setting("rate_limit_count", "2")))

    def _save(self):
        values = {
            "request_interval": f"{self.interval.value():g}", "max_concurrency": str(int(self.concurrency.value())),
            "timeout_seconds": str(int(self.timeout.value())), "max_retries": str(int(self.retries.value())),
            "rate_limit_days": str(int(self.days.value())), "rate_limit_count": str(int(self.count.value())),
        }
        for key, value in values.items(): set_setting(key, value)
        QMessageBox.information(self, "设置已保存", "新的设置将在下一次采集时生效。")
        self.saved.emit()

    def _reset(self):
        answer = QMessageBox.question(self, "确认重置", "清除全部频率计数记录？\n数据快照不会被删除。")
        if answer == QMessageBox.StandardButton.Yes:
            reset_crawl_log(); QMessageBox.information(self, "已重置", "频率计数记录已清除。"); self.saved.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); init_db()
        self.is_dark = get_setting("theme", "light") == "dark"
        apply_theme(QApplication.instance(), self.is_dark)
        self.setWindowTitle("YSP 校园数据雷达")
        self.resize(1280, 820); self.setMinimumSize(1050, 700)
        self._build()

    def _build(self):
        root = QWidget(); root.setObjectName("AppRoot"); self.setCentralWidget(root)
        shell = QHBoxLayout(root); shell.setContentsMargins(0, 0, 0, 0); shell.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(224)
        side = QVBoxLayout(sidebar); side.setContentsMargins(18, 24, 18, 18); side.setSpacing(8)
        mark = QLabel("YSP  ·  RADAR"); mark.setObjectName("BrandMark")
        name = QLabel("校园数据雷达"); name.setObjectName("BrandName")
        caption = QLabel("公开账号 · 本地分析"); caption.setObjectName("BrandCaption")
        side.addWidget(mark); side.addWidget(name); side.addWidget(caption); side.addSpacing(22)
        self.stack = QStackedWidget(); self.nav_group = QButtonGroup(self); self.nav_group.setExclusive(True)
        labels = ["采集中心", "数据快照", "单次分析", "对比分析", "爆款监测", "采集设置"]
        prefixes = ["●", "▦", "◒", "⌁", "◆", "⚙"]
        for index, (prefix, label) in enumerate(zip(prefixes, labels)):
            button = QPushButton(f"{prefix}   {label}"); button.setObjectName("NavButton")
            button.setCheckable(True); button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, i=index: self.set_page(i))
            self.nav_group.addButton(button, index); side.addWidget(button)
            if index == 0: button.setChecked(True)
        side.addStretch()
        status = QLabel("●  本地 SQLite · 在线采集"); status.setObjectName("SidebarCaption"); side.addWidget(status)
        self.theme_button = QPushButton(); self.theme_button.setObjectName("ThemeButton")
        self.theme_button.clicked.connect(self.toggle_theme); side.addWidget(self.theme_button)
        shell.addWidget(sidebar); shell.addWidget(self.stack, 1)

        self.crawl_page = CrawlPage(); self.data_page = DataPage(); self.analysis_page = AnalysisPage()
        self.compare_page = ComparePage(); self.burst_page = BurstMonitorPage(); self.settings_page = SettingsPage()
        self.pages = [
            self.crawl_page, self.data_page, self.analysis_page,
            self.compare_page, self.burst_page, self.settings_page,
        ]
        for page in self.pages: self.stack.addWidget(_scroll_page(page))
        self.crawl_page.crawl_completed.connect(self._crawl_done)
        self.data_page.snapshots_changed.connect(self.refresh_snapshot_pages)
        self.settings_page.saved.connect(self.crawl_page.refresh)
        self._update_theme_button()

    def set_page(self, index: int):
        self.stack.setCurrentIndex(index)
        button = self.nav_group.button(index)
        if button: button.setChecked(True)
        if index == 1: self.data_page.refresh_snapshots()
        elif index == 2: self.analysis_page.refresh_snapshots()
        elif index == 3: self.compare_page.refresh_snapshots()
        elif index == 4: self.burst_page.refresh_snapshots()

    def _crawl_done(self, snapshot_id: int):
        self.refresh_snapshot_pages(); self.data_page.refresh_snapshots(snapshot_id); self.set_page(1)

    def refresh_snapshot_pages(self):
        self.analysis_page.refresh_snapshots(); self.compare_page.refresh_snapshots(); self.burst_page.refresh_snapshots()

    def toggle_theme(self):
        self.is_dark = not self.is_dark; set_setting("theme", "dark" if self.is_dark else "light")
        apply_theme(QApplication.instance(), self.is_dark); self._update_theme_button()
        self.crawl_page.theme_changed(); self.analysis_page.theme_changed()
        self.compare_page.theme_changed(); self.burst_page.theme_changed()

    def _update_theme_button(self):
        self.theme_button.setText("☀  切换浅色" if self.is_dark else "◐  切换深色")

    def closeEvent(self, event):
        if self.crawl_page.is_running():
            answer = QMessageBox.question(self, "采集仍在运行", "停止当前采集并退出？")
            if answer != QMessageBox.StandardButton.Yes: event.ignore(); return
            self.crawl_page.stop(); self.crawl_page._thread.wait(2500)
        event.accept()

    def run(self) -> int:
        self.show()
        return QApplication.instance().exec()
