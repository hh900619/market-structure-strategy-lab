import numpy as np
import pandas as pd
import yfinance as yf

from regimes.slow_regime import build_slow_regime_full_state


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


def _normalize_yfinance_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("Yahoo Finance 下載回來的資料為空")

    out = df.copy()

    # 有些版本 yfinance 會回 MultiIndex
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = out.columns.get_level_values(0)

    rename_map = {
        "Adj Close": "Adj Close",
        "Open": "Open",
        "High": "High",
        "Low": "Low",
        "Close": "Close",
        "Volume": "Volume",
    }
    out = out.rename(columns=rename_map)

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required_cols if c not in out.columns]
    if missing:
        raise ValueError(f"週線資料缺少必要欄位：{missing}")

    out = out[required_cols].copy()
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    return out


def download_weekly_price_df(ticker: str, period: str = "5y") -> pd.DataFrame:
    """
    直接從 Yahoo Finance 下載週 K（1wk）。
    """
    raw = yf.download(
        tickers=ticker,
        period=period,
        interval="1wk",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )
    weekly_df = _normalize_yfinance_df(raw)
    return weekly_df


# =========================================================
# Weekly external naming
# =========================================================
def _compose_weekly_background_name(
    direction_state,
    structure_state,
    volatility_state,
) -> str:
    if pd.isna(direction_state) or pd.isna(structure_state) or pd.isna(volatility_state):
        return "warmup"

    direction_state = str(direction_state)
    structure_state = str(structure_state)
    volatility_state = str(volatility_state)

    if direction_state == "up":
        base = "偏多"
    elif direction_state == "down":
        base = "偏空"
    else:
        base = "中性"

    middle_parts = []

    if structure_state == "clean":
        middle_parts.append("穩定")
    elif structure_state == "messy":
        middle_parts.append("混亂")

    if volatility_state == "compressed":
        middle_parts.append("壓縮")
    elif volatility_state == "expanded":
        middle_parts.append("高風險")

    return base + "".join(middle_parts) + "背景"


def build_weekly_external_labels(weekly_full_df: pd.DataFrame) -> pd.DataFrame:
    df = weekly_full_df.copy()

    required_cols = [
        "mid_direction_state",
        "mid_structure_state",
        "mid_volatility_state",
    ]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"weekly_full_df 缺少必要欄位：{col}")

    df["weekly_ready_flag"] = (
        df["mid_direction_state"].notna()
        & df["mid_structure_state"].notna()
        & df["mid_volatility_state"].notna()
    )

    df["weekly_background_name"] = [
        _compose_weekly_background_name(d, s, v)
        for d, s, v in zip(
            df["mid_direction_state"],
            df["mid_structure_state"],
            df["mid_volatility_state"],
        )
    ]

    warmup_mask = ~df["weekly_ready_flag"]

    null_out_cols = [
        "short_direction_state",
        "mid_direction_state",
        "long_direction_state",
        "short_structure_state",
        "mid_structure_state",
        "long_structure_state",
        "short_impulse_state",
        "mid_impulse_state",
        "long_impulse_state",
        "short_volatility_state",
        "mid_volatility_state",
        "long_volatility_state",
        "short_regime_name",
        "mid_regime_name",
        "long_regime_name",
        "short_regime_confidence",
        "mid_regime_confidence",
        "long_regime_confidence",
    ]

    existing_null_out_cols = [c for c in null_out_cols if c in df.columns]
    df.loc[warmup_mask, existing_null_out_cols] = np.nan

    df["weekly_background_name"] = df["weekly_background_name"].fillna("warmup")

    return df


# =========================================================
# 對齊回日線
# =========================================================
def align_weekly_to_daily(
    daily_price_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
) -> pd.DataFrame:
    daily_df = _validate_price_df(daily_price_df)

    out = weekly_df.reindex(daily_df.index, method="ffill")
    return out


# =========================================================
# Full Builder
# =========================================================
def build_weekly_regime_full_state(
    daily_price_df: pd.DataFrame,
    ticker: str,
    period: str = "5y",
    rank_window: int = 52,
    short_state_window: int = 8,
    mid_state_window: int = 12,
    long_state_window: int = 26,
) -> pd.DataFrame:
    """
    真正的 Weekly Regime 路線：

    1. 直接下載 Yahoo Finance 週 K（1wk）
    2. 用週 K 做 slow regime full state
    3. 產生 weekly external labels
    4. 再對齊回 daily index
    """
    daily_df = _validate_price_df(daily_price_df)
    weekly_price_df = download_weekly_price_df(ticker=ticker, period=period)

    weekly_full = build_slow_regime_full_state(
        price_df=weekly_price_df,
        rank_window=rank_window,
        short_state_window=short_state_window,
        mid_state_window=mid_state_window,
        long_state_window=long_state_window,
    )

    weekly_full = build_weekly_external_labels(weekly_full)

    keep_cols = [
        "weekly_ready_flag",
        "short_direction_state",
        "mid_direction_state",
        "long_direction_state",
        "short_structure_state",
        "mid_structure_state",
        "long_structure_state",
        "short_impulse_state",
        "mid_impulse_state",
        "long_impulse_state",
        "short_volatility_state",
        "mid_volatility_state",
        "long_volatility_state",
        "short_regime_name",
        "mid_regime_name",
        "long_regime_name",
        "short_regime_confidence",
        "mid_regime_confidence",
        "long_regime_confidence",
        "weekly_background_name",
    ]

    weekly_keep = weekly_full[keep_cols].copy()

    # 方便日後 debug：這層是直接週 K 下載，不是日 K resample
    weekly_keep["weekly_data_source"] = "yfinance_1wk"

    weekly_keep = weekly_keep.rename(columns={c: f"weekly_{c}" for c in weekly_keep.columns})

    aligned = align_weekly_to_daily(daily_df, weekly_keep)
    return aligned