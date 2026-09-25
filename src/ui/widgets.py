"""现代界面的通用组件。"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


class Card(QFrame):
    def __init__(self, parent=None, padding: int = 18):
        super().__init__(parent)
        self.setObjectName("Card")
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(padding, padding, padding, padding)
        self.box.setSpacing(12)


class PageHeader(QWidget):
    def __init__(self, eyebrow: str, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        eye = QLabel(eyebrow.upper())
        eye.setObjectName("Eyebrow")
        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        caption = QLabel(subtitle)
        caption.setObjectName("PageSubtitle")
        caption.setWordWrap(True)
        box.addWidget(eye)
        box.addWidget(heading)
        box.addWidget(caption)


class MetricCard(Card):
    def __init__(self, label: str, value: str = "—", caption: str = "", parent=None):
        super().__init__(parent, padding=16)
        self.label = QLabel(label)
        self.label.setObjectName("Muted")
        self.value = QLabel(value)
        self.value.setObjectName("MetricValue")
        self.caption = QLabel(caption)
        self.caption.setObjectName("MetricDelta")
        self.caption.setWordWrap(True)
        self.box.addWidget(self.label)
        self.box.addWidget(self.value)
        self.box.addWidget(self.caption)
        self.box.addStretch()

    def set_data(self, value: str, caption: str = "") -> None:
        self.value.setText(value)
        self.caption.setText(caption)


class SectionTitle(QWidget):
    def __init__(self, title: str, caption: str = "", parent=None):
        super().__init__(parent)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        heading = QLabel(title)
        heading.setObjectName("CardTitle")
        box.addWidget(heading)
        if caption:
            sub = QLabel(caption)
            sub.setObjectName("CardCaption")
            sub.setWordWrap(True)
            box.addWidget(sub)


class UnitStepper(QFrame):
    valueChanged = Signal(float)

    def __init__(
        self, minimum: float, maximum: float, value: float, step: float,
        decimals: int, unit: str, parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("UnitStepper")
        box = QHBoxLayout(self); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(0)
        self.minus = QPushButton("−"); self.plus = QPushButton("+")
        for button in (self.minus, self.plus):
            button.setObjectName("StepperButton"); button.setFixedWidth(44)
            button.setAutoRepeat(True); button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.editor = QDoubleSpinBox(); self.editor.setObjectName("StepperInput")
        self.editor.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.editor.setRange(minimum, maximum); self.editor.setSingleStep(step)
        self.editor.setDecimals(decimals); self.editor.setValue(value)
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor.setKeyboardTracking(False)
        self.unit = QLabel(unit); self.unit.setObjectName("InputUnit")
        self.unit.setAlignment(Qt.AlignmentFlag.AlignCenter); self.unit.setMinimumWidth(54)
        box.addWidget(self.minus); box.addWidget(self.editor, 1); box.addWidget(self.unit); box.addWidget(self.plus)
        self.minus.clicked.connect(self.editor.stepDown); self.plus.clicked.connect(self.editor.stepUp)
        self.editor.valueChanged.connect(self.valueChanged.emit)

    def value(self) -> float:
        return self.editor.value()

    def setValue(self, value: float) -> None:
        self.editor.setValue(value)


def label_row(label: str, widget: QWidget) -> QWidget:
    row = QWidget()
    box = QHBoxLayout(row)
    box.setContentsMargins(0, 0, 0, 0)
    text = QLabel(label)
    text.setObjectName("Muted")
    text.setMinimumWidth(94)
    box.addWidget(text)
    box.addWidget(widget, 1)
    return row


def page_container(content: QWidget) -> QWidget:
    outer = QWidget()
    outer.setObjectName("Page")
    layout = QVBoxLayout(outer)
    layout.setContentsMargins(28, 24, 28, 28)
    layout.setSpacing(18)
    layout.addWidget(content)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    return outer
