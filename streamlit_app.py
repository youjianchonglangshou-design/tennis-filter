from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from curl_cffi import requests as http_requests

from crawler import CrawlerError, PinnacleCrawler

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
DEFAULT_MIN_ODDS = 1.50
DEFAULT_MAX_ODDS = 1.70

# 下載與回寫 GitHub 都固定使用這個檔名。
JSON_FILENAME = "today_matches.json"
GITHUB_REPOSITORY = "youjianchonglangshou-design/tennis-filter"
GITHUB_BRANCH = "main"
GITHUB_JSON_PATH = JSON_FILENAME

TABLE_COLUMNS = [
    "項次",
    "日期時間",
    "聯賽",
    "主場",
    "客場",
    "主場賠率",
    "客場賠率",
]

st.set_page_config(
    page_title="網球賽事分析",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top, #102337 0%, #07111d 48%, #03070c 100%);
    }
    .block-container {
        max-width: 1500px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    .hero {
        border: 1px solid rgba(94, 234, 212, 0.30);
        background: linear-gradient(135deg, rgba(15, 42, 60, 0.92), rgba(5, 14, 25, 0.95));
        border-radius: 18px;
        padding: 22px 26px;
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
        margin-bottom: 18px;
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        color: #e6fffb;
        margin-bottom: 5px;
    }
    .hero-subtitle {
        color: #9fb6c6;
        font-size: 0.98rem;
    }
    .status-card {
        border: 1px solid rgba(56, 189, 248, 0.22);
        border-radius: 14px;
        padding: 13px 16px;
        background: rgba(7, 20, 32, 0.76);
        min-height: 78px;
    }
    .status-label {
        color: #7f9aac;
        font-size: 0.82rem;
        margin-bottom: 6px;
    }
    .status-value {
        color: #e6fffb;
        font-size: 1.03rem;
        font-weight: 700;
        overflow-wrap: anywhere;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(94, 234, 212, 0.22);
        border-radius: 14px;
        overflow: hidden;
    }
    div.stButton > button,
    div.stDownloadButton > button,
    button[kind="primary"] {
        border-radius: 10px;
        min-height: 44px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_secret(name: str) -> str | None:
    """安全讀取 Streamlit Secrets。"""
    try:
        value = st.secrets.get(name)
        return str(value).strip() if value else None
    except Exception:
        return None


def get_api_key() -> str | None:
    """未設定時使用 crawler 內建的 Pinnacle guest key。"""
    return get_secret("PINNACLE_API_KEY")


def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "initialized": False,
        "matches": [],
        "last_updated": None,
        "filter_enabled": True,
        "min_odds": DEFAULT_MIN_ODDS,
        "max_odds": DEFAULT_MAX_ODDS,
        "applied_filter_enabled": True,
        "applied_min_odds": DEFAULT_MIN_ODDS,
        "applied_max_odds": DEFAULT_MAX_ODDS,
        "last_error": None,
        "github_sync_status": "尚未同步",
        "github_sync_message": None,
        "github_commit_sha": None,
        "github_file_url": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def make_json_payload() -> dict[str, Any]:
    return {
        "batch_date": datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d"),
        "query_time": st.session_state.last_updated,
        "timezone": "Asia/Taipei",
        "filter": {
            "enabled": st.session_state.applied_filter_enabled,
            "min_odds": st.session_state.applied_min_odds,
            "max_odds": st.session_state.applied_max_odds,
        },
        "matches": st.session_state.matches,
    }


def make_json_text() -> str:
    return json.dumps(make_json_payload(), ensure_ascii=False, indent=2)


def make_json_bytes() -> bytes:
    return make_json_text().encode("utf-8")


def push_json_to_github(json_text: str) -> dict[str, str | bool | None]:
    """建立或覆蓋 main/today_matches.json。"""
    token = get_secret("GITHUB_TOKEN")
    if not token:
        return {
            "ok": False,
            "status": "尚未設定",
            "message": "請先在 Streamlit Secrets 設定 GITHUB_TOKEN。",
            "commit_sha": None,
            "file_url": None,
        }

    encoded_path = quote(GITHUB_JSON_PATH, safe="/")
    api_url = (
        f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{encoded_path}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "tennis-filter-streamlit",
    }

    current_sha: str | None = None
    current_response = http_requests.get(
        api_url,
        headers=headers,
        params={"ref": GITHUB_BRANCH},
        timeout=20,
    )

    if current_response.status_code == 200:
        current_sha = current_response.json().get("sha")
    elif current_response.status_code != 404:
        detail = current_response.text[:500]
        raise RuntimeError(
            f"讀取 GitHub 現有 JSON 失敗：HTTP {current_response.status_code}｜{detail}"
        )

    payload: dict[str, Any] = {
        "message": (
            f"更新 {JSON_FILENAME}｜"
            f"{st.session_state.last_updated or datetime.now(TAIPEI_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        "content": base64.b64encode(json_text.encode("utf-8")).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if current_sha:
        payload["sha"] = current_sha

    write_response = http_requests.put(
        api_url,
        headers=headers,
        json=payload,
        timeout=30,
    )
    if write_response.status_code not in (200, 201):
        detail = write_response.text[:500]
        raise RuntimeError(
            f"回寫 GitHub JSON 失敗：HTTP {write_response.status_code}｜{detail}"
        )

    response_data = write_response.json()
    commit_sha = response_data.get("commit", {}).get("sha")
    file_url = response_data.get("content", {}).get("html_url")

    return {
        "ok": True,
        "status": "同步成功",
        "message": f"已覆蓋 {GITHUB_BRANCH}/{GITHUB_JSON_PATH}",
        "commit_sha": commit_sha,
        "file_url": file_url,
    }


def sync_current_json_to_github() -> None:
    try:
        result = push_json_to_github(make_json_text())
        st.session_state.github_sync_status = result["status"]
        st.session_state.github_sync_message = result["message"]
        st.session_state.github_commit_sha = result["commit_sha"]
        st.session_state.github_file_url = result["file_url"]
    except Exception as exc:
        st.session_state.github_sync_status = "同步失敗"
        st.session_state.github_sync_message = str(exc)
        st.session_state.github_commit_sha = None
        st.session_state.github_file_url = None


def run_analysis(
    *,
    filter_enabled: bool,
    min_odds: float,
    max_odds: float,
) -> None:
    """抓取比賽，成功後更新畫面並同步固定 JSON 到 GitHub。"""
    crawler = PinnacleCrawler(api_key=get_api_key())
    matches = crawler.get_matches(
        filter_enabled=filter_enabled,
        min_odds=min_odds,
        max_odds=max_odds,
    )

    st.session_state.matches = matches
    st.session_state.last_updated = datetime.now(TAIPEI_TZ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    st.session_state.applied_filter_enabled = filter_enabled
    st.session_state.applied_min_odds = float(min_odds)
    st.session_state.applied_max_odds = float(max_odds)
    st.session_state.last_error = None

    sync_current_json_to_github()


def render_status_cards() -> None:
    updated = st.session_state.last_updated or "尚未更新"
    count = len(st.session_state.matches)
    filter_text = (
        f"{st.session_state.applied_min_odds:.2f} ～ {st.session_state.applied_max_odds:.2f}"
        if st.session_state.applied_filter_enabled
        else "未啟用"
    )
    github_status = st.session_state.github_sync_status

    col1, col2, col3, col4 = st.columns(4)
    cards = (
        (col1, "最後更新｜台灣時間", updated),
        (col2, "符合條件賽事", f"{count} 場"),
        (col3, "目前賠率篩選", filter_text),
        (col4, f"GitHub｜{JSON_FILENAME}", github_status),
    )

    for column, label, value in cards:
        with column:
            st.markdown(
                f"""
                <div class="status-card">
                    <div class="status-label">{label}</div>
                    <div class="status-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


initialize_state()

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">🎾 Pinnacle 網球賽事分析</div>
        <div class="hero-subtitle">
            首次進入自動抓取；按下「重新分析」會重新取得資料，並覆蓋 GitHub 的 today_matches.json。
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

control1, control2, control3, control4 = st.columns([1.25, 1, 1, 1.25])
with control1:
    filter_enabled = st.checkbox(
        "啟用賠率過濾",
        key="filter_enabled",
    )
with control2:
    min_odds = st.number_input(
        "最低賠率",
        min_value=1.01,
        max_value=100.0,
        step=0.01,
        format="%.2f",
        disabled=not filter_enabled,
        key="min_odds",
    )
with control3:
    max_odds = st.number_input(
        "最高賠率",
        min_value=1.01,
        max_value=100.0,
        step=0.01,
        format="%.2f",
        disabled=not filter_enabled,
        key="max_odds",
    )
with control4:
    st.write("")
    st.write("")
    submitted = st.button(
        "🔄 重新分析",
        type="primary",
        use_container_width=True,
    )

should_fetch = not st.session_state.initialized or submitted

if should_fetch:
    st.session_state.initialized = True
    try:
        with st.spinner("正在抓取 Pinnacle 網球賽事、整理 JSON 並同步 GitHub……"):
            run_analysis(
                filter_enabled=filter_enabled,
                min_odds=float(min_odds),
                max_odds=float(max_odds),
            )
    except (CrawlerError, ValueError) as exc:
        st.session_state.last_error = str(exc)
    except Exception as exc:
        st.session_state.last_error = f"系統錯誤：{exc}"

if st.session_state.last_error:
    st.error(st.session_state.last_error)
    st.info(
        "可稍後按下「重新分析」重試；若 API key 已變更，可在 Streamlit Secrets 設定 PINNACLE_API_KEY。"
    )

render_status_cards()

sync_status = st.session_state.github_sync_status
sync_message = st.session_state.github_sync_message
if sync_status == "同步成功":
    commit_sha = st.session_state.github_commit_sha
    sha_text = f"｜Commit {commit_sha[:7]}" if commit_sha else ""
    file_url = st.session_state.github_file_url
    if file_url:
        st.success(f"GitHub 同步成功：{GITHUB_JSON_PATH}{sha_text}")
        st.markdown(f"[開啟 GitHub JSON]({file_url})")
    else:
        st.success(f"GitHub 同步成功：{GITHUB_JSON_PATH}{sha_text}")
elif sync_status == "尚未設定":
    st.info(
        "JSON 下載功能已可使用；要自動回寫 GitHub，請在 Streamlit Secrets 加入 GITHUB_TOKEN。"
    )
elif sync_status == "同步失敗" and sync_message:
    st.warning(f"GitHub 同步失敗：{sync_message}")

st.write("")

matches = st.session_state.matches
if matches:
    dataframe = pd.DataFrame(matches, columns=TABLE_COLUMNS)
    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
        height=min(720, 38 * (len(dataframe) + 1) + 6),
        column_config={
            "項次": st.column_config.NumberColumn("項次", width="small", format="%d"),
            "日期時間": st.column_config.TextColumn("日期時間", width="medium"),
            "聯賽": st.column_config.TextColumn("聯賽", width="large"),
            "主場": st.column_config.TextColumn("主場", width="large"),
            "客場": st.column_config.TextColumn("客場", width="large"),
            "主場賠率": st.column_config.TextColumn("主場賠率", width="small"),
            "客場賠率": st.column_config.TextColumn("客場賠率", width="small"),
        },
    )
else:
    st.warning("目前沒有符合篩選條件的賽事，或尚未成功取得資料。")

st.download_button(
    label=f"⬇️ 下載 {JSON_FILENAME}",
    data=make_json_bytes(),
    file_name=JSON_FILENAME,
    mime="application/json",
    use_container_width=True,
    disabled=st.session_state.last_updated is None,
)

st.caption(
    "資料時間與最後更新時間皆以 Asia/Taipei 顯示。每次首次載入或按下重新分析，"
    "都會嘗試覆蓋 GitHub main/today_matches.json。"
)
