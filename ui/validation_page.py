import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px


# =========================================================
# Core Builders
# =========================================================
def build_forward_return_table(
    df: pd.DataFrame,
    regime_col: str,
    close_col: str = "Close",
    horizons=(5, 10, 20),
) -> pd.DataFrame:
    tmp = df[[regime_col, close_col]].copy()

    for h in horizons:
        tmp[f"fwd_ret_{h}"] = tmp[close_col].shift(-h) / tmp[close_col] - 1.0
        tmp[f"win_{h}"] = (tmp[f"fwd_ret_{h}"] > 0).astype(float)

    grouped = tmp.groupby(regime_col)

    rows = []
    for regime_name, g in grouped:
        row = {"mid_regime_name": regime_name, "count": len(g)}
        for h in horizons:
            row[f"avg_fwd_ret_{h}"] = g[f"fwd_ret_{h}"].mean()
            row[f"win_rate_{h}"] = g[f"win_{h}"].mean()
        rows.append(row)

    out = pd.DataFrame(rows).sort_values("count", ascending=False)
    return out.reset_index(drop=True)


def build_transition_matrix(df: pd.DataFrame, regime_col: str) -> pd.DataFrame:
    tmp = df[[regime_col]].copy()
    tmp["next_regime"] = tmp[regime_col].shift(-1)

    trans = (
        tmp.dropna()
        .groupby([regime_col, "next_regime"])
        .size()
        .unstack(fill_value=0)
    )
    return trans.div(trans.sum(axis=1), axis=0)


def build_distribution_table(df: pd.DataFrame, regime_col: str) -> pd.DataFrame:
    dist_df = (
        df[regime_col]
        .value_counts(dropna=False)
        .rename_axis(regime_col)
        .reset_index(name="count")
    )
    dist_df["ratio"] = dist_df["count"] / dist_df["count"].sum()
    return dist_df


def build_validation_summary(dist_df: pd.DataFrame, fwd_df: pd.DataFrame) -> dict:
    regime_count = len(dist_df)

    largest_ratio = float(dist_df["ratio"].max()) if not dist_df.empty else 0.0
    smallest_ratio = float(dist_df["ratio"].min()) if not dist_df.empty else 0.0

    count_std = float(dist_df["count"].std()) if len(dist_df) > 1 else 0.0

    avg_ret_cols = [c for c in fwd_df.columns if c.startswith("avg_fwd_ret_")]
    win_cols = [c for c in fwd_df.columns if c.startswith("win_rate_")]

    if avg_ret_cols:
        mean_ret_by_regime = fwd_df[avg_ret_cols].mean(axis=1)
        spread_ret = float(mean_ret_by_regime.max() - mean_ret_by_regime.min())
    else:
        spread_ret = 0.0

    if win_cols:
        mean_win_by_regime = fwd_df[win_cols].mean(axis=1)
        spread_win = float(mean_win_by_regime.max() - mean_win_by_regime.min())
    else:
        spread_win = 0.0

    return {
        "regime_count": regime_count,
        "largest_ratio": largest_ratio,
        "smallest_ratio": smallest_ratio,
        "count_std": count_std,
        "spread_ret": spread_ret,
        "spread_win": spread_win,
    }


# =========================================================
# Charts
# =========================================================
def plot_distribution_chart(dist_df: pd.DataFrame, regime_col: str):
    fig = px.bar(
        dist_df,
        x=regime_col,
        y="count",
        text="count",
    )
    fig.update_layout(
        title="",
        template="plotly_dark",
        height=420,
        xaxis_title="Regime",
        yaxis_title="Count",
        margin=dict(l=20, r=20, t=20, b=20),
    )
    fig.update_traces(textposition="outside")
    return fig


def plot_forward_return_chart(fwd_df: pd.DataFrame, horizon: int):
    col = f"avg_fwd_ret_{horizon}"
    if col not in fwd_df.columns:
        return None

    fig = px.bar(
        fwd_df.sort_values(col, ascending=False),
        x="mid_regime_name",
        y=col,
        text=col,
    )
    fig.update_layout(
        title="",
        template="plotly_dark",
        height=420,
        xaxis_title="Mid Regime",
        yaxis_title=f"Average Forward Return ({horizon} bars)",
        margin=dict(l=20, r=20, t=20, b=20),
    )
    fig.update_traces(texttemplate="%{text:.2%}", textposition="outside")
    return fig


def plot_win_rate_chart(fwd_df: pd.DataFrame, horizon: int):
    col = f"win_rate_{horizon}"
    if col not in fwd_df.columns:
        return None

    fig = px.bar(
        fwd_df.sort_values(col, ascending=False),
        x="mid_regime_name",
        y=col,
        text=col,
    )
    fig.update_layout(
        title="",
        template="plotly_dark",
        height=420,
        xaxis_title="Mid Regime",
        yaxis_title=f"Win Rate ({horizon} bars)",
        margin=dict(l=20, r=20, t=20, b=20),
    )
    fig.update_traces(texttemplate="%{text:.1%}", textposition="outside")
    return fig


