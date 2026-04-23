import numpy as np
import pandas as pd
import plotly.graph_objects as go


# =========================================================
# Backtest Utilities
# =========================================================
def compute_equity_from_exposure(
    close: pd.Series,
    exposure: pd.Series,
    cost_bps: float = 5.0,
) -> pd.Series:
    """
    根據 exposure（-1, 0, 1）計算權益曲線。
    exposure 視為「當根收盤後持有到下一根」，
    因此使用 exposure.shift(1) * return。
    """
    close = pd.Series(close).astype(float).copy()
    exposure = pd.Series(exposure).reindex(close.index).fillna(0.0).astype(float)

    ret = close.pct_change().fillna(0.0)

    prev_exposure = exposure.shift(1).fillna(0.0)
    strategy_ret = prev_exposure * ret

    # turnover 成本
    turnover = exposure.diff().abs().fillna(exposure.abs())
    cost = turnover * (cost_bps / 10000.0)

    net_ret = strategy_ret - cost
    equity = (1.0 + net_ret).cumprod()

    return equity


def stats_from_equity(equity: pd.Series, annual_factor: int = 252) -> dict:
    equity = pd.Series(equity).astype(float).dropna()

    if len(equity) < 2:
        return {
            "total_return": 0.0,
            "annual_return": 0.0,
            "annual_vol": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
        }

    ret = equity.pct_change().dropna()

    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0

    n = len(ret)
    if n > 0:
        annual_return = equity.iloc[-1] ** (annual_factor / max(n, 1)) - 1.0
    else:
        annual_return = 0.0

    annual_vol = ret.std() * np.sqrt(annual_factor) if len(ret) > 1 else 0.0
    sharpe = annual_return / annual_vol if annual_vol and annual_vol > 0 else 0.0

    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_drawdown = drawdown.min() if len(drawdown) else 0.0

    return {
        "total_return": float(total_return),
        "annual_return": float(annual_return),
        "annual_vol": float(annual_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_drawdown),
    }


# =========================================================
# Signal Marker Helpers
# =========================================================
def _extract_trade_markers(signal: pd.Series) -> dict:
    """
    從 signal（-1,0,1）抽出：
    - long entry
    - long exit
    - short entry
    - short exit
    """
    signal = pd.Series(signal).fillna(0.0).astype(float)
    prev = signal.shift(1).fillna(0.0)

    long_entry = (signal == 1) & (prev != 1)
    long_exit = (prev == 1) & (signal != 1)

    short_entry = (signal == -1) & (prev != -1)
    short_exit = (prev == -1) & (signal != -1)

    return {
        "long_entry": long_entry,
        "long_exit": long_exit,
        "short_entry": short_entry,
        "short_exit": short_exit,
    }


def _marker_y_positions(price_df: pd.DataFrame, pad_ratio: float = 0.012) -> dict:
    """
    為了讓 marker 不要壓在 K 棒本體上，做一點上下偏移。
    """
    high = price_df["High"].astype(float)
    low = price_df["Low"].astype(float)
    close = price_df["Close"].astype(float)

    price_range = (high - low).replace(0, np.nan)
    fallback = close.abs() * 0.01
    pad = (price_range * pad_ratio).fillna(fallback).fillna(1.0)

    return {
        "above": high + pad,
        "below": low - pad,
    }


# =========================================================
# Chart Builders
# =========================================================
def build_equity_compare_chart(
    base_equity: pd.Series,
    engine_equity: pd.Series,
    title: str = "Equity Curve Compare",
) -> go.Figure:
    base_equity = pd.Series(base_equity).dropna().astype(float)
    engine_equity = pd.Series(engine_equity).dropna().astype(float)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=base_equity.index,
            y=base_equity.values,
            mode="lines",
            name="Base Equity",
            line=dict(width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=engine_equity.index,
            y=engine_equity.values,
            mode="lines",
            name="Engine Equity",
            line=dict(width=2),
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=430,
        margin=dict(l=20, r=20, t=70, b=20),
        xaxis_title="Date",
        yaxis_title="Equity",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_xaxes(rangeslider_visible=True, showgrid=True)
    fig.update_yaxes(showgrid=True)

    return fig


def build_trade_marker_candlestick(
    price_df: pd.DataFrame,
    signal: pd.Series,
    title: str = "K-Line + Trade Markers",
) -> go.Figure:
    """
    price_df 需要包含:
    - Open
    - High
    - Low
    - Close

    signal:
    -1 / 0 / 1
    """
    df = price_df.copy()
    sig = pd.Series(signal).reindex(df.index).fillna(0.0).astype(float)

    markers = _extract_trade_markers(sig)
    y_pos = _marker_y_positions(df)

    fig = go.Figure()

    # K 線主體
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K-Line",
            increasing_line_color="#8ef0b5",
            decreasing_line_color="#f2b8b5",
            increasing_fillcolor="#8ef0b5",
            decreasing_fillcolor="#f2b8b5",
            opacity=0.9,
        )
    )

    # Long Entry
    if markers["long_entry"].any():
        fig.add_trace(
            go.Scatter(
                x=df.index[markers["long_entry"]],
                y=y_pos["below"][markers["long_entry"]],
                mode="markers",
                name="Long Entry",
                marker=dict(
                    size=9,
                    symbol="triangle-up",
                    color="#6ea8ff",
                    line=dict(width=1),
                ),
            )
        )

    # Long Exit
    if markers["long_exit"].any():
        fig.add_trace(
            go.Scatter(
                x=df.index[markers["long_exit"]],
                y=y_pos["above"][markers["long_exit"]],
                mode="markers",
                name="Long Exit",
                marker=dict(
                    size=10,
                    symbol="x",
                    color="#f7d154",
                    line=dict(width=1.5),
                ),
            )
        )

    # Short Entry
    if markers["short_entry"].any():
        fig.add_trace(
            go.Scatter(
                x=df.index[markers["short_entry"]],
                y=y_pos["above"][markers["short_entry"]],
                mode="markers",
                name="Short Entry",
                marker=dict(
                    size=9,
                    symbol="triangle-down",
                    color="#ff7b72",
                    line=dict(width=1),
                ),
            )
        )

    # Short Exit
    if markers["short_exit"].any():
        fig.add_trace(
            go.Scatter(
                x=df.index[markers["short_exit"]],
                y=y_pos["below"][markers["short_exit"]],
                mode="markers",
                name="Short Exit",
                marker=dict(
                    size=10,
                    symbol="diamond",
                    color="#8ef0b5",
                    line=dict(width=1.5),
                ),
            )
        )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=520,
        margin=dict(l=20, r=20, t=70, b=20),
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=True,
        legend=dict(orientation="v"),
    )

    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True)

    return fig