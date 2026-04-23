import pandas as pd
import streamlit as st

from ui.strategy_lab_charts import plot_dual_trade_charts
from ui.strategy_lab_metrics import build_perf_summary
from ui.strategy_lab_controls import render_strategy_lab_controls, strictness_label
from ui.strategy_lab_runners import run_strategy
from ui.strategy_lab_report import build_strategy_lab_report_html


def _get_default_date_range(price_df: pd.DataFrame):
    start_default = price_df.index.min().date()
    end_default = price_df.index.max().date()
    return start_default, end_default


def _render_core_metrics_row(title: str, perf: dict):
    st.markdown(f"#### {title}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("總報酬", f"{perf['total_return']:.2%}")
    with c2:
        st.metric("最大回撤", f"{perf['max_dd']:.2%}")
    with c3:
        st.metric("Sharpe", f"{perf['sharpe']:.2f}")
    with c4:
        st.metric("交易筆數", f"{perf['trade_count']}")


# =========================================================
# Main page
# =========================================================
def render_strategy_lab(
    price_df: pd.DataFrame,
    state_df: pd.DataFrame,
):
    st.markdown("## Strategy Lab（策略回測實驗室）")
    st.caption("主頁只保留最核心的回測畫面；完整績效、交易明細與 Engine 分析可下載成互動報告。")

    left_col, right_col = st.columns([0.95, 2.05], gap="large")

    with left_col:
        st.markdown("### 回測區間")
        default_start, default_end = _get_default_date_range(price_df)

        start_date = st.date_input(
            "回測起始日",
            value=default_start,
            min_value=default_start,
            max_value=default_end,
            key="strategy_lab_start_date",
        )
        end_date = st.date_input(
            "回測結束日",
            value=default_end,
            min_value=default_start,
            max_value=default_end,
            key="strategy_lab_end_date",
        )

        st.markdown("---")

        strategy_key, strictness, params, _ = render_strategy_lab_controls()

        st.markdown("### 匯出")
        st.caption("下載完整互動報告，裡面會包含完整績效、資金曲線、交易明細、Engine 原因統計與最近訊號觀察。")

    result = run_strategy(
        strategy_key=strategy_key,
        price_df=price_df,
        state_df=state_df,
        strictness=strictness,
        params=params,
    )

    eng_df = result["eng_df"]
    base_signal = result["base_signal"]
    engine_signal = result["engine_signal"]

    # 回測區間
    mask = (
        (price_df.index >= pd.to_datetime(start_date))
        & (price_df.index <= pd.to_datetime(end_date))
    )
    price_df_bt = price_df.loc[mask].copy()
    state_df_bt = state_df.loc[mask].copy()
    eng_df_bt = eng_df.loc[mask].copy()

    base_perf = build_perf_summary(
        signal=base_signal,
        close=price_df["Close"],
        start_date=start_date,
        end_date=end_date,
    )
    eng_perf = build_perf_summary(
        signal=engine_signal,
        close=price_df["Close"],
        start_date=start_date,
        end_date=end_date,
    )

    base_fig, engine_fig = plot_dual_trade_charts(
        price_df=price_df_bt,
        base_signal=base_signal.loc[price_df_bt.index],
        engine_signal=engine_signal.loc[price_df_bt.index],
        base_trades_df=base_perf["trades_df"],
        engine_trades_df=eng_perf["trades_df"],
        eng_df=eng_df_bt,
    )

    report_html = build_strategy_lab_report_html(
        strategy_key=strategy_key,
        strictness=strictness,
        params=params,
        start_date=start_date,
        end_date=end_date,
        price_df=price_df_bt,
        state_df=state_df_bt,
        eng_df=eng_df_bt,
        base_signal=base_signal.loc[price_df_bt.index],
        engine_signal=engine_signal.loc[price_df_bt.index],
        base_perf=base_perf,
        eng_perf=eng_perf,
    )

    with left_col:
        st.download_button(
            label="下載完整互動報告（HTML）",
            data=report_html,
            file_name=f"strategy_lab_{strategy_key}_{strictness}_{start_date}_{end_date}.html",
            mime="text/html",
            use_container_width=True,
        )

    with right_col:
        st.markdown("### 回測概覽")
        st.caption(
            f"策略：{strategy_key}｜Engine：{strictness_label(strictness)}｜"
            f"回測區間：{pd.to_datetime(start_date).date()} ~ {pd.to_datetime(end_date).date()}"
        )

        _render_core_metrics_row("原始策略", base_perf)
        _render_core_metrics_row("加入 Engine 後", eng_perf)

        st.markdown("### 原始策略交易圖")
        st.caption("顯示原始策略在這段回測區間內的進出場，以及每筆交易最後是獲利還是虧損。綠線代表獲利，紅線代表虧損。")
        st.plotly_chart(base_fig, use_container_width=True)

        st.markdown("### 加入 Engine 後的交易圖")
        st.caption("顯示加入 Engine 後真正保留下來的交易；若原始策略進場被擋掉，圖上會額外標示。")
        st.plotly_chart(engine_fig, use_container_width=True)

    with st.expander("這頁怎麼看？", expanded=False):
        st.markdown(
            """
這一頁先讓你快速看三件事：

1. 原始策略的進出場長什麼樣子  
2. 加入 Engine 後，哪些交易被保留、哪些被擋掉  
3. 最核心的績效差異：總報酬、最大回撤、Sharpe、交易筆數  

如果你要看完整內容，例如：
- 完整績效摘要
- 資金曲線
- 交易明細
- Engine 原因分布
- 最近訊號觀察

請直接下載上方的完整互動報告。
"""
        )