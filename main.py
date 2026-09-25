"""央视频账号分析工具 - PySide6 版。"""
import os, sys, traceback

from PySide6.QtWidgets import QApplication, QMessageBox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("YSP 校园数据雷达")
    app.setOrganizationName("YSP Analyzer")
    try:
        from src.ui.main_window import MainWindow
        window = MainWindow()
        sys.exit(window.run())
    except SystemExit:
        raise
    except Exception as e:
        err = "".join(traceback.format_exception_only(e)).strip()
        detail = traceback.format_exc()
        print(f"FATAL ERROR: {err}\n{detail}")
        QMessageBox.critical(None, "启动失败", f"{err}\n\n详细信息已输出到控制台。")
        sys.exit(1)
