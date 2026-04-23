import streamlit as st
import pandas as pd

from data.loader import load_price_data
from engine.state_builder import build_full_market_state, build_state_summary_row
from regimes.weekly_regime import download_weekly_price_df

from ui.dashboard_page import render_dashboard
from ui.validation_page import render_validation_lab
from ui.strategy_lab_page import render_strategy_lab
from ui.methodology_page import render_methodology_page


# =========================================================
# Period helpers
# =========================================================
def map_display_period_to_calc_period(display_period: str) -> str:
    """
    使用者看到的顯示期間，不一定等於內部計算期間。
    內部多抓一段歷史，讓 regime / weekly / fast event 有暖機空間。
    """
    mapping = {
        "1y": "3y",
        "3y": "5y",
        "5y": "10y",
        "10y": "max",
        "20y": "max",
        "max": "max",
    }
    return mapping.get(display_period, display_period)


def cut_df_to_display_period(df: pd.DataFrame, display_period: str) -> pd.DataFrame:
    """
    將較長的計算資料裁切成使用者要看的顯示區間。
    """
    if df is None or df.empty:
        return df

    if display_period == "max":
        return df.copy()

    period_to_days = {
        "1y": 365,
        "3y": 365 * 3,
        "5y": 365 * 5,
        "10y": 365 * 10,
        "20y": 365 * 20,
    }

    days = period_to_days.get(display_period)
    if days is None:
        return df.copy()

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    end_dt = df.index.max()
    start_dt = end_dt - pd.Timedelta(days=days)

    return df.loc[df.index >= start_dt].copy()


# =========================================================
# Cached loaders
# =========================================================
@st.cache_data(show_spinner=False)
def cached_load_price_data(ticker: str, period: str):
    return load_price_data(ticker, period=period)


@st.cache_data(show_spinner=False)
def cached_build_full_market_state(ticker: str, calc_period: str):
    """
    注意：這裡吃的是 calc_period，不是 display_period。
    """
    price_df_full = load_price_data(ticker, period=calc_period)
    weekly_price_df_full = download_weekly_price_df(ticker=ticker, period=calc_period)

    state_df_full = build_full_market_state(
        price_df=price_df_full,
        ticker=ticker,
        period=calc_period,
    )
    latest_full = build_state_summary_row(state_df_full)

    return price_df_full, weekly_price_df_full, state_df_full, latest_full


# =========================================================
# Page config
# =========================================================
st.set_page_config(
    page_title="Market Structure & Strategy Lab",
    layout="wide",
)

st.title("Market Structure & Strategy Lab")
st.caption("Market Structure Classification / Strategy Research / Engine-Based Signal Filtering")

st.sidebar.header("參數設定")

ticker = st.sidebar.text_input("Ticker", value="AAPL")
display_period = st.sidebar.selectbox(
    "Period",
    options=["1y", "3y", "5y", "10y", "20y", "max"],
    index=1,
)

calc_period = map_display_period_to_calc_period(display_period)

st.sidebar.caption(f"顯示期間：{ticker} / {display_period}")
st.sidebar.caption(f"內部計算期間：{calc_period}")

try:
    with st.spinner("下載資料並建立市場狀態中..."):
        price_df_full, weekly_price_df_full, state_df_full, latest_full = cached_build_full_market_state(
            ticker, calc_period
        )

        # -------------------------------------------------
        # 裁切成使用者要看的區間
        # -------------------------------------------------
        price_df = cut_df_to_display_period(price_df_full, display_period)
        weekly_price_df = cut_df_to_display_period(weekly_price_df_full, display_period)
        state_df = cut_df_to_display_period(state_df_full, display_period)

        latest = build_state_summary_row(state_df)

except Exception as e:
    st.error(f"資料載入 / state builder 失敗：{e}")
    st.stop()

methodology_tab, dashboard_tab, validation_tab, strategy_tab = st.tabs(
    ["Methodology / About", "Market Dashboard", "Regime Validation Lab", "Strategy Lab"]
)

with methodology_tab:
    try:
        render_methodology_page()
    except Exception as e:
        st.error(f"Methodology 頁面失敗：{e}")

with dashboard_tab:
    try:
        render_dashboard(
            state_df=state_df,
            latest=latest,
            ticker=ticker,
            daily_price_df=price_df,
            weekly_price_df=weekly_price_df,
        )
    except Exception as e:
        st.error(f"Dashboard 頁面失敗：{e}")

with validation_tab:
    try:
        render_validation_lab(state_df)
    except Exception as e:
        st.error(f"Validation 頁面失敗：{e}")

with strategy_tab:
    try:
        render_strategy_lab(
            price_df=price_df,
            state_df=state_df,
        )
    except Exception as e:
        st.error(f"Strategy Lab 頁面失敗：{e}")