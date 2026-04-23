import numpy as np
import pandas as pd


def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    out = a.astype(float) / b.astype(float)
    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def _clip_0_1(series: pd.Series) -> pd.Series:
    return series.clip(lower=0.0, upper=1.0)


def _detect_pivot_low(low: pd.Series, swing_window: int) -> pd.Series:
    """
    pivot low 定義：
    某根 low 比前後各 swing_window 根都低
    """
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
    """
    pivot high 定義：
    某根 high 比前後各 swing_window 根都高
    """
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


def build_breakout_features(
    close: pd.Series,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
    entry_window: int = 20,
    trend_ma_window: int = 50,
    use_trend_filter: bool = True,
    swing_window: int = 2,
) -> pd.DataFrame:
    """
    新版 breakout 哲學：
    1. 進場很簡單：突破前 N 根高低點
    2. 可選擇只保留很輕的趨勢濾網
    3. 出場不是固定停利停損，而是用最近 swing 結構破壞
    """
    df = pd.DataFrame(index=close.index)
    df["close"] = close.astype(float)

    # 若沒提供 high / low，就退化成用 close
    if high is None:
        df["high"] = df["close"]
    else:
        df["high"] = high.astype(float).reindex(df.index)

    if low is None:
        df["low"] = df["close"]
    else:
        df["low"] = low.astype(float).reindex(df.index)

    # =====================================================
    # 1. 基本突破結構
    # =====================================================
    df["entry_high"] = df["high"].rolling(entry_window).max().shift(1)
    df["entry_low"] = df["low"].rolling(entry_window).min().shift(1)

    # =====================================================
    # 2. 輕量趨勢濾網
    # =====================================================
    df["trend_ma"] = df["close"].rolling(trend_ma_window).mean()

    if use_trend_filter:
        df["trend_bias_long"] = (df["close"] > df["trend_ma"]).fillna(False)
        df["trend_bias_short"] = (df["close"] < df["trend_ma"]).fillna(False)
    else:
        df["trend_bias_long"] = True
        df["trend_bias_short"] = True

    # =====================================================
    # 3. 突破條件
    # =====================================================
    df["trigger_long"] = (
        (df["close"] > df["entry_high"])
        & df["trend_bias_long"]
    ).fillna(False)

    df["trigger_short"] = (
        (df["close"] < df["entry_low"])
        & df["trend_bias_short"]
    ).fillna(False)

    # =====================================================
    # 4. Swing 結構偵測
    # =====================================================
    df["pivot_low"] = _detect_pivot_low(df["low"], swing_window=swing_window)
    df["pivot_high"] = _detect_pivot_high(df["high"], swing_window=swing_window)

    # 最近確認 swing low / high
    # 注意：pivot 本身需要未來 bars 才能確認，所以這本來就會有自然延遲
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
    # 6. Strategy score（先保留給 engine 當參考）
    # 這裡不再當主角，只提供一個簡單品質分數
    # =====================================================
    breakout_dist_long = _safe_div(df["close"] - df["entry_high"], df["entry_high"]).clip(lower=0.0)
    breakout_dist_short = _safe_div(df["entry_low"] - df["close"], df["entry_low"]).clip(lower=0.0)

    df["strategy_score_long"] = (
        100.0 * _clip_0_1(breakout_dist_long / 0.05)
    ).fillna(0.0)

    df["strategy_score_short"] = (
        100.0 * _clip_0_1(breakout_dist_short / 0.05)
    ).fillna(0.0)

    return df


def build_trend_breakout_signals(
    close: pd.Series,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
    entry_window: int = 20,
    trend_ma_window: int = 50,
    use_trend_filter: bool = True,
    swing_window: int = 2,
) -> pd.DataFrame:
    df = build_breakout_features(
        close=close,
        high=high,
        low=low,
        entry_window=entry_window,
        trend_ma_window=trend_ma_window,
        use_trend_filter=use_trend_filter,
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


def generate_breakout_signal(
    close: pd.Series,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
    entry_window: int = 10,
    trend_ma_window: int = 20,
    use_trend_filter: bool = False,
    swing_window: int = 1,
) -> pd.Series:
    df = build_trend_breakout_signals(
        close=close,
        high=high,
        low=low,
        entry_window=entry_window,
        trend_ma_window=trend_ma_window,
        use_trend_filter=use_trend_filter,
        swing_window=swing_window,
    )
    return df["base_signal"]