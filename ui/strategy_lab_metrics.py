import numpy as np
import pandas as pd


# =========================================================
# Basic helpers
# =========================================================
def safe_pct_change(series: pd.Series) -> pd.Series:
    return series.astype(float).pct_change().fillna(0.0)


def filter_series_by_date(
    series: pd.Series,
    start_date=None,
    end_date=None,
) -> pd.Series:
    out = series.copy()
    if start_date is not None:
        out = out[out.index >= pd.to_datetime(start_date)]
    if end_date is not None:
        out = out[out.index <= pd.to_datetime(end_date)]
    return out


def align_signal_and_close(
    signal: pd.Series,
    close: pd.Series,
    start_date=None,
    end_date=None,
) -> tuple[pd.Series, pd.Series]:
    close_aligned = close.astype(float).copy()
    signal_aligned = signal.reindex(close_aligned.index).fillna(0.0).astype(float)

    if start_date is not None:
        start_ts = pd.to_datetime(start_date)
        close_aligned = close_aligned[close_aligned.index >= start_ts]
        signal_aligned = signal_aligned[signal_aligned.index >= start_ts]

    if end_date is not None:
        end_ts = pd.to_datetime(end_date)
        close_aligned = close_aligned[close_aligned.index <= end_ts]
        signal_aligned = signal_aligned[signal_aligned.index <= end_ts]

    common_index = close_aligned.index.intersection(signal_aligned.index)
    return signal_aligned.loc[common_index], close_aligned.loc[common_index]


