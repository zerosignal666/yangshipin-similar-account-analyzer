"""爬虫引擎 —— 队列调度、并发、重试、回调通知"""
import threading, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models.database import (create_snapshot, update_snapshot_counts,
    save_account, log_crawl, can_crawl, get_setting)


class CrawlEngine:
    def __init__(self):
        self._stop = threading.Event()
        self._pause = threading.Event(); self._pause.set()
        self.running = False

    # callbacks
    def _log(self, msg, level="info"):
        if hasattr(self, "_cb_log"): self._cb_log(msg, level)

    def _progress(self, cur, total, name, status, msg=""):
        if hasattr(self, "_cb_progress"): self._cb_progress(cur, total, name, status, msg)

    def _finished(self, sid, total, ok, fail):
        if hasattr(self, "_cb_finished"): self._cb_finished(sid, total, ok, fail)

    def stop(self):
        self._stop.set(); self._pause.set(); self.running = False

    def pause(self):
        self._pause.clear()

    def resume(self):
        self._pause.set()

    def crawl(self, accounts: list[dict], snapshot_name: str = None) -> int | None:
        from .fetcher import fetch_account_page
        from .parser import parse_account

        # rate check
        limit_days = int(get_setting("rate_limit_days", "7"))
        limit_count = int(get_setting("rate_limit_count", "2"))
        ok, reason = can_crawl(limit_days, limit_count)
        if not ok:
            self._log(f"[BLOCKED] {reason}", "error")
            self._finished(-1, 0, 0, 0); return None

        self._stop.clear(); self._pause.set(); self.running = True

        if snapshot_name is None:
            snapshot_name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        sid = create_snapshot(snapshot_name)
        self._log(f"Snapshot: {snapshot_name} (ID={sid})", "info")
        self._log(f"Total accounts: {len(accounts)}", "info")

        total = len(accounts); ok_cnt = 0; fail_cnt = 0
        workers = int(get_setting("max_concurrency", "3"))
        retries = int(get_setting("max_retries", "3"))
        interval = float(get_setting("request_interval", "3"))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._crawl_one, a, interval, retries): a for a in accounts}
            for f in as_completed(futures):
                if self._stop.is_set(): break
                acc = futures[f]
                try:
                    result = f.result()
                except Exception as e:
                    result = None
                    self._log(f"Thread error [{acc['name']}]: {e}", "error")

                if result:
                    save_account(sid, result)
                    log_crawl(acc["url"], result["cp_id"], result["name"], True)
                    ok_cnt += 1
                    self._progress(ok_cnt + fail_cnt, total, result["name"], "ok",
                        f"fans:{result['fans_raw']}{result['fans_unit']} play:{result['play_raw']}{result['play_unit']} video:{result['video_cnt']}")
                else:
                    log_crawl(acc["url"], "", acc["name"], False, "failed")
                    fail_cnt += 1
                    self._progress(ok_cnt + fail_cnt, total, acc["name"], "fail", "failed")

        update_snapshot_counts(sid, total, ok_cnt, fail_cnt)
        self._log(f"Crawl done: {ok_cnt} ok, {fail_cnt} fail, {total} total",
                  "ok" if fail_cnt == 0 else "warn")
        self.running = False
        self._finished(sid, total, ok_cnt, fail_cnt)
        return sid

    def _crawl_one(self, acc, interval, max_retries):
        from .fetcher import fetch_account_page
        from .parser import parse_account
        url, name = acc["url"], acc["name"]

        for attempt in range(1, max_retries + 1):
            if self._stop.is_set(): return None
            while not self._pause.is_set():
                if self._stop.is_set(): return None
                time.sleep(0.5)
            time.sleep(interval * (2 if attempt > 1 else 1))
            try:
                page = fetch_account_page(url)
                if not page:
                    self._log(f"Retry {attempt} [{name}]: network", "warn"); continue
                result = parse_account(page["html"], page["cpid"], url)
                if result:
                    self._log(f"OK [{name}] fans:{result['fans_raw']}{result['fans_unit']} play:{result['play_raw']}{result['play_unit']} video:{result['video_cnt']}", "ok")
                    return result
                self._log(f"Retry {attempt} [{name}]: parse", "warn")
            except Exception as e:
                self._log(f"Retry {attempt} [{name}]: {e}", "warn")
        self._log(f"FAIL [{name}] after {max_retries} retries", "error")
        return None
