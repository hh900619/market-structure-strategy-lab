import pandas as pd
import plotly.graph_objects as go


# =========================================================
# Human-readable labels
# =========================================================
ENGINE_REASON_LABELS = {
    "flat": "當下沒有持倉或沒有新訊號",
    "long_entry_allowed": "市場背景支持做多，Engine 允許進場",
    "short_entry_allowed": "市場背景支持做空，Engine 允許進場",
    "long_entry_cautious": "可做多，但市場背景沒有那麼乾淨，建議保守",
    "short_entry_cautious": "可做空，但市場背景沒有那麼乾淨，建議保守",
    "long_entry_blocked": "目前市場背景不支持做多，所以這筆原始進場被擋掉",
    "short_entry_blocked": "目前市場背景不支持做空，所以這筆原始進場被擋掉",
    "long_hold_ok": "市場背景仍支持持有多單",
    "short_hold_ok": "市場背景仍支持持有空單",
    "long_hold_reduce": "多單可以續抱，但 Engine 認為應降低倉位",
    "short_hold_reduce": "空單可以續抱，但 Engine 認為應降低倉位",
    "long_exit_regime": "市場背景轉弱，Engine 要求多單提早出場",
    "short_exit_regime": "市場背景轉弱，Engine 要求空單提早出場",
}


def explain_engine_reason(reason: str) -> str:
    return ENGINE_REASON_LABELS.get(str(reason), str(reason))


# =========================================================
# Signal event extraction
# =========================================================
def extract_signal_events(price_df: pd.DataFrame, signal: pd.Series) -> pd.DataFrame:
    """
    將 signal 轉成事件表：
    - long_entry
    - short_entry
    - exit
    """
    s = signal.reindex(price_df.index).fillna(0.0).astype(float)
    prev = s.shift(1).fillna(0.0)

    long_entry = (prev <= 0) & (s == 1)
    short_entry = (prev >= 0) & (s == -1)
    exit_signal = (prev != 0) & (s == 0)

    rows = []

    for dt in price_df.index[long_entry]:
        rows.append(
            {
                "date": dt,
                "event": "long_entry",
                "price": float(price_df.loc[dt, "Close"]),
                "signal": 1.0,
                "display_reason": "策略訊號成立，原始策略決定做多進場",
            }
        )

    for dt in price_df.index[short_entry]:
        rows.append(
            {
                "date": dt,
                "event": "short_entry",
                "price": float(price_df.loc[dt, "Close"]),
                "signal": -1.0,
                "display_reason": "策略訊號成立，原始策略決定做空進場",
            }
        )

    for dt in price_df.index[exit_signal]:
        rows.append(
            {
                "date": dt,
                "event": "exit",
                "price": float(price_df.loc[dt, "Close"]),
                "signal": 0.0,
                "display_reason": "策略條件不再成立，原始策略決定出場",
            }
        )

    events_df = pd.DataFrame(rows)
    if not events_df.empty:
        events_df = events_df.sort_values("date").reset_index(drop=True)

    return events_df


# =========================================================
# Trade line builder
# =========================================================
def build_trade_lines(trades_df: pd.DataFrame) -> list[dict]:
    """
    將 trades_df 轉成畫圖用線段資訊。
    return_pct > 0 => 綠線
    return_pct <= 0 => 紅線
    """
    if trades_df is None or trades_df.empty:
        return []

    lines = []
    for _, row in trades_df.iterrows():
        trade_ret = float(row["return_pct"])
        color = "rgba(50,205,50,0.95)" if trade_ret > 0 else "rgba(255,99,71,0.95)"

        lines.append(
            {
                "x": [row["entry_date"], row["exit_date"]],
                "y": [row["entry_price"], row["exit_price"]],
                "color": color,
                "width": 3,
                "side": row["side"],
                "return_pct": trade_ret,
            }
        )

    return lines


# =========================================================
# Equity compare
# =========================================================
def plot_equity_compare(base_perf: dict, eng_perf: dict, title: str = ""):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=base_perf["equity_df"].index,
            y=base_perf["equity_df"]["equity"],
            mode="lines",
            name="原始策略",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=eng_perf["equity_df"].index,
            y=eng_perf["equity_df"]["equity"],
            mode="lines",
            name="加入 Engine 後",
        )
    )

    fig.update_layout(
        title_text=title,
        template="plotly_dark",
        height=320,
        margin=dict(l=20, r=20, t=50, b=30),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        hovermode="x unified",
    )
    return fig


