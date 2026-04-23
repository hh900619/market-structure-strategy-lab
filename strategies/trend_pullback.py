import numpy as np
import pandas as pd


def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    out = a.astype(float) / b.astype(float)
    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def _clip_0_1(series: pd.Series) -> pd.Series:
    return series.clip(lower=0.0, upper=1.0)


def _detect_pivot_low(low: pd.Series, swing_window: int) -> pd.Series:
    out = pd.Series(False, index=low.index)

    if swing_window < 1:
        return out

    for i in range(swing_window, len(low) - swing_window):
        center = low.iloc[i]
        left = low.iloc[i - swing_window:i]
        right = low.iloc[i + 1:i + 1 + swing_window]

        if pd.isna(center) or left.isna().any() or right.isna().any():
            continue

        if center < left.min() and center < right.min():
            out.iloc[i] = True

    return out


def _detect_pivot_high(high: pd.Series, swing_window: int) -> pd.Series:
    out = pd.Series(False, index=high.index)

    if swing_window < 1:
        return out

    for i in range(swing_window, len(high) - swing_window):
        center = high.iloc[i]
        left = high.iloc[i - swing_window:i]
        right = high.iloc[i + 1:i + 1 + swing_window]

        if pd.isna(center) or left.isna().any() or right.isna().any():
            continue

        if center > left.max() and center > right.max():
            out.iloc[i] = True

    return out


def build_pullback_features(
    close: pd.Series,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
    trend_ma_window: int = 20,
    pullback_ma_window: int = 10,
    pullback_lookback: int = 8,
    confirm_window: int = 3,
    touch_buffer: float = 0.003,
    swing_window: int = 1,
) -> pd.DataFrame:
    """
    pullback 哲學：
    1. 先有順勢背景
    2. 中途出現回踩 / 反彈
    3. 回踩後重新恢復原方向才進場
    4. 出場仍然用 swing 結構破壞
    """
    df = pd.DataFrame(index=close.index)
    df["close"] = close.astype(float)

    if high is None:
        df["high"] = df["close"]
    else:
        df["high"] = high.astype(float).reindex(df.index)

    if low is None:
        df["low"] = df["close"]
    else:
        df["low"] = low.astype(float).reindex(df.index)

    # =====================================================
    # 1. 趨勢背景
    # =====================================================
    df["trend_ma"] = df["close"].rolling(trend_ma_window).mean()
    df["pullback_ma"] = df["close"].rolling(pullback_ma_window).mean()

    df["trend_ma_slope"] = df["trend_ma"].diff()

    df["trend_bias_long"] = (
        (df["close"] > df["trend_ma"])
        & (df["trend_ma_slope"] > 0)
    ).fillna(False)

    df["trend_bias_short"] = (
        (df["close"] < df["trend_ma"])
        & (df["trend_ma_slope"] < 0)
    ).fillna(False)

    # =====================================================
    # 2. 回踩 / 反彈偵測
    # long: 價格回踩到 pullback_ma 附近
    # short: 價格反彈到 pullback_ma 附近
    # =====================================================
    df["long_touch_pullback"] = (
        (df["low"] <= df["pullback_ma"] * (1.0 + touch_buffer))
        & df["trend_bias_long"]
    ).fillna(False)

    df["short_touch_pullback"] = (
        (df["high"] >= df["pullback_ma"] * (1.0 - touch_buffer))
        & df["trend_bias_short"]
    ).fillna(False)

    df["recent_long_pullback"] = (
        df["long_touch_pullback"]
        .rolling(pullback_lookback, min_periods=1)
        .max()
        .fillna(0)
        .astype(bool)
    )

    df["recent_short_pullback"] = (
        df["short_touch_pullback"]
        .rolling(pullback_lookback, min_periods=1)
        .max()
        .fillna(0)
        .astype(bool)
    )

    # =====================================================
    # 3. 回踩後恢復原方向
    # 用短週期 reclaim breakout 來當 trigger
    # breakout 是破大區間
    # pullback 是破回踩後的小區間
    # =====================================================
    df["reclaim_high"] = df["high"].rolling(confirm_window).max().shift(1)
    df["reclaim_low"] = df["low"].rolling(confirm_window).min().shift(1)

    df["trigger_long"] = (
        df["recent_long_pullback"]
        & df["trend_bias_long"]
        & (df["close"] > df["reclaim_high"])
    ).fillna(False)

    df["trigger_short"] = (
        df["recent_short_pullback"]
        & df["trend_bias_short"]
        & (df["close"] < df["reclaim_low"])
    ).fillna(False)

    # =====================================================
    # 4. Swing 結構偵測
    # =====================================================
    df["pivot_low"] = _detect_pivot_low(df["low"], swing_window=swing_window)
    df["pivot_high"] = _detect_pivot_high(df["high"], swing_window=swing_window)

    df["confirmed_swing_low"] = np.where(df["pivot_low"], df["low"], np.nan)
    df["confirmed_swing_high"] = np.where(df["pivot_high"], df["high"], np.nan)

    df["last_swing_low"] = pd.Series(df["confirmed_swing_low"], index=df.index).ffill()
    df["last_swing_high"] = pd.Series(df["confirmed_swing_high"], index=df.index).ffill()

    # =====================================================
    # 5. 結構破壞出場
    # =====================================================
    df["long_exit_trigger"] = (
        (df["close"] < df["last_swing_low"])
        & df["last_swing_low"].notna()
    ).fillna(False)

    df["short_exit_trigger"] = (
        (df["close"] > df["last_swing_high"])
        & df["last_swing_high"].notna()
    ).fillna(False)

    # =====================================================
    # 6. Strategy score（只給 engine 當參考）
    # pullback 的品質來自：
    # - 趨勢一致
    # - 有沒有真的出現 pullback
    # - reclaim 是否有力
    # =====================================================
    reclaim_dist_long = _safe_div(df["close"] - df["reclaim_high"], df["reclaim_high"]).clip(lower=0.0)
    reclaim_dist_short = _safe_div(df["reclaim_low"] - df["close"], df["reclaim_low"]).clip(lower=0.0)

    trend_score_long = df["trend_bias_long"].astype(float)
    trend_score_short = df["trend_bias_short"].astype(float)

    pullback_score_long = df["recent_long_pullback"].astype(float)
    pullback_score_short = df["recent_short_pullback"].astype(float)

    reclaim_score_long = _clip_0_1(reclaim_dist_long / 0.03).fillna(0.0)
    reclaim_score_short = _clip_0_1(reclaim_dist_short / 0.03).fillna(0.0)

    df["strategy_score_long"] = (
        100.0
        * (
            0.40 * trend_score_long
            + 0.25 * pullback_score_long
            + 0.35 * reclaim_score_long
        )
    ).clip(lower=0.0, upper=100.0)

    df["strategy_score_short"] = (
        100.0
        * (
            0.40 * trend_score_short
            + 0.25 * pullback_score_short
            + 0.35 * reclaim_score_short
        )
    ).clip(lower=0.0, upper=100.0)

    return df


