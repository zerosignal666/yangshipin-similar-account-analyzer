"""后台爬取线程 —— QThread 信号与 Qt 主线程通信。"""
from PySide6.QtCore import QThread, Signal

from ..crawler.engine import CrawlEngine


class CrawlThread(QThread):
    log = Signal(str, str)
    progress = Signal(int, int, str, str, str)
    finished_crawl = Signal(int, int, int, int)
    failed = Signal(str)

    def __init__(self, accounts: list[dict], snapshot_name: str = ""):
        super().__init__()
        self.accounts = accounts
        self.snapshot_name = snapshot_name
        self.engine = CrawlEngine()
        self.engine._cb_log = self.log.emit
        self.engine._cb_progress = self.progress.emit
        self.engine._cb_finished = self.finished_crawl.emit

    def run(self):
        try:
            self.engine.crawl(self.accounts, self.snapshot_name)
        except Exception as exc:
            self.failed.emit(str(exc))

    def stop(self): self.engine.stop()
    def pause(self): self.engine.pause()
    def resume(self): self.engine.resume()
