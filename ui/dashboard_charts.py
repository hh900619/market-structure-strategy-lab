import pandas as pd
import plotly.graph_objects as go


def classify_regime_masks(regime_text: pd.Series):
    regime_text = regime_text.astype(str)

    warmup_mask = regime_text.str.contains("warmup|暖機", case=False, na=False)
    bull_mask = regime_text.str.contains("多|漲", na=False)
    bear_mask = regime_text.str.contains("空|跌", na=False)
    range_mask = regime_text.str.contains("盤整|中性", na=False)

    bull_mask = bull_mask & (~warmup_mask)
    bear_mask = bear_mask & (~warmup_mask)
    range_mask = range_mask & (~warmup_mask)

    other_mask = ~(bull_mask | bear_mask | range_mask | warmup_mask)
    range_mask = range_mask | other_mask

    return bull_mask, bear_mask, range_mask, warmup_mask


def align_weekly_regime_to_weekly_index(
    weekly_price_df: pd.DataFrame,
    state_df: pd.DataFrame,
    regime_col: str,
) -> pd.Series:
    """
    把 daily-aligned 的 weekly regime，轉成 weekly index 上的一份 label。
    對每個週K日期，抓 state_df 截至當天最後一筆可用值。
    """
    labels = []
    for dt in weekly_price_df.index:
        sub = state_df.loc[state_df.index <= dt]
        if sub.empty:
            labels.append("warmup")
        else:
            labels.append(sub[regime_col].iloc[-1])
    return pd.Series(labels, index=weekly_price_df.index)


def build_regime_colored_chart(
    price_df: pd.DataFrame,
    regime_text: pd.Series,
    ticker: str,
    title_prefix: str,
):
    regime_text = regime_text.reindex(price_df.index).astype(str)

    bull_mask, bear_mask, range_mask, warmup_mask = classify_regime_masks(regime_text)

    fig = go.Figure()

    def add_regime_candles(mask, name, color):
        sub = price_df.loc[mask].copy()
        if sub.empty:
            return

        fig.add_trace(
            go.Candlestick(
                x=sub.index,
                open=sub["Open"],
                high=sub["High"],
                low=sub["Low"],
                close=sub["Close"],
                name=name,
                increasing_line_color=color,
                decreasing_line_color=color,
                increasing_fillcolor=color,
                decreasing_fillcolor=color,
                opacity=0.95,
                whiskerwidth=0.3,
                showlegend=True,
            )
        )

    add_regime_candles(bull_mask, "Bull Regime（偏多）", "#60a5fa")
    add_regime_candles(bear_mask, "Bear Regime（偏空）", "#fca5a5")
    add_regime_candles(range_mask, "Range Regime（盤整）", "#fbbf24")
    add_regime_candles(warmup_mask, "Warmup（暖機）", "#94a3b8")

    fig.update_layout(
        title=f"{ticker} {title_prefix} Structure Chart（市場結構圖）",
        template="plotly_dark",
        height=560,
        margin=dict(l=20, r=20, t=70, b=20),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1.0,
            xanchor="left",
            x=1.01,
        ),
        dragmode="zoom",
        xaxis_rangeslider_visible=False,
    )

    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(title_text="Price（價格）", showgrid=True)

    return fig


def build_fast_event_chart(
    state_df: pd.DataFrame,
    ticker: str,
    selected_event_types: list[str],
) -> go.Figure:
    df = state_df.copy()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name="Close（收盤價）",
            line=dict(width=2, color="#8ab4f8"),
        )
    )

    if {"fast_event_type", "fast_event_phase"}.issubset(df.columns):
        trigger_df = df[
            df["fast_event_phase"].astype(str).eq("trigger")
            & df["fast_event_type"].astype(str).isin(selected_event_types)
        ].copy()

        event_style = {
            "volatility_shock": {"color": "#86efac", "label": "Volatility Shock（波動衝擊）"},
            "structural_break": {"color": "#ffffff", "label": "Structural Break（結構破壞）"},
            "upward_burst": {"color": "#60a5fa", "label": "Upward Burst（向上爆發）"},
            "downward_burst": {"color": "#fca5a5", "label": "Downward Burst（向下爆發）"},
        }

        for event_type, style in event_style.items():
            sub = trigger_df[trigger_df["fast_event_type"].astype(str) == event_type]
            if sub.empty:
                continue

            fig.add_trace(
                go.Scatter(
                    x=sub.index,
                    y=sub["Close"],
                    mode="markers",
                    name=style["label"],
                    marker=dict(
                        size=9,
                        color=style["color"],
                        symbol="x",
                        line=dict(width=1.5, color=style["color"]),
                    ),
                    hovertemplate="%{x}<br>" + style["label"] + "<extra></extra>",
                )
            )

    fig.update_layout(
        title=f"{ticker} Fast Event Explorer（快層事件檢視圖）",
        template="plotly_dark",
        height=460,
        margin=dict(l=20, r=20, t=70, b=20),
        dragmode="zoom",
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1.0,
            xanchor="left",
            x=1.01,
        ),
    )

    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(title_text="Price（價格）", showgrid=True)

    return fig