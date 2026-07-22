"""HTML 解析 —— 提取 __STATE_user__ JSON，单位归一化"""
import json, re
from ..models.schema import normalize_value


def extract_state_json(html: str) -> dict | None:
    pattern = r'statesync="user"[^>]*>\s*window\.__STATE_user__\s*=\s*(\{.*?\})\s*</script>'
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        m = re.search(r"window\.__STATE_user__\s*=\s*(\{.*?\});\s*</script>", html, re.DOTALL)
    if not m: return None
    try: return json.loads(m.group(1))
    except json.JSONDecodeError: return None


def parse_account(html: str, cp_id: str = "", short_url: str = "") -> dict | None:
    state = extract_state_json(html)
    if not state: return None
    try:
        head = state.get("payloads", {}).get("headInfo", {})
        if not head:
            head = state.get("headInfo", {})
        if not head: return None

        name = head.get("cpName", "")
        if not name: return None

        fans = head.get("fansCnt", {})
        fans_raw = float(fans.get("cnt", 0)) if fans.get("cnt") else 0.0
        fans_unit = fans.get("unitTxt", "")

        play = head.get("playCnt", {})
        play_raw = float(play.get("cnt", 0)) if play.get("cnt") else 0.0
        play_unit = play.get("unitTxt", "")

        video = head.get("videoCnt", {})
        video_cnt = int(video.get("cnt", 0)) if video.get("cnt") else 0

        return {
            "cp_id": cp_id or head.get("cpID", ""),
            "name": name,
            "fans_raw": fans_raw, "fans_unit": fans_unit,
            "fans_base": normalize_value(fans_raw, fans_unit),
            "play_raw": play_raw, "play_unit": play_unit,
            "play_base": normalize_value(play_raw, play_unit),
            "video_cnt": video_cnt,
            "description": head.get("desc", ""),
            "avatar_url": head.get("avatar", ""),
            "short_url": short_url,
        }
    except (KeyError, ValueError, TypeError):
        return None
