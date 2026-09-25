"""步进输入与 Matplotlib 柱图悬停交互测试。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QApplication, QWidget

from src.ui.chart_windows import attach_bar_hover
from src.ui.widgets import UnitStepper


def _app():
    return QApplication.instance() or QApplication([])


def test_unit_stepper_keeps_unit_fixed_and_uses_large_buttons():
    _app()
    stepper = UnitStepper(0.5, 10, 3, 0.5, 1, "倍")
    assert stepper.editor.suffix() == ""
    assert stepper.unit.text() == "倍"
    assert stepper.plus.width() == 44
    stepper.plus.click()
    assert stepper.value() == 3.5


def test_bar_hover_shows_exact_value_for_embedded_chart():
    _app(); parent = QWidget(); parent.is_dark = True
    fig, ax = plt.subplots()
    ax.barh([0, 1], [10, 20]); ax.set_yticks([0, 1]); ax.set_yticklabels(["University A", "University B"])
    canvas = FigureCanvasQTAgg(fig); hover = attach_bar_hover(canvas, parent); canvas.draw()
    x, y = ax.transData.transform((5, 0))
    hover._on_hover(MouseEvent("motion_notify_event", canvas, x, y))
    annotation = hover._annotations[ax]
    assert hover.connection_id is not None
    assert annotation.get_visible() is True
    assert "University A" in annotation.get_text()
    assert "10" in annotation.get_text()
    x, y = ax.transData.transform((19, 1))
    hover._on_hover(MouseEvent("motion_notify_event", canvas, x, y))
    assert annotation.get_position()[0] < 0
    plt.close(fig)
