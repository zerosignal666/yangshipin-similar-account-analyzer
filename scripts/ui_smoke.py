"""离屏验证 PySide6 主窗口、工作区和本地分析链路。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.ui.burst_window import BurstAnalysisWindow
from src.ui.main_window import MainWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert len(window.pages) == 6

    for index in range(6):
        window.set_page(index)
        app.processEvents()

    if window.analysis_page.snapshot_combo.count():
        window.analysis_page.analyze()
        assert window.analysis_page.df is not None
        assert not window.analysis_page.df.empty
        assert window.analysis_page.preview_canvas._bar_hover.connection_id is not None

    if window.compare_page.combo_a.count() >= 2:
        window.compare_page.compare()
        assert window.compare_page.result is not None

    if window.burst_page.combo_start.count() >= 2:
        window.burst_page.analyze()
        assert window.burst_page.result is not None
        assert window.burst_page.result["summary"]["mad_multiplier"] == window.burst_page.threshold.value()
        assert window.burst_page.result["summary"]["school_count"] > 0
        assert window.burst_page.table.rowCount() > 0
        detail_row = next(
            row for row in range(window.burst_page.table.rowCount())
            if window.burst_page._schools[
                window.burst_page.table.item(row, 1).data(Qt.ItemDataRole.UserRole + 1)
            ]["snapshot_count"] >= 2
        )
        window.burst_page.table.setCurrentCell(detail_row, 1)
        window.burst_page._open_detail()
        burst_windows = window.findChildren(BurstAnalysisWindow)
        assert len(burst_windows) == 1
        assert burst_windows[0]._result["intervals"]
        burst_windows[0].close()

    assert window.settings_page.interval.unit.text() == "秒"
    assert window.settings_page.interval.plus.width() >= 40
    assert window.settings_page.concurrency.unit.text() == "个任务"
    assert window.burst_page.threshold.unit.text() == "倍"

    initial_theme = window.is_dark
    window.toggle_theme(); app.processEvents()
    assert window.is_dark is not initial_theme
    window.toggle_theme(); app.processEvents()
    assert window.is_dark is initial_theme

    window.close()
    app.processEvents()
    print("GUI smoke: 6 pages, fixed-unit steppers, chart hover, burst scan, and detail passed")


if __name__ == "__main__":
    main()
