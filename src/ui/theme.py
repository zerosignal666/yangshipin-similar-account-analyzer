"""PySide6 主题与视觉令牌。"""
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication


LIGHT = {
    "canvas": "#F3F6FA",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "sidebar": "#FFFFFF",
    "sidebar_hover": "#E9EFF8",
    "sidebar_text": "#42516B",
    "sidebar_muted": "#72819A",
    "sidebar_line": "#DCE3ED",
    "sidebar_brand": "#172033",
    "tooltip_bg": "#172033",
    "tooltip_text": "#FFFFFF",
    "text": "#172033",
    "muted": "#69758A",
    "line": "#DCE3ED",
    "primary": "#3568D4",
    "primary_hover": "#2B59B8",
    "signal": "#27A6B7",
    "success": "#2F9D6A",
    "warning": "#D68B2C",
    "danger": "#D95858",
}

DARK = {
    "canvas": "#111827",
    "surface": "#182235",
    "surface_alt": "#202C41",
    "sidebar": "#0A1120",
    "sidebar_hover": "#1B2940",
    "sidebar_text": "#C3CEE0",
    "sidebar_muted": "#97A8C3",
    "sidebar_line": "#33435E",
    "sidebar_brand": "#FFFFFF",
    "tooltip_bg": "#0A1120",
    "tooltip_text": "#FFFFFF",
    "text": "#E8EDF5",
    "muted": "#9CA9BA",
    "line": "#314159",
    "primary": "#6F9AF1",
    "primary_hover": "#8BACF3",
    "signal": "#4CC4D0",
    "success": "#56C58A",
    "warning": "#E9A94B",
    "danger": "#F07676",
}


def palette(dark: bool) -> dict[str, str]:
    return DARK if dark else LIGHT


def app_font() -> QFont:
    font = QFont()
    font.setFamilies(["PingFang SC", "Microsoft YaHei UI", "Noto Sans CJK SC", "Arial"])
    font.setPointSize(10)
    return font