# =========================================================
# Helper: classify exit type
# =========================================================
def build_exit_reason_map(
    price_df: pd.DataFrame,
    base_signal: pd.Series,
    engine_signal: pd.Series | None = None,
    eng_df: pd.DataFrame | None = None,
):
    """
    判斷每個 exit 是：
    - 策略自己出場
    - Engine 提早出場
    """
    s_base = base_signal.reindex(price_df.index).fillna(0.0).astype(float)
    prev_base = s_base.shift(1).fillna(0.0)
    base_exit_mask = (prev_base != 0) & (s_base == 0)

    exit_reason_map = {}

    # base 圖：全部都視為原始策略出場
    if engine_signal is None:
        for dt in price_df.index[base_exit_mask]:
            exit_reason_map[dt] = "原始策略出場，策略條件不再成立"
        return exit_reason_map

    s_eng = engine_signal.reindex(price_df.index).fillna(0.0).astype(float)
    prev_eng = s_eng.shift(1).fillna(0.0)
    eng_exit_mask = (prev_eng != 0) & (s_eng == 0)

    base_exit_dates = set(price_df.index[base_exit_mask])

    for dt in price_df.index[eng_exit_mask]:
        # 如果同一天 base 也 exit，代表是原始策略自己出場
        if dt in base_exit_dates:
            exit_reason_map[dt] = "原始策略出場，策略條件不再成立"
            continue

        # 否則視為 engine 提早出場
        reason = None
        if eng_df is not None and "engine_reason" in eng_df.columns and dt in eng_df.index:
            raw_reason = str(eng_df.loc[dt, "engine_reason"])
            if raw_reason != "flat":
                reason = explain_engine_reason(raw_reason)

        exit_reason_map[dt] = reason or "Engine 判斷目前背景不再適合持有，因此提早出場"

    return exit_reason_map


