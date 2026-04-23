import numpy as np
import pandas as pd


# =========================================================
# 基本工具
# =========================================================
def _validate_close(close: pd.Series) -> pd.Series:
    if close is None or len(close) == 0:
        raise ValueError("close 為空，無法建立 slow regime。")

    close = close.astype(float).copy()
    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    return close


def _rolling_percentile_rank(series: pd.Series, window: int) -> pd.Series:
    """
    將 series 轉成 rolling percentile rank，輸出範圍約在 0 ~ 1。
    只使用當下以前的資料，不偷看未來。
    """
    if window <= 1:
        raise ValueError("window 必須大於 1。")

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


def _center_percentile_rank(pct_rank: pd.Series) -> pd.Series:
    """
    把 0~1 的 percentile rank 轉成以 0 為中心的範圍，大致為 -0.5 ~ +0.5。
    """
    return pct_rank - 0.5


def _rolling_state_from_score(
    score: pd.Series,
    low_label: str,
    mid_label: str,
    high_label: str,
    window: int = 252,
    q_low: float = 0.30,
    q_high: float = 0.70,
) -> pd.Series:
    """
    將連續 score 用 rolling 分位切成三狀態。
    """
    if score is None or len(score) == 0:
        raise ValueError("score 為空，無法切 state。")

    min_p = min(window, max(3, window // 3))
    rolling_low = score.rolling(window=window, min_periods=min_p).quantile(q_low)
    rolling_high = score.rolling(window=window, min_periods=min_p).quantile(q_high)

    state = pd.Series(index=score.index, dtype=object)
    state[score <= rolling_low] = low_label
    state[(score > rolling_low) & (score < rolling_high)] = mid_label
    state[score >= rolling_high] = high_label

    return state


def _path_efficiency(close: pd.Series, window: int) -> pd.Series:
    """
    路徑效率 = |淨位移| / 總路徑長度
    越高代表越直、越 clean。
    """
    net_move = close.diff(window).abs()
    total_move = close.diff().abs().rolling(window).sum()
    eff = net_move / total_move.replace(0.0, np.nan)
    return eff


def _sign_flip_stability(close: pd.Series, window: int) -> pd.Series:
    """
    先算報酬正負號切換率，再轉成 stability。
    stability 越高，代表越少來回翻轉、越 clean。
    """
    ret = close.pct_change()
    sign = np.sign(ret)

    flip = (sign != sign.shift(1)).astype(float)
    flip = flip.where(sign.notna() & sign.shift(1).notna(), np.nan)

    flip_rate = flip.rolling(window).mean()
    stability = 1.0 - flip_rate
    return stability


def _pullback_resilience(close: pd.Series, window: int) -> pd.Series:
    """
    用 rolling drawdown 的反向概念近似 pullback resilience。
    越接近 1，代表該區間內回撤越不深、韌性越高。
    """
    rolling_max = close.rolling(window).max()
    drawdown = (close / rolling_max) - 1.0
    worst_dd = drawdown.rolling(window).min().abs()
    resilience = 1.0 / (1.0 + worst_dd)
    return resilience


def _atr_like(price_df: pd.DataFrame, window: int) -> pd.Series:
    """
    簡化版 ATR。
    """
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
# Direction Scores
# =========================================================
def build_direction_scores(close: pd.Series, rank_window: int = 252) -> pd.DataFrame:
    close = _validate_close(close)

    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    ma240 = close.rolling(240).mean()

    # raw features
    short_ma_gap = (ma5 / ma20) - 1.0
    short_ma_slope = (ma20 / ma20.shift(5)) - 1.0
    short_price_gap = (close / ma20) - 1.0

    mid_ma_gap = (ma20 / ma60) - 1.0
    mid_ma_slope = (ma60 / ma60.shift(10)) - 1.0
    mid_price_gap = (close / ma60) - 1.0

    long_ma_gap = (ma60 / ma240) - 1.0
    long_ma_slope = (ma240 / ma240.shift(20)) - 1.0
    long_price_gap = (close / ma240) - 1.0

    # percentile rank -> centered
    short_ma_gap_n = _center_percentile_rank(_rolling_percentile_rank(short_ma_gap, rank_window))
    short_ma_slope_n = _center_percentile_rank(_rolling_percentile_rank(short_ma_slope, rank_window))
    short_price_gap_n = _center_percentile_rank(_rolling_percentile_rank(short_price_gap, rank_window))

    mid_ma_gap_n = _center_percentile_rank(_rolling_percentile_rank(mid_ma_gap, rank_window))
    mid_ma_slope_n = _center_percentile_rank(_rolling_percentile_rank(mid_ma_slope, rank_window))
    mid_price_gap_n = _center_percentile_rank(_rolling_percentile_rank(mid_price_gap, rank_window))

    long_ma_gap_n = _center_percentile_rank(_rolling_percentile_rank(long_ma_gap, rank_window))
    long_ma_slope_n = _center_percentile_rank(_rolling_percentile_rank(long_ma_slope, rank_window))
    long_price_gap_n = _center_percentile_rank(_rolling_percentile_rank(long_price_gap, rank_window))

    out = pd.DataFrame(index=close.index)

    out["short_direction_score"] = (
        0.40 * short_ma_gap_n
        + 0.35 * short_ma_slope_n
        + 0.25 * short_price_gap_n
    )

    out["mid_direction_score"] = (
        0.40 * mid_ma_gap_n
        + 0.35 * mid_ma_slope_n
        + 0.25 * mid_price_gap_n
    )

    out["long_direction_score"] = (
        0.40 * long_ma_gap_n
        + 0.35 * long_ma_slope_n
        + 0.25 * long_price_gap_n
    )

    return out


# =========================================================
# Structure Scores
# =========================================================
def build_structure_scores(close: pd.Series, rank_window: int = 252) -> pd.DataFrame:
    close = _validate_close(close)

    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    ma240 = close.rolling(240).mean()

    # short
    short_eff = _path_efficiency(close, 20)
    short_flip = _sign_flip_stability(close, 20)
    short_sep = (ma5 / ma20 - 1.0).abs()

    # mid
    mid_eff = _path_efficiency(close, 60)
    mid_flip = _sign_flip_stability(close, 60)
    mid_sep = (ma20 / ma60 - 1.0).abs()

    # long
    long_eff = _path_efficiency(close, 120)
    long_flip = _sign_flip_stability(close, 120)
    long_sep = (ma60 / ma240 - 1.0).abs()

    short_eff_n = _rolling_percentile_rank(short_eff, rank_window)
    short_flip_n = _rolling_percentile_rank(short_flip, rank_window)
    short_sep_n = _rolling_percentile_rank(short_sep, rank_window)

    mid_eff_n = _rolling_percentile_rank(mid_eff, rank_window)
    mid_flip_n = _rolling_percentile_rank(mid_flip, rank_window)
    mid_sep_n = _rolling_percentile_rank(mid_sep, rank_window)

    long_eff_n = _rolling_percentile_rank(long_eff, rank_window)
    long_flip_n = _rolling_percentile_rank(long_flip, rank_window)
    long_sep_n = _rolling_percentile_rank(long_sep, rank_window)

    out = pd.DataFrame(index=close.index)

    out["short_structure_score"] = (
        0.45 * short_eff_n
        + 0.35 * short_flip_n
        + 0.20 * short_sep_n
    )

    out["mid_structure_score"] = (
        0.45 * mid_eff_n
        + 0.35 * mid_flip_n
        + 0.20 * mid_sep_n
    )

    out["long_structure_score"] = (
        0.45 * long_eff_n
        + 0.35 * long_flip_n
        + 0.20 * long_sep_n
    )

    return out


# =========================================================
# Impulse Scores
# =========================================================
def build_impulse_scores(close: pd.Series, rank_window: int = 252) -> pd.DataFrame:
    close = _validate_close(close)
    ret = close.pct_change()

    # short
    short_disp = close.diff(20).abs() / close.shift(20).replace(0.0, np.nan)
    short_eff = close.diff(20).abs() / ret.rolling(20).std(ddof=0).replace(0.0, np.nan)
    short_pull = _pullback_resilience(close, 20)

    # mid
    mid_disp = close.diff(60).abs() / close.shift(60).replace(0.0, np.nan)
    mid_eff = close.diff(60).abs() / ret.rolling(60).std(ddof=0).replace(0.0, np.nan)
    mid_pull = _pullback_resilience(close, 60)

    # long
    long_disp = close.diff(120).abs() / close.shift(120).replace(0.0, np.nan)
    long_eff = close.diff(120).abs() / ret.rolling(120).std(ddof=0).replace(0.0, np.nan)
    long_pull = _pullback_resilience(close, 120)

    short_disp_n = _rolling_percentile_rank(short_disp, rank_window)
    short_eff_n = _rolling_percentile_rank(short_eff, rank_window)
    short_pull_n = _rolling_percentile_rank(short_pull, rank_window)

    mid_disp_n = _rolling_percentile_rank(mid_disp, rank_window)
    mid_eff_n = _rolling_percentile_rank(mid_eff, rank_window)
    mid_pull_n = _rolling_percentile_rank(mid_pull, rank_window)

    long_disp_n = _rolling_percentile_rank(long_disp, rank_window)
    long_eff_n = _rolling_percentile_rank(long_eff, rank_window)
    long_pull_n = _rolling_percentile_rank(long_pull, rank_window)

    out = pd.DataFrame(index=close.index)

    out["short_impulse_score"] = (
        0.40 * short_disp_n
        + 0.35 * short_eff_n
        + 0.25 * short_pull_n
    )

    out["mid_impulse_score"] = (
        0.40 * mid_disp_n
        + 0.35 * mid_eff_n
        + 0.25 * mid_pull_n
    )

    out["long_impulse_score"] = (
        0.40 * long_disp_n
        + 0.35 * long_eff_n
        + 0.25 * long_pull_n
    )

    return out


# =========================================================
# Volatility Levels
# =========================================================
def build_volatility_levels(price_df: pd.DataFrame, rank_window: int = 252) -> pd.DataFrame:
    required_cols = ["Open", "High", "Low", "Close"]
    for col in required_cols:
        if col not in price_df.columns:
            raise ValueError(f"price_df 缺少必要欄位：{col}")

    df = price_df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)

    ret = close.pct_change()
    range_ratio = (high - low) / close.replace(0.0, np.nan)

    short_rv = ret.rolling(20).std(ddof=0)
    mid_rv = ret.rolling(60).std(ddof=0)
    long_rv = ret.rolling(120).std(ddof=0)

    short_range = range_ratio.rolling(20).mean()
    mid_range = range_ratio.rolling(60).mean()
    long_range = range_ratio.rolling(120).mean()

    short_atr = _atr_like(df, 20) / close.replace(0.0, np.nan)
    mid_atr = _atr_like(df, 60) / close.replace(0.0, np.nan)
    long_atr = _atr_like(df, 120) / close.replace(0.0, np.nan)

    short_rv_n = _rolling_percentile_rank(short_rv, rank_window)
    short_range_n = _rolling_percentile_rank(short_range, rank_window)
    short_atr_n = _rolling_percentile_rank(short_atr, rank_window)

    mid_rv_n = _rolling_percentile_rank(mid_rv, rank_window)
    mid_range_n = _rolling_percentile_rank(mid_range, rank_window)
    mid_atr_n = _rolling_percentile_rank(mid_atr, rank_window)

    long_rv_n = _rolling_percentile_rank(long_rv, rank_window)
    long_range_n = _rolling_percentile_rank(long_range, rank_window)
    long_atr_n = _rolling_percentile_rank(long_atr, rank_window)

    out = pd.DataFrame(index=df.index)

    out["short_volatility_level"] = (
        0.40 * short_rv_n
        + 0.30 * short_range_n
        + 0.30 * short_atr_n
    )

    out["mid_volatility_level"] = (
        0.40 * mid_rv_n
        + 0.30 * mid_range_n
        + 0.30 * mid_atr_n
    )

    out["long_volatility_level"] = (
        0.40 * long_rv_n
        + 0.30 * long_range_n
        + 0.30 * long_atr_n
    )

    return out


# =========================================================
# States
# =========================================================
def build_slow_regime_states(
    price_df: pd.DataFrame,
    rank_window: int = 252,
    short_state_window: int = 252,
    mid_state_window: int = 252,
    long_state_window: int = 504,
) -> pd.DataFrame:
    required_cols = ["Open", "High", "Low", "Close"]
    for col in required_cols:
        if col not in price_df.columns:
            raise ValueError(f"price_df 缺少必要欄位：{col}")

    df = price_df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    close = df["Close"].astype(float)

    direction_df = build_direction_scores(close, rank_window=rank_window)
    structure_df = build_structure_scores(close, rank_window=rank_window)
    impulse_df = build_impulse_scores(close, rank_window=rank_window)
    volatility_df = build_volatility_levels(df, rank_window=rank_window)

    out = pd.concat([direction_df, structure_df, impulse_df, volatility_df], axis=1)

    # direction states
    out["short_direction_state"] = _rolling_state_from_score(
        out["short_direction_score"], "down", "neutral", "up", window=short_state_window
    )
    out["mid_direction_state"] = _rolling_state_from_score(
        out["mid_direction_score"], "down", "neutral", "up", window=mid_state_window
    )
    out["long_direction_state"] = _rolling_state_from_score(
        out["long_direction_score"], "down", "neutral", "up", window=long_state_window
    )

    # structure states
    out["short_structure_state"] = _rolling_state_from_score(
        out["short_structure_score"], "messy", "neutral", "clean", window=short_state_window
    )
    out["mid_structure_state"] = _rolling_state_from_score(
        out["mid_structure_score"], "messy", "neutral", "clean", window=mid_state_window
    )
    out["long_structure_state"] = _rolling_state_from_score(
        out["long_structure_score"], "messy", "neutral", "clean", window=long_state_window
    )

    # impulse states
    out["short_impulse_state"] = _rolling_state_from_score(
        out["short_impulse_score"], "low", "medium", "high", window=short_state_window
    )
    out["mid_impulse_state"] = _rolling_state_from_score(
        out["mid_impulse_score"], "low", "medium", "high", window=mid_state_window
    )
    out["long_impulse_state"] = _rolling_state_from_score(
        out["long_impulse_score"], "low", "medium", "high", window=long_state_window
    )

    # volatility states
    out["short_volatility_state"] = _rolling_state_from_score(
        out["short_volatility_level"], "compressed", "normal", "expanded", window=short_state_window
    )
    out["mid_volatility_state"] = _rolling_state_from_score(
        out["mid_volatility_level"], "compressed", "normal", "expanded", window=mid_state_window
    )
    out["long_volatility_state"] = _rolling_state_from_score(
        out["long_volatility_level"], "compressed", "normal", "expanded", window=long_state_window
    )

    return out

# =========================================================
# Neutral Bias / Regime Naming
# =========================================================
def _neutral_bias_from_score(
    score: pd.Series,
    state: pd.Series,
    window: int = 252,
) -> pd.Series:
    """
    對 direction_state == neutral 的區間再細分：
    - neutral_up_bias
    - neutral_mid
    - neutral_down_bias
    """
    q30 = score.rolling(window=window, min_periods=min(window, max(3, window // 3))).quantile(0.30)
    q70 = score.rolling(window=window, min_periods=min(window, max(3, window // 3))).quantile(0.70)

    neutral_bias = pd.Series(index=score.index, dtype=object)

    neutral_mask = state == "neutral"
    neutral_bias[~neutral_mask] = np.nan

    # neutral 區內中心點
    center = (q30 + q70) / 2.0
    lower_mid = (q30 + center) / 2.0
    upper_mid = (q70 + center) / 2.0

    neutral_bias[neutral_mask & (score <= lower_mid)] = "neutral_down_bias"
    neutral_bias[neutral_mask & (score >= upper_mid)] = "neutral_up_bias"
    neutral_bias[neutral_mask & (score > lower_mid) & (score < upper_mid)] = "neutral_mid"

    return neutral_bias


def _compose_regime_name(
    direction_state: str,
    direction_bias: str,
    structure_state: str,
    impulse_state: str,
    volatility_state: str,
) -> str:
    """
    slow regime 命名規則：
    1. 先決定主體名
    2. 再加 volatility / structure 修飾
    順序：volatility -> structure -> 主體名
    """
    # 主體名
    if direction_state == "up":
        base_name = "急漲" if impulse_state == "high" else "緩漲"
    elif direction_state == "down":
        base_name = "急跌" if impulse_state == "high" else "緩跌"
    else:
        if direction_bias == "neutral_up_bias":
            base_name = "偏多盤整"
        elif direction_bias == "neutral_down_bias":
            base_name = "偏空盤整"
        else:
            base_name = "中性盤整"

    prefix_parts = []

    if volatility_state == "compressed":
        prefix_parts.append("壓縮")
    elif volatility_state == "expanded":
        prefix_parts.append("高波動")

    if structure_state == "messy":
        prefix_parts.append("混亂")

    if len(prefix_parts) == 0:
        return base_name

    return "".join(prefix_parts) + base_name


def build_slow_regime_names(
    state_df: pd.DataFrame,
    short_state_window: int = 252,
    mid_state_window: int = 252,
    long_state_window: int = 504,
) -> pd.DataFrame:
    """
    根據 short / mid / long 的 state 產生最終 regime 名稱。
    """
    df = state_df.copy()

    # neutral bias
    df["short_direction_bias"] = _neutral_bias_from_score(
        df["short_direction_score"], df["short_direction_state"], window=short_state_window
    )
    df["mid_direction_bias"] = _neutral_bias_from_score(
        df["mid_direction_score"], df["mid_direction_state"], window=mid_state_window
    )
    df["long_direction_bias"] = _neutral_bias_from_score(
        df["long_direction_score"], df["long_direction_state"], window=long_state_window
    )

    # short name
    df["short_regime_name"] = [
        _compose_regime_name(d, b, s, i, v)
        for d, b, s, i, v in zip(
            df["short_direction_state"],
            df["short_direction_bias"],
            df["short_structure_state"],
            df["short_impulse_state"],
            df["short_volatility_state"],
        )
    ]

    # mid name
    df["mid_regime_name"] = [
        _compose_regime_name(d, b, s, i, v)
        for d, b, s, i, v in zip(
            df["mid_direction_state"],
            df["mid_direction_bias"],
            df["mid_structure_state"],
            df["mid_impulse_state"],
            df["mid_volatility_state"],
        )
    ]

    # long name
    df["long_regime_name"] = [
        _compose_regime_name(d, b, s, i, v)
        for d, b, s, i, v in zip(
            df["long_direction_state"],
            df["long_direction_bias"],
            df["long_structure_state"],
            df["long_impulse_state"],
            df["long_volatility_state"],
        )
    ]

    return df


# =========================================================
# Confidence
# =========================================================
def _boundary_confidence_from_score(
    score: pd.Series,
    state: pd.Series,
    window: int = 252,
    q_low: float = 0.30,
    q_high: float = 0.70,
) -> pd.Series:
    """
    根據 score 在當前 state 區間中的相對位置，估計邊界距離 confidence。
    輸出範圍 0~1。

    設計原則：
    - up: 越高於 q70，confidence 越高
    - down: 越低於 q30，confidence 越高
    - neutral: 越靠近 neutral 區中心，confidence 越高
    """
    q30 = score.rolling(window=window, min_periods=min(window, max(3, window // 3))).quantile(q_low)
    q70 = score.rolling(window=window, min_periods=min(window, max(3, window // 3))).quantile(q_high)

    conf = pd.Series(index=score.index, dtype=float)

    # down 區：從 q30 往下越深，confidence 越高
    down_mask = state == "down"
    down_span = (q70 - q30).replace(0.0, np.nan)
    down_raw = (q30 - score) / down_span
    conf[down_mask] = down_raw[down_mask].clip(lower=0.0, upper=1.0)

    # up 區：從 q70 往上越深，confidence 越高
    up_mask = state == "up"
    up_span = (q70 - q30).replace(0.0, np.nan)
    up_raw = (score - q70) / up_span
    conf[up_mask] = up_raw[up_mask].clip(lower=0.0, upper=1.0)

    # neutral 區：越靠近 neutral 區中心越高
    neutral_mask = state == "neutral"
    center = (q30 + q70) / 2.0
    half_band = ((q70 - q30) / 2.0).replace(0.0, np.nan)
    neutral_raw = 1.0 - ((score - center).abs() / half_band)
    conf[neutral_mask] = neutral_raw[neutral_mask].clip(lower=0.0, upper=1.0)

    # 加一點底部，避免整排太接近 0，讓辨識度更好
    conf = 0.15 + 0.85 * conf.fillna(0.0)

    return conf.clip(lower=0.0, upper=1.0)


def _name_stability_confidence(name_series: pd.Series, max_run: int = 10) -> pd.Series:
    """
    看 final regime name 已連續維持多久。
    維持越久，confidence 越高，但做飽和處理。
    """
    run_lengths = []
    current_name = None
    run = 0

    for name in name_series:
        if pd.isna(name):
            current_name = None
            run = 0
            run_lengths.append(0)
            continue

        if name == current_name:
            run += 1
        else:
            current_name = name
            run = 1

        run_lengths.append(run)

    run_s = pd.Series(run_lengths, index=name_series.index, dtype=float)
    conf = (run_s / max_run).clip(lower=0.0, upper=1.0)
    return conf


def build_slow_regime_confidence(
    named_df: pd.DataFrame,
    short_state_window: int = 252,
    mid_state_window: int = 252,
    long_state_window: int = 504,
) -> pd.DataFrame:
    """
    產生 short / mid / long 的 regime confidence。
    來源：
    - 邊界距離 0.70
    - 名稱穩定性 0.30
    """
    df = named_df.copy()

    # short boundary confidence
    short_dir_conf = _boundary_confidence_from_score(
        df["short_direction_score"], df["short_direction_state"], window=short_state_window
    )
    short_str_conf = _boundary_confidence_from_score(
        df["short_structure_score"], df["short_structure_state"], window=short_state_window
    )
    short_imp_conf = _boundary_confidence_from_score(
        df["short_impulse_score"], df["short_impulse_state"], window=short_state_window
    )
    short_vol_conf = _boundary_confidence_from_score(
        df["short_volatility_level"], df["short_volatility_state"], window=short_state_window
    )
    short_boundary_conf = (short_dir_conf + short_str_conf + short_imp_conf + short_vol_conf) / 4.0
    short_stability_conf = _name_stability_confidence(df["short_regime_name"])
    df["short_regime_confidence"] = 0.70 * short_boundary_conf + 0.30 * short_stability_conf

    # mid boundary confidence
    mid_dir_conf = _boundary_confidence_from_score(
        df["mid_direction_score"], df["mid_direction_state"], window=mid_state_window
    )
    mid_str_conf = _boundary_confidence_from_score(
        df["mid_structure_score"], df["mid_structure_state"], window=mid_state_window
    )
    mid_imp_conf = _boundary_confidence_from_score(
        df["mid_impulse_score"], df["mid_impulse_state"], window=mid_state_window
    )
    mid_vol_conf = _boundary_confidence_from_score(
        df["mid_volatility_level"], df["mid_volatility_state"], window=mid_state_window
    )
    mid_boundary_conf = (mid_dir_conf + mid_str_conf + mid_imp_conf + mid_vol_conf) / 4.0
    mid_stability_conf = _name_stability_confidence(df["mid_regime_name"])
    df["mid_regime_confidence"] = 0.70 * mid_boundary_conf + 0.30 * mid_stability_conf

    # long boundary confidence
    long_dir_conf = _boundary_confidence_from_score(
        df["long_direction_score"], df["long_direction_state"], window=long_state_window
    )
    long_str_conf = _boundary_confidence_from_score(
        df["long_structure_score"], df["long_structure_state"], window=long_state_window
    )
    long_imp_conf = _boundary_confidence_from_score(
        df["long_impulse_score"], df["long_impulse_state"], window=long_state_window
    )
    long_vol_conf = _boundary_confidence_from_score(
        df["long_volatility_level"], df["long_volatility_state"], window=long_state_window
    )
    long_boundary_conf = (long_dir_conf + long_str_conf + long_imp_conf + long_vol_conf) / 4.0
    long_stability_conf = _name_stability_confidence(df["long_regime_name"])
    df["long_regime_confidence"] = 0.70 * long_boundary_conf + 0.30 * long_stability_conf

    return df


# =========================================================
# Full Builder
# =========================================================
def build_slow_regime_full_state(
    price_df: pd.DataFrame,
    rank_window: int = 252,
    short_state_window: int = 252,
    mid_state_window: int = 252,
    long_state_window: int = 504,
) -> pd.DataFrame:
    """
    slow regime 完整輸出：
    - scores
    - states
    - regime names
    - regime confidence
    """
    state_df = build_slow_regime_states(
        price_df=price_df,
        rank_window=rank_window,
        short_state_window=short_state_window,
        mid_state_window=mid_state_window,
        long_state_window=long_state_window,
    )
    named_df = build_slow_regime_names(
        state_df=state_df,
        short_state_window=short_state_window,
        mid_state_window=mid_state_window,
        long_state_window=long_state_window,
    )

    full_df = build_slow_regime_confidence(
        named_df=named_df,
        short_state_window=short_state_window,
        mid_state_window=mid_state_window,
        long_state_window=long_state_window,
    )
    return full_df