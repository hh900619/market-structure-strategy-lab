import numpy as np
import pandas as pd


# =========================================================
# 基本工具
# =========================================================
def _validate_price_df(price_df: pd.DataFrame) -> pd.DataFrame:
    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in required_cols:
        if col not in price_df.columns:
            raise ValueError(f"price_df 缺少必要欄位：{col}")

    df = price_df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df


def _rolling_percentile_rank(series: pd.Series, window: int) -> pd.Series:
    def pct_rank_last(x: pd.Series) -> float:
        s = pd.Series(x).dropna()
        if len(s) == 0:
            return np.nan
        last = s.iloc[-1]
        return float((s <= last).mean())

    return series.rolling(window=window, min_periods=max(10, window // 5)).apply(
        pct_rank_last,
        raw=False,
    )


def _atr_like(price_df: pd.DataFrame, window: int) -> pd.Series:
    high = price_df["High"].astype(float)
    low = price_df["Low"].astype(float)
    close = price_df["Close"].astype(float)
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window).mean()
    return atr


# =========================================================
# Event feature builder
# =========================================================
def build_fast_event_features(price_df: pd.DataFrame) -> pd.DataFrame:
    df = _validate_price_df(price_df)

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)

    ret_1 = close.pct_change(1)
    ret_3 = close.pct_change(3)
    ret_5 = close.pct_change(5)

    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    ma20_gap = (close / ma20) - 1.0
    ma60_gap = (close / ma60) - 1.0

    daily_vol_20 = close.pct_change().rolling(20).std(ddof=0)
    daily_vol_60 = close.pct_change().rolling(60).std(ddof=0)
    vol_ratio = daily_vol_20 / daily_vol_60.replace(0.0, np.nan)

    range_ratio = (high - low) / close.replace(0.0, np.nan)
    range_rank = _rolling_percentile_rank(range_ratio, 126)

    atr20 = _atr_like(df, 20) / close.replace(0.0, np.nan)
    atr_rank = _rolling_percentile_rank(atr20, 126)

    ret3_rank = _rolling_percentile_rank(ret_3, 126)
    ret5_rank = _rolling_percentile_rank(ret_5, 126)
    vol_ratio_rank = _rolling_percentile_rank(vol_ratio, 126)

    out = pd.DataFrame(index=df.index)
    out["ret_1"] = ret_1
    out["ret_3"] = ret_3
    out["ret_5"] = ret_5
    out["ma20_gap"] = ma20_gap
    out["ma60_gap"] = ma60_gap
    out["vol_ratio"] = vol_ratio
    out["range_ratio"] = range_ratio
    out["atr20"] = atr20

    # ranks
    out["ret3_rank"] = ret3_rank
    out["ret5_rank"] = ret5_rank
    out["vol_ratio_rank"] = vol_ratio_rank
    out["range_rank"] = range_rank
    out["atr_rank"] = atr_rank

    return out


# =========================================================
# Event type classification
# =========================================================
def classify_fast_event_type(feature_df: pd.DataFrame) -> pd.DataFrame:
    """
    第一版 fast event type：
    - none
    - upward_burst
    - downward_burst
    - volatility_shock
    - structural_break

    優先級：
    structural_break > downward/upward_burst > volatility_shock > none
    """
    df = feature_df.copy()

    required_cols = [
        "ret3_rank",
        "ret5_rank",
        "vol_ratio_rank",
        "range_rank",
        "atr_rank",
        "ma20_gap",
        "ma60_gap",
    ]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"feature_df 缺少必要欄位：{col}")

    event_type = pd.Series("none", index=df.index, dtype=object)

    upward_burst_mask = (
        (df["ret3_rank"] >= 0.85)
        & (df["ret5_rank"] >= 0.80)
        & (df["ma20_gap"] > 0)
    )

    downward_burst_mask = (
        (df["ret3_rank"] <= 0.15)
        & (df["ret5_rank"] <= 0.20)
        & (df["ma20_gap"] < 0)
    )

    volatility_shock_mask = (
        (df["vol_ratio_rank"] >= 0.85)
        | (df["range_rank"] >= 0.90)
        | (df["atr_rank"] >= 0.90)
    )

    structural_break_mask = (
        (df["ret3_rank"] <= 0.10)
        & (df["ma20_gap"] < -0.03)
        & (df["ma60_gap"] < -0.05)
    )

    event_type[volatility_shock_mask] = "volatility_shock"
    event_type[upward_burst_mask] = "upward_burst"
    event_type[downward_burst_mask] = "downward_burst"
    event_type[structural_break_mask] = "structural_break"

    df["fast_event_type"] = event_type
    return df