def build_stylesheet(dark: bool) -> str:
    c = palette(dark)
    return f"""
    * {{ outline: none; }}
    QMainWindow, QWidget#AppRoot {{ background: {c['canvas']}; color: {c['text']}; }}
    QWidget {{ font-size: 13px; color: {c['text']}; }}
    QFrame#Sidebar {{
        background: {c['sidebar']}; border: none; border-right: 1px solid {c['sidebar_line']};
    }}
    QLabel#BrandMark {{ color: {c['sidebar_brand']}; font-size: 19px; font-weight: 800; }}
    QLabel#BrandName {{ color: {c['sidebar_brand']}; font-size: 15px; font-weight: 700; }}
    QLabel#BrandCaption, QLabel#SidebarCaption {{ color: {c['sidebar_muted']}; font-size: 11px; }}
    QPushButton#NavButton {{
        color: {c['sidebar_text']}; background: transparent; border: none; border-radius: 9px;
        text-align: left; padding: 10px 13px; font-size: 14px;
    }}
    QPushButton#NavButton:hover {{ background: {c['sidebar_hover']}; color: {c['sidebar_brand']}; }}
    QPushButton#NavButton:checked {{
        background: {c['primary']}; color: white; font-weight: 700;
    }}
    QPushButton#ThemeButton {{
        color: {c['sidebar_text']}; background: {c['sidebar_hover']}; border: 1px solid {c['sidebar_line']};
        border-radius: 9px; padding: 9px 12px; text-align: left;
    }}
    QPushButton#ThemeButton:hover {{ border-color: {c['signal']}; }}
    QScrollArea, QStackedWidget {{ border: none; background: transparent; }}
    QWidget#Page {{ background: {c['canvas']}; }}
    QLabel#Eyebrow {{ color: {c['primary']}; font-size: 11px; font-weight: 800; }}
    QLabel#PageTitle {{ color: {c['text']}; font-size: 27px; font-weight: 800; }}
    QLabel#PageSubtitle {{ color: {c['muted']}; font-size: 13px; }}
    QFrame#Card {{
        background: {c['surface']}; border: 1px solid {c['line']}; border-radius: 14px;
    }}
    QLabel#CardTitle {{ color: {c['text']}; font-size: 14px; font-weight: 700; }}
    QLabel#CardCaption, QLabel#Muted {{ color: {c['muted']}; font-size: 12px; }}
    QLabel#MetricValue {{ color: {c['text']}; font-size: 24px; font-weight: 800; }}
    QLabel#MetricDelta {{ color: {c['signal']}; font-size: 12px; font-weight: 700; }}
    QLabel#BurstCallout {{
        color: {c['text']}; background: {c['surface']}; border: 1px solid {c['warning']};
        border-left: 5px solid {c['warning']}; border-radius: 10px; padding: 13px 15px;
        font-size: 13px; font-weight: 600;
    }}
    QLabel#SignalStrip {{
        color: {c['text']}; background: {c['surface_alt']}; border: 1px solid {c['line']};
        border-radius: 10px; padding: 14px 16px; font-size: 13px;
    }}
    QPushButton {{
        background: {c['surface']}; border: 1px solid {c['line']}; border-radius: 8px;
        padding: 8px 14px; min-height: 18px;
    }}
    QPushButton:hover {{ border-color: {c['primary']}; color: {c['primary']}; }}
    QPushButton:disabled {{ color: {c['muted']}; background: {c['surface_alt']}; }}
    QPushButton#PrimaryButton {{
        color: white; background: {c['primary']}; border-color: {c['primary']}; font-weight: 700;
    }}
    QPushButton#PrimaryButton:hover {{ background: {c['primary_hover']}; color: white; }}
    QPushButton#DangerButton {{ color: {c['danger']}; border-color: {c['danger']}; }}
    QPushButton#DangerButton:hover {{ color: white; background: {c['danger']}; }}
    QPushButton#BurstButton {{
        color: white; background: {c['warning']}; border-color: {c['warning']}; font-weight: 700;
    }}
    QPushButton#BurstButton:hover {{ color: white; background: {c['danger']}; border-color: {c['danger']}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {c['surface']}; color: {c['text']}; border: 1px solid {c['line']};
        border-radius: 8px; padding: 7px 10px; min-height: 20px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {c['primary']}; }}
    QFrame#UnitStepper {{
        background: {c['surface']}; border: 1px solid {c['line']}; border-radius: 9px;
    }}
    QDoubleSpinBox#StepperInput {{
        background: transparent; color: {c['text']}; border: none; padding: 8px 10px;
        min-height: 22px; font-weight: 700;
    }}
    QLabel#InputUnit {{
        color: {c['muted']}; background: transparent; border: none; padding: 0 8px;
        font-size: 12px; font-weight: 700;
    }}
    QPushButton#StepperButton {{
        color: {c['primary']}; background: {c['surface_alt']}; border: none;
        border-radius: 7px; padding: 6px 0; min-height: 24px; font-size: 18px; font-weight: 800;
    }}
    QPushButton#StepperButton:hover {{ color: white; background: {c['primary']}; }}
    QPushButton#StepperButton:pressed {{ color: white; background: {c['primary_hover']}; }}
    QLabel#InfoCallout {{
        color: {c['muted']}; background: {c['surface_alt']}; border: 1px solid {c['line']};
        border-radius: 9px; padding: 10px 12px; font-size: 12px;
    }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background: {c['surface']}; color: {c['text']}; selection-background-color: {c['primary']};
        border: 1px solid {c['line']};
    }}
    QPlainTextEdit, QTextEdit {{
        background: {c['surface_alt']}; color: {c['text']}; border: 1px solid {c['line']};
        border-radius: 10px; padding: 8px; font-family: "Cascadia Mono", "SFMono-Regular", monospace;
    }}
    QProgressBar {{
        background: {c['surface_alt']}; border: none; border-radius: 5px; height: 10px; text-align: center;
    }}
    QProgressBar::chunk {{ background: {c['signal']}; border-radius: 5px; }}
    QTableWidget {{
        background: {c['surface']}; alternate-background-color: {c['surface_alt']};
        color: {c['text']}; border: 1px solid {c['line']}; border-radius: 12px;
        gridline-color: {c['line']}; selection-background-color: {c['primary']};
    }}
    QHeaderView::section {{
        background: {c['surface_alt']}; color: {c['muted']}; border: none;
        border-bottom: 1px solid {c['line']}; padding: 10px 8px; font-weight: 700;
    }}
    QListWidget {{
        background: {c['surface']}; color: {c['text']}; border: 1px solid {c['line']};
        border-radius: 10px; padding: 4px;
    }}
    QListWidget::item {{ padding: 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background: {c['primary']}; color: white; }}
    QTabWidget::pane {{ border: 1px solid {c['line']}; border-radius: 10px; background: {c['surface']}; }}
    QTabBar::tab {{ padding: 9px 16px; color: {c['muted']}; }}
    QTabBar::tab:selected {{ color: {c['primary']}; font-weight: 700; }}
    QToolTip {{ background: {c['tooltip_bg']}; color: {c['tooltip_text']}; border: none; padding: 6px; }}
    """


def apply_theme(app: QApplication, dark: bool) -> None:
    app.setStyle("Fusion")
    app.setFont(app_font())
    app.setStyleSheet(build_stylesheet(dark))
    pal = app.palette()
    c = palette(dark)
    pal.setColor(pal.ColorRole.Window, QColor(c["canvas"]))
    pal.setColor(pal.ColorRole.Base, QColor(c["surface"]))
    pal.setColor(pal.ColorRole.Text, QColor(c["text"]))
    app.setPalette(pal)
