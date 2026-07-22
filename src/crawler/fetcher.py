"""HTTP 请求 —— 跟随重定向获取最终页面"""
import httpx, time
from ..models.database import get_setting


def _create_client() -> httpx.Client:
    timeout = int(get_setting("timeout_seconds", "30"))
    ua = get_setting("user_agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    return httpx.Client(headers={"User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
        follow_redirects=True, timeout=timeout)


def fetch_account_page(short_url: str) -> dict | None:
    from .url_parser import parse_meta_refresh, extract_cpid
    client = _create_client()
    interval = float(get_setting("request_interval", "3"))
    try:
        resp = client.get(short_url)
        if resp.status_code != 200: return None
        redirect_url = parse_meta_refresh(resp.text)
        if not redirect_url: return None
        cpid = extract_cpid(redirect_url)
        if not cpid: return None
        time.sleep(interval)
        resp2 = client.get(redirect_url)
        if resp2.status_code != 200: return None
        return {"cpid": cpid, "html": resp2.text}
    except Exception:
        return None
    finally:
        client.close()
