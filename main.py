"""央视频账号分析工具 - Tkinter 版"""
import sys, os, traceback, tkinter.messagebox as mb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        from src.ui.main_window import MainWindow
        app = MainWindow()
        app.run()
    except SystemExit:
        pass
    except Exception as e:
        # 尽量用 GUI 弹窗显示错误，否则打印到控制台
        err = "".join(traceback.format_exception_only(e)).strip()
        detail = traceback.format_exc()
        print(f"FATAL ERROR: {err}\n{detail}")
        try:
            mb.showerror("Startup Error", f"{err}\n\nSee console for details.")
        except Exception:
            pass
        sys.exit(1)