# =========================================================
# Main trade chart
# =========================================================
def plot_trade_chart(
    price_df: pd.DataFrame,
    signal: pd.Series,
    trades_df: pd.DataFrame | None = None,
    title: str = "",
    blocked_events_df: pd.DataFrame | None = None,
    exit_reason_map: dict | None = None,
):
    """
    類似 MultiCharts 的交易圖：
    - K 線
    - 進場 / 出場 marker
    - 每筆交易盈虧線
    - 可選顯示被擋掉的訊號
    """
    df = price_df.copy()
    sig = signal.reindex(df.index).fillna(0.0).astype(float)
    events_df = extract_signal_events(df, sig)

    fig = go.Figure()

    # -------------------------
    # K bars
    # -------------------------
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
        )
    )

    # -------------------------
    # Trade lines
    # -------------------------
    line_items = build_trade_lines(trades_df)
    for item in line_items:
        fig.add_trace(
            go.Scatter(
                x=item["x"],
                y=item["y"],
                mode="lines",
                name="獲利交易" if item["return_pct"] > 0 else "虧損交易",
                line=dict(color=item["color"], width=item["width"]),
                hovertemplate=(
                    f"方向：{item['side']}<br>"
                    f"交易報酬：{item['return_pct']:.2%}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    # -------------------------
    # Entry / exit markers
    # -------------------------
    if not events_df.empty:
        long_df = events_df[events_df["event"] == "long_entry"].copy()
        short_df = events_df[events_df["event"] == "short_entry"].copy()
        exit_df = events_df[events_df["event"] == "exit"].copy()

        if not long_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=long_df["date"],
                    y=long_df["price"],
                    mode="markers",
                    name="做多進場",
                    marker=dict(symbol="triangle-up", size=11),
                    customdata=long_df[["display_reason"]].values,
                    hovertemplate=(
                        "<b>做多進場</b><br>"
                        "Date=%{x|%b %d, %Y}<br>"
                        "Price=%{y:.2f}<br>"
                        "原因=%{customdata[0]}<extra></extra>"
                    ),
                )
            )

        if not short_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=short_df["date"],
                    y=short_df["price"],
                    mode="markers",
                    name="做空進場",
                    marker=dict(symbol="triangle-down", size=11),
                    customdata=short_df[["display_reason"]].values,
                    hovertemplate=(
                        "<b>做空進場</b><br>"
                        "Date=%{x|%b %d, %Y}<br>"
                        "Price=%{y:.2f}<br>"
                        "原因=%{customdata[0]}<extra></extra>"
                    ),
                )
            )

        if not exit_df.empty:
            if exit_reason_map is None:
                exit_df["display_reason"] = "策略條件不再成立，原始策略決定出場"
            else:
                exit_df["display_reason"] = exit_df["date"].map(exit_reason_map).fillna(
                    "策略條件不再成立，原始策略決定出場"
                )

            fig.add_trace(
                go.Scatter(
                    x=exit_df["date"],
                    y=exit_df["price"],
                    mode="markers",
                    name="出場",
                    marker=dict(symbol="x", size=9),
                    customdata=exit_df[["display_reason"]].values,
                    hovertemplate=(
                        "<b>出場</b><br>"
                        "Date=%{x|%b %d, %Y}<br>"
                        "Price=%{y:.2f}<br>"
                        "原因=%{customdata[0]}<extra></extra>"
                    ),
                )
            )

    # -------------------------
    # Blocked events
    # -------------------------
    if blocked_events_df is not None and not blocked_events_df.empty:
        fig.add_trace(
            go.Scatter(
                x=blocked_events_df["date"],
                y=blocked_events_df["price"],
                mode="markers",
                name="被 Engine 擋掉",
                marker=dict(
                    symbol="circle-open",
                    size=12,
                    line=dict(width=2),
                    opacity=0.85,
                ),
                customdata=blocked_events_df[["display_reason"]].values,
                hovertemplate=(
                    "<b>被 Engine 擋掉</b><br>"
                    "Date=%{x|%b %d, %Y}<br>"
                    "Price=%{y:.2f}<br>"
                    "原因=%{customdata[0]}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title_text=title,
        template="plotly_dark",
        height=620,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.10,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        hovermode="closest",
    )

    fig.update_yaxes(title_text="Price")
    return fig


# =========================================================
# Helper: blocked events from base vs engine
# =========================================================
def build_blocked_events_df(
    price_df: pd.DataFrame,
    base_signal: pd.Series,
    engine_signal: pd.Series,
    eng_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    找出 base 本來想進，但 engine 沒保留的 entry。
    """
    base_events = extract_signal_events(price_df, base_signal)
    engine_events = extract_signal_events(price_df, engine_signal)

    if base_events.empty:
        return pd.DataFrame(columns=["date", "price", "reason", "display_reason"])

    base_entries = base_events[base_events["event"].isin(["long_entry", "short_entry"])].copy()
    engine_entries = engine_events[engine_events["event"].isin(["long_entry", "short_entry"])].copy()

    if engine_entries.empty:
        blocked = base_entries.copy()
    else:
        engine_key = set(zip(engine_entries["date"], engine_entries["event"]))
        blocked = base_entries[
            ~base_entries.apply(lambda r: (r["date"], r["event"]) in engine_key, axis=1)
        ].copy()

    if blocked.empty:
        return pd.DataFrame(columns=["date", "price", "reason", "display_reason"])

    blocked = blocked.rename(columns={"event": "blocked_event", "price": "price"})
    blocked["date"] = blocked["date"]

    if eng_df is not None and "engine_reason" in eng_df.columns:
        blocked["reason"] = blocked["date"].map(eng_df["engine_reason"].to_dict())
    else:
        blocked["reason"] = "blocked"

    blocked["display_reason"] = blocked["reason"].apply(explain_engine_reason)

    return blocked[["date", "price", "reason", "display_reason"]]


# =========================================================
# Dual charts helper
# =========================================================
def plot_dual_trade_charts(
    price_df: pd.DataFrame,
    base_signal: pd.Series,
    engine_signal: pd.Series,
    base_trades_df: pd.DataFrame | None = None,
    engine_trades_df: pd.DataFrame | None = None,
    eng_df: pd.DataFrame | None = None,
):
    blocked_df = build_blocked_events_df(
        price_df=price_df,
        base_signal=base_signal,
        engine_signal=engine_signal,
        eng_df=eng_df,
    )

    base_exit_reason_map = build_exit_reason_map(
        price_df=price_df,
        base_signal=base_signal,
        engine_signal=None,
        eng_df=None,
    )

    engine_exit_reason_map = build_exit_reason_map(
        price_df=price_df,
        base_signal=base_signal,
        engine_signal=engine_signal,
        eng_df=eng_df,
    )

    base_fig = plot_trade_chart(
        price_df=price_df,
        signal=base_signal,
        trades_df=base_trades_df,
        title="原始策略交易圖",
        blocked_events_df=None,
        exit_reason_map=base_exit_reason_map,
    )

    engine_fig = plot_trade_chart(
        price_df=price_df,
        signal=engine_signal,
        trades_df=engine_trades_df,
        title="加入 Engine 後的交易圖",
        blocked_events_df=blocked_df,
        exit_reason_map=engine_exit_reason_map,
    )

    return base_fig, engine_fig