# =========================================================
# Equity curve
# =========================================================
def build_equity_curve(signal: pd.Series, close: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame(index=close.index)
    df["close"] = close.astype(float)
    df["ret"] = safe_pct_change(df["close"])
    df["signal"] = signal.astype(float).fillna(0.0)
    df["strategy_ret"] = df["signal"].shift(1).fillna(0.0) * df["ret"]
    df["equity"] = (1.0 + df["strategy_ret"]).cumprod()
    return df


# =========================================================
# Risk / return metrics
# =========================================================
def max_drawdown(equity: pd.Series) -> float:
    if len(equity) == 0:
        return 0.0
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    return float(dd.min())


def annualized_return(strategy_ret: pd.Series, bars_per_year: int = 252) -> float:
    n = len(strategy_ret)
    if n == 0:
        return 0.0

    total = float((1.0 + strategy_ret).prod())
    if total <= 0:
        return -1.0

    return total ** (bars_per_year / n) - 1.0


def annualized_vol(strategy_ret: pd.Series, bars_per_year: int = 252) -> float:
    if len(strategy_ret) == 0:
        return 0.0
    vol = float(strategy_ret.std())
    return vol * np.sqrt(bars_per_year)


def sharpe(strategy_ret: pd.Series, bars_per_year: int = 252) -> float:
    vol = annualized_vol(strategy_ret, bars_per_year=bars_per_year)
    if vol == 0:
        return 0.0
    ann_ret = annualized_return(strategy_ret, bars_per_year=bars_per_year)
    return ann_ret / vol


# =========================================================
# Trade extraction
# =========================================================
def extract_trades(signal: pd.Series, close: pd.Series) -> pd.DataFrame:
    """
    將持倉序列轉成逐筆交易明細。
    規則：
    - 0 -> 1 / -1 視為進場
    - 1 / -1 -> 0 視為出場
    - 1 -> -1 或 -1 -> 1 視為同一天反手：
      先平舊倉，再開新倉
    報酬用 close-to-close 百分比估算。
    """
    signal = signal.reindex(close.index).fillna(0.0).astype(float)
    close = close.astype(float)

    trades = []
    current_pos = 0.0
    entry_date = None
    entry_price = None
    entry_idx = None

    idx_list = list(close.index)

    for i, dt in enumerate(idx_list):
        sig = float(signal.loc[dt])
        px = float(close.loc[dt])

        # 無持倉 -> 開倉
        if current_pos == 0.0 and sig != 0.0:
            current_pos = sig
            entry_date = dt
            entry_price = px
            entry_idx = i
            continue

        # 有持倉 -> 平倉
        if current_pos != 0.0 and sig == 0.0:
            side = "Long" if current_pos > 0 else "Short"
            if current_pos > 0:
                trade_ret = px / entry_price - 1.0
            else:
                trade_ret = entry_price / px - 1.0

            trades.append(
                {
                    "entry_date": entry_date,
                    "exit_date": dt,
                    "side": side,
                    "entry_price": entry_price,
                    "exit_price": px,
                    "return_pct": trade_ret,
                    "holding_bars": i - entry_idx if entry_idx is not None else np.nan,
                    "is_win": trade_ret > 0,
                }
            )

            current_pos = 0.0
            entry_date = None
            entry_price = None
            entry_idx = None
            continue

        # 有持倉 -> 反手
        if current_pos != 0.0 and sig != 0.0 and sig != current_pos:
            old_side = "Long" if current_pos > 0 else "Short"
            if current_pos > 0:
                old_ret = px / entry_price - 1.0
            else:
                old_ret = entry_price / px - 1.0

            trades.append(
                {
                    "entry_date": entry_date,
                    "exit_date": dt,
                    "side": old_side,
                    "entry_price": entry_price,
                    "exit_price": px,
                    "return_pct": old_ret,
                    "holding_bars": i - entry_idx if entry_idx is not None else np.nan,
                    "is_win": old_ret > 0,
                }
            )

            current_pos = sig
            entry_date = dt
            entry_price = px
            entry_idx = i

    # 若最後仍有持倉，這裡先不強制平倉
    # 讓回測摘要只統計已完成交易
    trades_df = pd.DataFrame(trades)

    if not trades_df.empty:
        trades_df["entry_date"] = pd.to_datetime(trades_df["entry_date"])
        trades_df["exit_date"] = pd.to_datetime(trades_df["exit_date"])

    return trades_df


# =========================================================
# Summary
# =========================================================
def build_perf_summary(
    signal: pd.Series,
    close: pd.Series,
    bars_per_year: int = 252,
    start_date=None,
    end_date=None,
) -> dict:
    signal_aligned, close_aligned = align_signal_and_close(
        signal=signal,
        close=close,
        start_date=start_date,
        end_date=end_date,
    )

    eq = build_equity_curve(signal_aligned, close_aligned)
    trades_df = extract_trades(signal_aligned, close_aligned)

    total_return = float(eq["equity"].iloc[-1] - 1.0) if not eq.empty else 0.0
    ann_return = annualized_return(eq["strategy_ret"], bars_per_year=bars_per_year)
    ann_vol = annualized_vol(eq["strategy_ret"], bars_per_year=bars_per_year)
    sharpe_value = sharpe(eq["strategy_ret"], bars_per_year=bars_per_year)
    max_dd_value = max_drawdown(eq["equity"])
    exposure = float((signal_aligned != 0).mean()) if len(signal_aligned) > 0 else 0.0

    # 使用者更容易懂的統計
    entry_count = int(((signal_aligned.shift(1).fillna(0.0) == 0.0) & (signal_aligned != 0.0)).sum())
    exit_count = int(((signal_aligned.shift(1).fillna(0.0) != 0.0) & (signal_aligned == 0.0)).sum())
    trade_count = int(len(trades_df))

    if not trades_df.empty:
        win_rate = float(trades_df["is_win"].mean())
        avg_trade_return = float(trades_df["return_pct"].mean())
        median_trade_return = float(trades_df["return_pct"].median())
        best_trade = float(trades_df["return_pct"].max())
        worst_trade = float(trades_df["return_pct"].min())
        avg_holding_bars = float(trades_df["holding_bars"].mean())
    else:
        win_rate = 0.0
        avg_trade_return = 0.0
        median_trade_return = 0.0
        best_trade = 0.0
        worst_trade = 0.0
        avg_holding_bars = 0.0

    return {
        "start_date": eq.index.min() if not eq.empty else None,
        "end_date": eq.index.max() if not eq.empty else None,
        "bars": int(len(eq)),
        "equity_df": eq,
        "trades_df": trades_df,
        "total_return": total_return,
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "sharpe": sharpe_value,
        "max_dd": max_dd_value,
        "exposure": exposure,
        "entry_count": entry_count,
        "exit_count": exit_count,
        "trade_count": trade_count,
        "win_rate": win_rate,
        "avg_trade_return": avg_trade_return,
        "median_trade_return": median_trade_return,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "avg_holding_bars": avg_holding_bars,
    }