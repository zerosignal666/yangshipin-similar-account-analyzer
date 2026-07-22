"""数据库操作层"""
import sqlite3, os, sys
from datetime import datetime
from .schema import ALL_TABLES

if getattr(sys, 'frozen', False):
    DB_PATH = os.path.join(os.path.dirname(sys.executable), "data", "app.db")
else:
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(_this_dir)), "data", "app.db")


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    for sql in ALL_TABLES:
        conn.execute(sql)
    defaults = {
        "request_interval": "3", "max_concurrency": "3",
        "rate_limit_days": "7", "rate_limit_count": "2",
        "display_unit": "万", "timeout_seconds": "30", "max_retries": "3",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    for k, v in defaults.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit(); conn.close()


def get_setting(key: str, default: str = "") -> str:
    conn = _connect()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = _connect()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit(); conn.close()


# --- 快照 ---
def create_snapshot(name: str, notes: str = "") -> int:
    conn = _connect()
    cur = conn.execute("INSERT INTO snapshots (name, created_at, notes) VALUES (?, ?, ?)",
                       (name, datetime.now().isoformat(), notes))
    conn.commit(); sid = cur.lastrowid; conn.close()
    return sid


def update_snapshot_counts(sid: int, total: int, success: int, fail: int):
    conn = _connect()
    conn.execute("UPDATE snapshots SET total_count=?, success_count=?, fail_count=? WHERE id=?",
                 (total, success, fail, sid))
    conn.commit(); conn.close()


def get_all_snapshots() -> list:
    conn = _connect()
    rows = conn.execute("SELECT * FROM snapshots ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_snapshot(sid: int) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM snapshots WHERE id=?", (sid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_snapshot(sid: int):
    conn = _connect()
    conn.execute("DELETE FROM account_data WHERE snapshot_id=?", (sid,))
    conn.execute("DELETE FROM snapshots WHERE id=?", (sid,))
    conn.commit(); conn.close()


# --- 账号数据 ---
def save_account(snapshot_id: int, data: dict):
    conn = _connect()
    conn.execute(
        """INSERT OR REPLACE INTO account_data
           (snapshot_id, cp_id, name, fans_raw, fans_unit, fans_base,
            play_raw, play_unit, play_base, video_cnt, description,
            avatar_url, short_url, crawled_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (snapshot_id, data["cp_id"], data["name"],
         data["fans_raw"], data["fans_unit"], data["fans_base"],
         data["play_raw"], data["play_unit"], data["play_base"],
         data["video_cnt"], data.get("description", ""),
         data.get("avatar_url", ""), data.get("short_url", ""),
         datetime.now().isoformat()))
    conn.commit(); conn.close()


def get_snapshot_data(snapshot_id: int) -> list:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM account_data WHERE snapshot_id=? ORDER BY fans_base DESC",
        (snapshot_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- 爬取日志 ---
def log_crawl(url: str, cp_id: str = "", name: str = "",
              success: bool = True, error_msg: str = ""):
    conn = _connect()
    conn.execute(
        "INSERT INTO crawl_log (crawled_at, url, cp_id, name, success, error_msg) VALUES (?,?,?,?,?,?)",
        (datetime.now().isoformat(), url, cp_id, name, 1 if success else 0, error_msg))
    conn.commit(); conn.close()


def get_crawl_count_in_window(days: int) -> int:
    conn = _connect()
    row = conn.execute(
        """SELECT COUNT(DISTINCT strftime('%Y-%m-%d %H:', crawled_at) ||
           CAST(CAST(strftime('%M', crawled_at) AS INTEGER) / 30 AS TEXT)) as batch_count
           FROM crawl_log WHERE crawled_at > datetime('now', ? || ' days')""",
        (f"-{days}",)).fetchone()
    conn.close()
    return row["batch_count"] if row else 0


def get_last_crawl_time() -> str | None:
    conn = _connect()
    row = conn.execute("SELECT crawled_at FROM crawl_log ORDER BY crawled_at DESC LIMIT 1").fetchone()
    conn.close()
    return row["crawled_at"] if row else None


def can_crawl(days_limit: int, count_limit: int) -> tuple:
    count = get_crawl_count_in_window(days_limit)
    if count >= count_limit:
        return False, f"最近 {days_limit} 天内已爬取 {count} 次（上限 {count_limit} 次）"
    return True, f"{days_limit} 天内已爬取 {count}/{count_limit} 次"


def reset_crawl_log():
    conn = _connect()
    conn.execute("DELETE FROM crawl_log")
    conn.commit(); conn.close()
