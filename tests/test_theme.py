"""浅深主题令牌与输入控件样式测试。"""

from src.ui.theme import build_stylesheet, palette


def test_sidebar_changes_with_light_and_dark_theme():
    light = palette(False)
    dark = palette(True)
    assert light["sidebar"] == "#FFFFFF"
    assert dark["sidebar"] == "#0A1120"
    assert light["sidebar_text"] != dark["sidebar_text"]


def test_double_spinbox_uses_shared_input_style():
    stylesheet = build_stylesheet(False)
    assert "QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox" in stylesheet
    assert "QDoubleSpinBox:focus" in stylesheet
