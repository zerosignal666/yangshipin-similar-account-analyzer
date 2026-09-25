"""央视频账号页面状态提取与字段解析测试。"""

import json

from src.crawler.parser import extract_state_json, parse_account


def _html(state: dict, statesync: bool = True) -> str:
    payload = json.dumps(state, ensure_ascii=False)
    if statesync:
        return f'<script statesync="user">window.__STATE_user__ = {payload}</script>'
    return f"<script>window.__STATE_user__ = {payload};</script>"


def test_extract_state_json_supports_both_script_forms():
    state = {"payloads": {"headInfo": {"cpName": "测试大学"}}}
    assert extract_state_json(_html(state)) == state
    assert extract_state_json(_html(state, statesync=False)) == state


def test_extract_state_json_rejects_missing_or_invalid_json():
    assert extract_state_json("<html></html>") is None
    assert extract_state_json("<script>window.__STATE_user__ = {broken};</script>") is None


def test_parse_account_normalizes_units_and_keeps_source_fields():
    state = {
        "payloads": {
            "headInfo": {
                "cpID": "from-page",
                "cpName": "测试大学",
                "fansCnt": {"cnt": "1.2", "unitTxt": "万"},
                "playCnt": {"cnt": "0.5", "unitTxt": "亿"},
                "videoCnt": {"cnt": "42"},
                "desc": "简介",
                "avatar": "https://example.com/avatar.png",
            }
        }
    }
    result = parse_account(_html(state), cp_id="override", short_url="https://example.com/s")
    assert result == {
        "cp_id": "override",
        "name": "测试大学",
        "fans_raw": 1.2,
        "fans_unit": "万",
        "fans_base": 12_000,
        "play_raw": 0.5,
        "play_unit": "亿",
        "play_base": 50_000_000,
        "video_cnt": 42,
        "description": "简介",
        "avatar_url": "https://example.com/avatar.png",
        "short_url": "https://example.com/s",
    }


def test_parse_account_accepts_root_head_info_and_requires_name():
    assert parse_account(_html({"headInfo": {"cpName": "根节点大学"}}))["name"] == "根节点大学"
    assert parse_account(_html({"payloads": {"headInfo": {}}})) is None
