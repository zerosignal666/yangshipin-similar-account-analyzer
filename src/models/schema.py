"""数据表结构定义 + 单位换算"""

CREATE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    total_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    fail_count  INTEGER DEFAULT 0,
    notes       TEXT DEFAULT ''
);
"""

CREATE_ACCOUNT_DATA = """
CREATE TABLE IF NOT EXISTS account_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    cp_id       TEXT NOT NULL,
    name        TEXT NOT NULL,
    fans_raw    REAL,
    fans_unit   TEXT,
    fans_base   REAL,
    play_raw    REAL,
    play_unit   TEXT,
    play_base   REAL,
    video_cnt   INTEGER,
    description TEXT DEFAULT '',
    avatar_url  TEXT DEFAULT '',
    short_url   TEXT DEFAULT '',
    crawled_at  TEXT NOT NULL,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE,
    UNIQUE(snapshot_id, cp_id)
);
"""
CREATE_INDEX_ACCOUNT_1 = "CREATE INDEX IF NOT EXISTS idx_acc_snap ON account_data(snapshot_id);"
CREATE_INDEX_ACCOUNT_2 = "CREATE INDEX IF NOT EXISTS idx_acc_name ON account_data(name);"

CREATE_CRAWL_LOG = """
CREATE TABLE IF NOT EXISTS crawl_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    crawled_at  TEXT NOT NULL,
    url         TEXT NOT NULL,
    cp_id       TEXT DEFAULT '',
    name        TEXT DEFAULT '',
    success     INTEGER DEFAULT 0,
    error_msg   TEXT DEFAULT ''
);
"""
CREATE_INDEX_LOG = "CREATE INDEX IF NOT EXISTS idx_log_time ON crawl_log(crawled_at);"

CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

ALL_TABLES = [
    CREATE_SNAPSHOTS, CREATE_ACCOUNT_DATA,
    CREATE_INDEX_ACCOUNT_1, CREATE_INDEX_ACCOUNT_2,
    CREATE_CRAWL_LOG, CREATE_INDEX_LOG, CREATE_SETTINGS,
]

UNIT_MULTIPLIERS = {"": 1, "个": 1, "万": 10_000, "亿": 100_000_000}
DISPLAY_UNITS = ["个", "万", "亿"]


def normalize_value(raw_value: float, unit: str) -> float:
    return raw_value * UNIT_MULTIPLIERS.get(unit, 1)


def format_value(base_value: float, target_unit: str = "万") -> tuple:
    if base_value == 0:
        return 0.0, "个"
    if target_unit == "亿":
        return base_value / 100_000_000, "亿"
    elif target_unit == "万":
        return base_value / 10_000, "万"
    else:
        return base_value, "个"


def auto_unit(base_value: float) -> tuple:
    if base_value >= 100_000_000:
        return format_value(base_value, "亿")
    elif base_value >= 10_000:
        return format_value(base_value, "万")
    else:
        return format_value(base_value, "个")
