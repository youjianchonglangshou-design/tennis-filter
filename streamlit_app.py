from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from crawler import CrawlerError, PinnacleCrawler

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
DEFAULT_MIN_ODDS = 1.50
DEFAULT_MAX_ODDS = 1.70
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
        font-size: 1.08rem;
        font-weight: 700;
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


def get_api_key() -> str | None:
    """優先讀取 Streamlit Secrets；未設定時使用 crawler 內建 guest key。"""
    try:
        value = st.secrets.get("PINNACLE_API_KEY")
        return str(value) if value else None
    except Exception:
        return None


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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def run_analysis(
    *,
    filter_enabled: bool,
    min_odds: float,
    max_odds: float,
) -> None:
    """執行一次抓取，成功後更新 Session State。"""
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


def make_json_bytes() -> bytes:
    payload = {
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
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def render_status_cards() -> None:
    updated = st.session_state.last_updated or "尚未更新"
    count = len(st.session_state.matches)
    filter_text = (
        f"{st.session_state.applied_min_odds:.2f} ～ {st.session_state.applied_max_odds:.2f}"
        if st.session_state.applied_filter_enabled
        else "未啟用"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="status-card">
                <div class="status-label">最後更新｜台灣時間</div>
                <div class="status-value">{updated}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="status-card">
                <div class="status-label">符合條件賽事</div>
                <div class="status-value">{count} 場</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="status-card">
                <div class="status-label">目前賠率篩選</div>
                <div class="status-value">{filter_text}</div>
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
            首次進入自動抓取；按下「重新分析」可依目前賠率條件再次取得資料。
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
        with st.spinner("正在抓取 Pinnacle 網球賽事與賠率……"):
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
    st.info("可稍後按下「重新分析」重試；若 API key 已變更，可在 Streamlit Secrets 設定 PINNACLE_API_KEY。")

render_status_cards()
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

filename_time = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d_%H%M%S")
st.download_button(
    label="⬇️ 下載 JSON",
    data=make_json_bytes(),
    file_name=f"pinnacle_matches_{filename_time}.json",
    mime="application/json",
    use_container_width=True,
    disabled=st.session_state.last_updated is None,
)

st.caption(
    "資料時間與最後更新時間皆以 Asia/Taipei 顯示。Pinnacle guest API、端點或防爬規則若變更，抓取可能失敗。"
)
