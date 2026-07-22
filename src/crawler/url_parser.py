"""URL 解析 —— 从 同类账号.txt 提取名称和链接"""
import re, os, sys


def _get_resource_path(filename):
    """Get absolute path to resource, works for dev and PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        # Check EXE directory first (user can edit the file there)
        local_path = os.path.join(os.path.dirname(sys.executable), filename)
        if os.path.exists(local_path):
            return local_path
        # Fall back to bundled copy in _internal
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), filename)


def parse_account_file(filepath: str = None) -> list[dict]:
    if filepath is None:
        filepath = _get_resource_path("同类账号.txt")
    accounts = []
    url_pattern = re.compile(r"https?://www\.yspapp\.cn/\S+")
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            m = url_pattern.search(line)
            if not m: continue
            url = m.group(0).rstrip("/")
            name_part = line[:m.start()].strip()
            name_part = re.sub(r"^\d+\s*", "", name_part)
            name = re.sub(r"-央视频$", "", name_part).strip()
            if name and url:
                accounts.append({"name": name, "url": url})
    return accounts


def extract_cpid(redirect_url: str) -> str:
    m = re.search(r"cpid=(\d+)", redirect_url)
    return m.group(1) if m else ""


def parse_meta_refresh(html: str) -> str | None:
    m = re.search(r"URL='([^']+)'", html, re.IGNORECASE)
    if m: return m.group(1)
    m = re.search(r'URL="([^"]+)"', html, re.IGNORECASE)
    return m.group(1) if m else None
