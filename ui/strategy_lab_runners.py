import pandas as pd

from strategies.trend_breakout import build_trend_breakout_signals
from strategies.trend_pullback import build_trend_pullback_signals

from engines.breakout_engine import apply_breakout_engine
from engines.pullback_engine import apply_pullback_engine


def run_trend_breakout(
    price_df: pd.DataFrame,
    state_df: pd.DataFrame,
    strictness: str,
    params: dict,
):
    strat_df = build_trend_breakout_signals(
        close=price_df["Close"],
        high=price_df["High"],
        low=price_df["Low"],
        entry_window=params.get("entry_window", 20),
        trend_ma_window=params.get("trend_ma_window", 50),
        use_trend_filter=params.get("use_trend_filter", True),
        swing_window=params.get("swing_window", 2),
    )

    eng_df = apply_breakout_engine(
        state_df=state_df,
        base_signal=strat_df["base_signal"],
        strictness=strictness,
    )

    return {
        "strat_df": strat_df,
        "eng_df": eng_df,
        "base_signal": strat_df["base_signal"],
        "engine_signal": eng_df["engine_signal"],
    }


def run_trend_pullback(
    price_df: pd.DataFrame,
    state_df: pd.DataFrame,
    strictness: str,
    params: dict,
):
    strat_df = build_trend_pullback_signals(
        close=price_df["Close"],
        high=price_df["High"],
        low=price_df["Low"],
        trend_ma_window=params["trend_ma_window"],
        pullback_ma_window=params["pullback_ma_window"],
        pullback_lookback=params["pullback_lookback"],
        confirm_window=params["confirm_window"],
        touch_buffer=params["touch_buffer"],
        swing_window=params["swing_window"],
    )

    eng_df = apply_pullback_engine(
        state_df=state_df,
        base_signal=strat_df["base_signal"],
        strictness=strictness,
    )

    return {
        "strat_df": strat_df,
        "eng_df": eng_df,
        "base_signal": strat_df["base_signal"],
        "engine_signal": eng_df["engine_signal"],
    }


def run_strategy(
    strategy_key: str,
    price_df: pd.DataFrame,
    state_df: pd.DataFrame,
    strictness: str,
    params: dict,
):
    if strategy_key == "trend_breakout":
        return run_trend_breakout(price_df, state_df, strictness, params)

    if strategy_key == "trend_pullback":
        return run_trend_pullback(price_df, state_df, strictness, params)

    raise ValueError(f"未知策略：{strategy_key}")