# =========================================================
# Event phase classification
# =========================================================
def classify_fast_event_phase(
    event_df: pd.DataFrame,
    decay_bars: int = 2,
) -> pd.DataFrame:
    """
    phase:
    - trigger: 事件剛出現
    - active: 事件連續持續
    - decay: 事件剛結束後的短暫消退期

    規則：
    1. event_type != none 且前一根不是同類型 -> trigger
    2. event_type != none 且前一根是同類型 -> active
    3. event_type == none 時，若前面最近 decay_bars 根內剛結束過事件 -> decay
    """
    df = event_df.copy()

    if "fast_event_type" not in df.columns:
        raise ValueError("event_df 缺少 fast_event_type。")

    event_type = df["fast_event_type"].copy()
    phase = pd.Series(index=df.index, dtype=object)

    prev_type = event_type.shift(1)

    # 事件剛出現
    trigger_mask = (event_type != "none") & (prev_type != event_type)
    phase[trigger_mask] = "trigger"

    # 同事件持續
    active_mask = (event_type != "none") & (prev_type == event_type)
    phase[active_mask] = "active"

    # 事件結束後的 decay 記憶
    last_non_none_idx = None
    last_non_none_type = None
    decay_count = 0

    for idx in event_type.index:
        current_type = event_type.loc[idx]

        if current_type != "none":
            last_non_none_idx = idx
            last_non_none_type = current_type
            decay_count = 0
            continue

        # current_type == none
        if last_non_none_type is not None and decay_count < decay_bars:
            phase.loc[idx] = "decay"
            decay_count += 1
        else:
            phase.loc[idx] = np.nan
            if decay_count >= decay_bars:
                last_non_none_type = None

    df["fast_event_phase"] = phase
    return df


# =========================================================
# Human-readable labels
# =========================================================
FAST_EVENT_TYPE_NAME_MAP = {
    "none": "無事件",
    "upward_burst": "向上爆發",
    "downward_burst": "向下爆發",
    "volatility_shock": "波動衝擊",
    "structural_break": "結構破壞",
}

FAST_EVENT_PHASE_NAME_MAP = {
    "trigger": "觸發",
    "active": "持續",
    "decay": "消退",
}


def build_fast_event_display(event_df: pd.DataFrame) -> pd.DataFrame:
    df = event_df.copy()

    if "fast_event_type" not in df.columns:
        raise ValueError("event_df 缺少 fast_event_type。")
    if "fast_event_phase" not in df.columns:
        raise ValueError("event_df 缺少 fast_event_phase。")

    df["fast_event_type_name"] = df["fast_event_type"].map(FAST_EVENT_TYPE_NAME_MAP)
    df["fast_event_phase_name"] = df["fast_event_phase"].map(FAST_EVENT_PHASE_NAME_MAP)

    display = []
    for etype, ephase, type_name, phase_name in zip(
        df["fast_event_type"],
        df["fast_event_phase"],
        df["fast_event_type_name"],
        df["fast_event_phase_name"],
    ):
        if etype == "none":
            display.append("無事件")
        elif pd.isna(ephase):
            display.append(type_name)
        else:
            display.append(f"{type_name}｜{phase_name}")

    df["fast_event_display"] = display
    return df


# =========================================================
# Tactical hint layer
# =========================================================
def build_fast_tactical_hints(event_df: pd.DataFrame) -> pd.DataFrame:
    df = event_df.copy()

    if "fast_event_type" not in df.columns:
        raise ValueError("event_df 缺少 fast_event_type。")

    descriptions = []
    entry_hints = []
    counter_hints = []
    size_hints = []
    confidence_hints = []

    for event_type in df["fast_event_type"]:
        if event_type == "upward_burst":
            descriptions.append("短期向上推進突然變強，逆勢做空風險提高，順勢多方訊號相對有利。")
            entry_hints.append("正常或偏正向")
            counter_hints.append("逆勢做空風險提高")
            size_hints.append("維持")
            confidence_hints.append("維持")

        elif event_type == "downward_burst":
            descriptions.append("短期向下推進突然變強，逆勢做多風險提高，多頭訊號短期可信度下降。")
            entry_hints.append("正常或偏保守")
            counter_hints.append("逆勢做多風險提高")
            size_hints.append("小幅降低")
            confidence_hints.append("小幅降低")

        elif event_type == "volatility_shock":
            descriptions.append("短期波動突然粗化，假訊號與洗盤風險上升，regime 可讀性下降。")
            entry_hints.append("保守")
            counter_hints.append("雙邊都保守")
            size_hints.append("小幅降低")
            confidence_hints.append("降低")

        elif event_type == "structural_break":
            descriptions.append("原有結構邏輯被打斷，市場可能進入重估或切換狀態，短期內應顯著提高警覺。")
            entry_hints.append("明顯保守")
            counter_hints.append("雙邊都更保守")
            size_hints.append("中度降低")
            confidence_hints.append("顯著降低")

        else:
            descriptions.append("目前沒有明確短期事件，回到 slow 與 weekly 主導，不額外加入 fast 風險修飾。")
            entry_hints.append("正常")
            counter_hints.append("正常")
            size_hints.append("維持")
            confidence_hints.append("維持")

    df["fast_event_description"] = descriptions
    df["fast_entry_hint"] = entry_hints
    df["fast_counter_trend_hint"] = counter_hints
    df["fast_size_hint"] = size_hints
    df["fast_confidence_hint"] = confidence_hints

    return df


# =========================================================
# Full Builder
# =========================================================
def build_fast_regime_full_state(price_df: pd.DataFrame) -> pd.DataFrame:
    feat_df = build_fast_event_features(price_df)
    type_df = classify_fast_event_type(feat_df)
    phase_df = classify_fast_event_phase(type_df)
    display_df = build_fast_event_display(phase_df)
    hint_df = build_fast_tactical_hints(display_df)
    return hint_df