def plot_transition_heatmap(trans_df: pd.DataFrame):
    fig = px.imshow(
        trans_df,
        text_auto=".0%",
        aspect="auto",
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        title="",
        template="plotly_dark",
        height=520,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Next Regime",
        yaxis_title="Current Regime",
    )
    return fig


# =========================================================
# Page
# =========================================================
def render_validation_lab(state_df: pd.DataFrame):
    st.subheader("Regime Validation Lab（Regime 驗證實驗室）")
    st.caption("先驗證市場分類有沒有研究價值，再把策略建立在這些分類之上。")

    regime_col = "mid_regime_name"
    close_col = "Close"
    horizons = (5, 10, 20)

    if regime_col not in state_df.columns or close_col not in state_df.columns:
        st.error("state_df 缺少必要欄位，至少需要 mid_regime_name 與 Close。")
        return

    dist_df = build_distribution_table(state_df, regime_col=regime_col)
    fwd_df = build_forward_return_table(
        state_df,
        regime_col=regime_col,
        close_col=close_col,
        horizons=horizons,
    )
    trans_df = build_transition_matrix(state_df, regime_col=regime_col)
    summary = build_validation_summary(dist_df, fwd_df)

    # -----------------------------------------------------
    # Intro
    # -----------------------------------------------------
    with st.expander("這頁在看什麼？", expanded=True):
        st.markdown(
            """
這頁不是在看策略績效，而是在看：

1. 你的市場分類有沒有明顯區分力  
2. 不同 Regime 的未來報酬是否真的不同  
3. 某些 Regime 是不是太少、太偏，或太不穩定  
4. Regime 轉移是否有研究價值  

如果這頁看起來沒有差異，那後面把策略建在 Regime 上面，通常也不會太有意義。
"""
        )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------
    st.markdown("### Validation Summary（驗證摘要）")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Regime 數量", f"{summary['regime_count']}")
    with c2:
        st.metric("最大 Regime 佔比", f"{summary['largest_ratio']:.2%}")
    with c3:
        st.metric("最小 Regime 佔比", f"{summary['smallest_ratio']:.2%}")

    c4, c5, c6 = st.columns(3)
    with c4:
        st.metric("分布離散度", f"{summary['count_std']:.1f}")
    with c5:
        st.metric("未來報酬差距", f"{summary['spread_ret']:.2%}")
    with c6:
        st.metric("勝率差距", f"{summary['spread_win']:.2%}")

    st.info(
        "直觀來說：\n"
        "如果不同 Regime 的未來報酬與勝率差距很小，代表這套分類的研究價值可能有限；"
        "如果差距明顯，代表這些分類可能真的有資訊含量。"
    )

    # -----------------------------------------------------
    # Distribution
    # -----------------------------------------------------
    st.markdown("### Mid Regime Distribution（中期 Regime 分布）")

    st.plotly_chart(
        plot_distribution_chart(dist_df, regime_col=regime_col),
        use_container_width=True,
    )

    with st.expander("查看 Regime 分布表格", expanded=False):
        st.dataframe(dist_df, use_container_width=True)

    # -----------------------------------------------------
    # Forward Return Validation
    # -----------------------------------------------------
    st.markdown("### Forward Return Validation（未來報酬驗證）")

    selected_horizon = st.selectbox(
        "選擇驗證 horizon",
        options=list(horizons),
        index=1,
        format_func=lambda x: f"{x} bars",
    )

    left, right = st.columns(2)

    with left:
        fig_ret = plot_forward_return_chart(fwd_df, horizon=selected_horizon)
        if fig_ret is not None:
            st.markdown(f"#### 平均未來報酬（{selected_horizon} bars）")
            st.plotly_chart(fig_ret, use_container_width=True)

    with right:
        fig_win = plot_win_rate_chart(fwd_df, horizon=selected_horizon)
        if fig_win is not None:
            st.markdown(f"#### 勝率（{selected_horizon} bars）")
            st.plotly_chart(fig_win, use_container_width=True)

    with st.expander("查看 Forward Return 詳細表格", expanded=False):
        st.dataframe(fwd_df, use_container_width=True)

    # -----------------------------------------------------
    # Transition Matrix
    # -----------------------------------------------------
    st.markdown("### Mid Regime Transition Matrix（中期 Regime 轉移矩陣）")

    st.plotly_chart(
        plot_transition_heatmap(trans_df),
        use_container_width=True,
    )

    with st.expander("查看 Transition Matrix 表格", expanded=False):
        st.dataframe(trans_df, use_container_width=True)

    # -----------------------------------------------------
    # Interpretation Guide
    # -----------------------------------------------------
    with st.expander("如何解讀這頁", expanded=False):
        st.markdown(
            """
先看分布：

- 某些 Regime 如果太少，可能只是雜訊或極端狀態
- 某些 Regime 如果太多，可能代表分類過度集中，辨識力不足

再看未來報酬：

- 如果不同 Regime 的平均未來報酬差很大，代表分類有機會真的在區分市場狀態
- 如果勝率也有差，代表不只是極端值在影響，而是整體傾向真的不同

最後看轉移矩陣：

- 如果某些 Regime 很容易持續停留，代表有穩定研究價值
- 如果每一格都很快亂跳，代表這套分類可能太敏感或不夠穩
"""
        )