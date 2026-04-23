import pandas as pd
import streamlit as st

from ui.dashboard_tables import make_recent_state_table
from ui.dashboard_helpers import (
    safe_get,
    safe_float,
    pretty_weekly_label,
    pretty_regime_label,
    state_dot_color,
)
from ui.dashboard_charts import (
    align_weekly_regime_to_weekly_index,
    build_regime_colored_chart,
    build_fast_event_chart,
)
from ui.dashboard_explanations import (
    build_market_conclusion,
    build_mid_explanation_bundle,
    build_weekly_background_explanation_bundle,
    build_fast_explanation_bundle,
)
from ui.dashboard_sections import (
    render_core_card,
    render_current_view_info,
)


# =========================================================
# Main Render
# =========================================================
def render_dashboard(
    state_df: pd.DataFrame,
    latest,
    ticker: str,
    daily_price_df: pd.DataFrame,
    weekly_price_df: pd.DataFrame,
):
    fast_event_raw = pretty_regime_label(safe_get(latest, "fast_event_display"))

    latest_close = safe_float(safe_get(latest, "Close"), 0.0)
    latest_date = getattr(latest, "name", "-")
    weekly_source = safe_get(latest, "weekly_weekly_data_source", "-")

    mid_name = pretty_regime_label(safe_get(latest, "mid_regime_name"))
    weekly_bg = pretty_weekly_label(safe_get(latest, "weekly_weekly_background_name"))
    fast_event = fast_event_raw

    mid_bundle = build_mid_explanation_bundle(mid_name)
    weekly_bundle = build_weekly_background_explanation_bundle(weekly_bg)
    fast_event_bundle = build_fast_explanation_bundle(fast_event_raw)

    # -----------------------------------------------------
    # Intro
    # -----------------------------------------------------
    st.markdown("## What This App Does（這個 App 在做什麼）")
    with st.expander("打開說明", expanded=True):
        st.markdown(
            """
這個 App 目前包含兩個主要時間框架：

- **Daily Regime（日線分類）**：使用 Yahoo Finance 的日 K（1d）
- **Weekly Regime（週線分類）**：使用 Yahoo Finance 的週 K（1wk）

它不是直接預測明天一定漲跌，而是在做三件事：

1. 看目前市場主要處於什麼狀態
2. 看更高時間尺度的大方向背景
3. 看最近是否有短期事件干擾

所以它更像是：

- 市場狀態儀表板
- Regime 研究平台
- 策略驗證入口

"""
        )

    # -----------------------------------------------------
    # Latest Price
    # -----------------------------------------------------
    st.markdown("## Latest Price（最新價格）")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.metric("Ticker", ticker)
    with p2:
        st.metric("Latest Close（最新收盤價）", f"{latest_close:.2f}")
    with p3:
        st.metric("Latest Date（最新日期）", str(latest_date)[:10])
    with p4:
        st.metric("Daily Frequency（日線頻率）", "1d（日 K）")

    st.caption("Daily Data Source（日線資料來源）：Yahoo Finance")
    st.caption(f"Weekly Data Source（週線資料來源）：{weekly_source}")

    # -----------------------------------------------------
    # Market Summary
    # -----------------------------------------------------
    st.markdown("## Market Summary（市場摘要）")
    st.info(build_market_conclusion(latest))

    s1, s2, s3 = st.columns(3)

    with s1:
        render_core_card(
            "現在市場主要狀態",
            mid_name,
            "這代表目前日線層級下，市場主要正在怎麼走。你可以把它理解成現在市場最主要的中期樣子。",
            state_dot_color=state_dot_color,
        )

    with s2:
        render_core_card(
            "大方向背景",
            weekly_bg,
            "這代表更高時間尺度下的背景底色。它不是短線進出場訊號，而是幫你判斷大方向比較站在哪一邊。",
            state_dot_color=state_dot_color,
        )

    with s3:
        render_core_card(
            "短期事件警報",
            fast_event,
            "這代表最近有沒有出現額外的短期干擾，例如波動突然放大或結構被打亂。它不是大方向，而是短線警報。",
            state_dot_color=state_dot_color,
        )

    # -----------------------------------------------------
    # Main chart
    # -----------------------------------------------------
    st.markdown("## Main Market Structure Chart（主要市場結構圖）")

    regime_view = st.radio(
        "Chart View（圖表視角）",
        options=[
            "Mid-term Regime（中期分類）",
            "Weekly Background（週線背景）",
        ],
        horizontal=True,
    )

    render_current_view_info(
        regime_view=regime_view,
        ticker=ticker,
        latest=latest,
        safe_get=safe_get,
    )

    if regime_view == "Mid-term Regime（中期分類）":
        regime_text = state_df["mid_regime_name"]
        st.plotly_chart(
            build_regime_colored_chart(
                price_df=daily_price_df,
                regime_text=regime_text,
                ticker=ticker,
                title_prefix="Mid-term Regime",
            ),
            use_container_width=True,
        )
    else:
        weekly_regime_text = align_weekly_regime_to_weekly_index(
            weekly_price_df=weekly_price_df,
            state_df=state_df,
            regime_col="weekly_weekly_background_name",
        )
        st.plotly_chart(
            build_regime_colored_chart(
                price_df=weekly_price_df,
                regime_text=weekly_regime_text,
                ticker=ticker,
                title_prefix="Weekly Background",
            ),
            use_container_width=True,
        )

    # -----------------------------------------------------
    # State Explanation
    # -----------------------------------------------------
    st.markdown("## State Explanation（目前狀態解釋）")

    tab1, tab2, tab3 = st.tabs([
        "現在市場主要狀態",
        "大方向背景",
        "短期事件警報",
    ])

    with tab1:
        st.write(f"目前狀態：{mid_name}")

        st.markdown("**一句話定位（Headline）**")
        st.info(mid_bundle["headline"])

        st.markdown("**市場特徵（Market Trait）**")
        st.write(mid_bundle["market_trait"])

        st.markdown("**使用者最該注意的風險（Risk Focus）**")
        st.warning(mid_bundle["risk_focus"])

        st.markdown("**操作含義（Trading Bias）**")
        st.write(mid_bundle["trading_bias"])

        with st.expander("查看狀態拆解（波動 / 結構 / 方向）", expanded=False):
            st.markdown(f"**波動（Volatility）**：{mid_bundle['volatility_title']}")
            st.caption(mid_bundle["volatility_desc"])

            st.markdown(f"**結構（Structure）**：{mid_bundle['structure_title']}")
            st.caption(mid_bundle["structure_desc"])

            st.markdown(f"**方向（Direction）**：{mid_bundle['direction_title']}")
            st.caption(mid_bundle["direction_desc"])

    with tab2:
        st.write(f"目前狀態：{weekly_bg}")

        st.markdown("**一句話定位（Headline）**")
        st.info(weekly_bundle["headline"])

        st.markdown("**市場特徵（Market Trait）**")
        st.write(weekly_bundle["market_trait"])

        st.markdown("**使用者最該注意的風險（Risk Focus）**")
        st.warning(weekly_bundle["risk_focus"])

        st.markdown("**操作含義（Trading Bias）**")
        st.write(weekly_bundle["trading_bias"])

    with tab3:
        st.write(f"目前狀態：{fast_event}")

        st.markdown("**一句話定位（Headline）**")
        st.info(fast_event_bundle["headline"])

        st.markdown("**事件代表什麼（Market Trait）**")
        st.write(fast_event_bundle["market_trait"])

        st.markdown("**使用者最該注意的風險（Risk Focus）**")
        st.warning(fast_event_bundle["risk_focus"])

        st.markdown("**操作含義（Trading Bias）**")
        st.write(fast_event_bundle["trading_bias"])

    # -----------------------------------------------------
    # Fast event explorer
    # -----------------------------------------------------
    st.markdown("## Fast Event Explorer（快層事件檢視區）")
    with st.expander("Fast Event 是什麼？（點我看說明）", expanded=False):
        st.markdown(
            """
Fast Event（快層事件）不是市場大方向，而是短期事件層，主要用來提醒：

- 市場是否突然出現波動衝擊
- 市場結構是否被破壞
- 是否出現短期向上或向下爆發

它的用途比較像：

- 短線風險提醒
- 短期環境警報
- 策略執行時的輔助判斷

不是單獨的買賣訊號。
"""
        )

    show_fast_event = st.checkbox(
        "Show Fast Event Explorer（顯示快層事件圖）",
        value=True,
    )

    if show_fast_event:
        event_options = {
            "volatility_shock": "Volatility Shock（波動衝擊）",
            "structural_break": "Structural Break（結構破壞）",
            "upward_burst": "Upward Burst（向上爆發）",
            "downward_burst": "Downward Burst（向下爆發）",
        }

        selected_labels = st.multiselect(
            "Select Fast Event Types（選擇要顯示的快層事件類型）",
            options=list(event_options.values()),
            default=[
                "Volatility Shock（波動衝擊）",
                "Structural Break（結構破壞）",
            ],
        )

        selected_event_types = [
            k for k, v in event_options.items() if v in selected_labels
        ]

        if selected_event_types:
            st.plotly_chart(
                build_fast_event_chart(state_df, ticker, selected_event_types),
                use_container_width=True,
            )
        else:
            st.info("請至少選擇一種 Fast Event（快層事件）類型。")

    # -----------------------------------------------------
    # Detail breakdown
    # -----------------------------------------------------
    st.markdown("## Detail Breakdown（詳細拆解）")

    with st.expander("查看 Slow / Weekly / Fast 詳細資訊", expanded=False):
        d1, d2, d3 = st.columns(3)

        with d1:
            st.markdown("### Slow Regime（慢層分類）")
            st.write(f"Short Regime（短期分類）：{safe_get(latest, 'short_regime_name')}")
            st.write(f"Mid Regime（中期分類）：{safe_get(latest, 'mid_regime_name')}")
            st.write(f"Long Regime（長期分類）：{safe_get(latest, 'long_regime_name')}")

        with d2:
            st.markdown("### Weekly Regime（週線分類）")
            weekly_ready = safe_get(latest, "weekly_weekly_ready_flag")
            weekly_ready_text = "是（已完成暖機）" if weekly_ready is True else "否（尚在暖機）"

            st.write(f"Weekly Data Source（週線資料來源）：{safe_get(latest, 'weekly_weekly_data_source')}")
            st.write(f"Weekly Ready Flag（週線是否完成暖機）：{weekly_ready_text}")
            st.write(f"Weekly Background（週線背景）：{pretty_weekly_label(safe_get(latest, 'weekly_weekly_background_name'))}")
            st.write(f"Weekly Mid Direction（週線中期方向）：{safe_get(latest, 'weekly_mid_direction_state')}")
            st.write(f"Weekly Mid Structure（週線中期結構）：{safe_get(latest, 'weekly_mid_structure_state')}")
            st.write(f"Weekly Mid Volatility（週線中期波動）：{safe_get(latest, 'weekly_mid_volatility_state')}")
            st.write(f"Weekly Mid Regime（週線中期分類）：{safe_get(latest, 'weekly_mid_regime_name')}")

        with d3:
            st.markdown("### Fast Event（快層事件）")
            st.write(f"Fast Event Display（事件顯示）：{safe_get(latest, 'fast_event_display')}")
            st.write(f"Entry Hint（進場提示）：{safe_get(latest, 'fast_entry_hint')}")
            st.write(f"Counter-Trend Hint（逆勢提示）：{safe_get(latest, 'fast_counter_trend_hint')}")
            st.write(f"Size Hint（倉位提示）：{safe_get(latest, 'fast_size_hint')}")
            st.write(f"Confidence Hint（信心提示）：{safe_get(latest, 'fast_confidence_hint')}")

    with st.expander("查看最近 20 根市場狀態", expanded=False):
        st.dataframe(
            make_recent_state_table(
                state_df=state_df,
                pretty_weekly_label=pretty_weekly_label,
            ),
            use_container_width=True,
        )

    with st.expander("查看最後 10 根完整 state dataframe（除錯用）", expanded=False):
        st.dataframe(state_df.tail(10), use_container_width=True)

    # -----------------------------------------------------
    # Glossary
    # -----------------------------------------------------
    with st.expander("Glossary（名詞解釋）", expanded=False):
        st.markdown(
            """
**Mid-term Core（中期主狀態）**  
表示目前市場最主要的日 K 中期結構，是偏多、偏空，還是盤整。

**Weekly Background（週線背景）**  
表示由 Yahoo Finance 週 K（1wk）直接計算出的背景層，用來幫助你看更慢、更穩定的大方向。

**Weekly Warmup（週線暖機中）**  
表示週線分類所需特徵尚未完全成熟。這不是市場方向判斷，而是背景層暫時仍在建立中。

**Fast Event（快層事件）**  
表示短期突然出現的事件型變化，例如波動衝擊、結構破壞。它不是市場大方向，而是短線警報。

**Daily Bar（日 K）**  
表示目前日線主層是以每天一根 K 棒的資料來做分類與測試。

**Weekly Bar（週 K）**  
表示週線背景層是以每週一根 K 棒的資料來做分類與測試。

**Yahoo Finance**  
表示目前這個原型系統的市場資料主要來自 Yahoo Finance。
"""
        )