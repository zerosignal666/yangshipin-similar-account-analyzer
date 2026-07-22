"""后台爬取线程 —— threading + queue，与 Tkinter 主线程通信"""
import threading, queue
from ..crawler.engine import CrawlEngine


class CrawlThread(threading.Thread):
    def __init__(self, accounts, snapshot_name=""):
        super().__init__(daemon=True)
        self.accounts = accounts
        self.snapshot_name = snapshot_name
        self.engine = CrawlEngine()
        self.mq = queue.Queue()
        self.engine._cb_log = lambda m, l: self.mq.put(("log", (m, l)))
        self.engine._cb_progress = lambda c, t, n, s, m: self.mq.put(("progress", (c, t, n, s, m)))
        self.engine._cb_finished = lambda sid, t, ok, fail: self.mq.put(("done", (sid, t, ok, fail)))

    def run(self):
        self.engine.crawl(self.accounts, self.snapshot_name)

    def stop(self): self.engine.stop()
    def pause(self): self.engine.pause()
    def resume(self): self.engine.resume()