def build_trend_pullback_signals(
    close: pd.Series,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
    trend_ma_window: int = 20,
    pullback_ma_window: int = 10,
    pullback_lookback: int = 8,
    confirm_window: int = 3,
    touch_buffer: float = 0.003,
    swing_window: int = 1,
) -> pd.DataFrame:
    df = build_pullback_features(
        close=close,
        high=high,
        low=low,
        trend_ma_window=trend_ma_window,
        pullback_ma_window=pullback_ma_window,
        pullback_lookback=pullback_lookback,
        confirm_window=confirm_window,
        touch_buffer=touch_buffer,
        swing_window=swing_window,
    )

    base_signal = []
    base_pos = 0

    for _, row in df.iterrows():
        if base_pos == 0:
            if bool(row["trigger_long"]):
                base_pos = 1
            elif bool(row["trigger_short"]):
                base_pos = -1

        elif base_pos == 1:
            if bool(row["long_exit_trigger"]):
                base_pos = 0

        elif base_pos == -1:
            if bool(row["short_exit_trigger"]):
                base_pos = 0

        base_signal.append(base_pos)

    df["base_signal"] = pd.Series(base_signal, index=df.index, dtype=float)
    return df


def generate_pullback_signal(
    close: pd.Series,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
    trend_ma_window: int = 20,
    pullback_ma_window: int = 10,
    pullback_lookback: int = 8,
    confirm_window: int = 3,
    touch_buffer: float = 0.003,
    swing_window: int = 1,
) -> pd.Series:
    df = build_trend_pullback_signals(
        close=close,
        high=high,
        low=low,
        trend_ma_window=trend_ma_window,
        pullback_ma_window=pullback_ma_window,
        pullback_lookback=pullback_lookback,
        confirm_window=confirm_window,
        touch_buffer=touch_buffer,
        swing_window=swing_window,
    )
    return df["base_signal"]