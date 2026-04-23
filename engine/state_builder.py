import pandas as pd

from regimes.slow_regime import build_slow_regime_full_state
from regimes.weekly_regime import build_weekly_regime_full_state
from regimes.fast_regime import build_fast_regime_full_state


def _validate_price_df(price_df: pd.DataFrame) -> pd.DataFrame:
    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in required_cols:
        if col not in price_df.columns:
            raise ValueError(f"price_df 缺少必要欄位：{col}")

    df = price_df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df


def build_full_market_state(
    price_df: pd.DataFrame,
    ticker: str,
    period: str = "5y",
) -> pd.DataFrame:
    """
    建立完整市場狀態表，整合：
    1. 原始日線 OHLCV
    2. slow regime
    3. weekly context
    4. fast regime
    """
    df = _validate_price_df(price_df)

    # -----------------------------
    # Slow regime
    # -----------------------------
    slow_df = build_slow_regime_full_state(df)

    # -----------------------------
    # Weekly context
    # -----------------------------
    weekly_df = build_weekly_regime_full_state(
        daily_price_df=df,
        ticker=ticker,
        period=period,
    )

    # -----------------------------
    # Fast regime
    # -----------------------------
    fast_df = build_fast_regime_full_state(df)

    # -----------------------------
    # 合併
    # -----------------------------
    out = pd.concat(
        [
            df,
            slow_df,
            weekly_df,
            fast_df,
        ],
        axis=1,
    )

    return out


def build_state_summary_row(state_df: pd.DataFrame) -> pd.Series:
    """
    取最後一根 bar 的摘要資訊，方便 app 顯示。
    """
    if state_df is None or len(state_df) == 0:
        raise ValueError("state_df 為空，無法建立摘要。")

    return state_df.iloc[-1].copy()