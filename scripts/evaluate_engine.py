from __future__ import annotations

from pathlib import Path
import sys
import argparse
from typing import Tuple

# 把專案根目錄加進 Python 匯入路徑
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.loader import load_price_data
from engine.state_builder import build_full_market_state

from strategies.trend_breakout import build_trend_breakout_signals
from strategies.trend_pullback import build_trend_pullback_signals

from engines.breakout_engine import apply_breakout_engine
from engines.pullback_engine import apply_pullback_engine

from research.engine_evaluator import evaluate_engine_variants


VALID_STRATEGIES = {
    "trend_breakout",
    "trend_pullback",
}


def _parse_bool(value: str) -> bool:
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate engine usefulness across strategies."
    )
    parser.add_argument(
        "--strategy",
        type=str,
        required=True,
        choices=sorted(list(VALID_STRATEGIES)),
        help="Strategy name: trend_breakout / trend_pullback / oscillator_reversal",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default="AAPL",
        help="Ticker symbol, default=AAPL",
    )
    parser.add_argument(
        "--period",
        type=str,
        default="5y",
        help="Data period, default=5y",
    )
    parser.add_argument(
        "--cost_bps",
        type=float,
        default=0.0,
        help="Transaction cost in bps, default=0.0",
    )

    # =====================================================
    # breakout params（新版）
    # =====================================================
    parser.add_argument("--breakout_entry_window", type=int, default=10)
    parser.add_argument("--breakout_trend_ma_window", type=int, default=20)
    parser.add_argument("--breakout_use_trend_filter", type=_parse_bool, default=False)
    parser.add_argument("--breakout_swing_window", type=int, default=1)

    # =====================================================
    # pullback params（新版）
    # =====================================================
    parser.add_argument("--pullback_trend_ma_window", type=int, default=20)
    parser.add_argument("--pullback_ma_window", type=int, default=10)
    parser.add_argument("--pullback_lookback", type=int, default=8)
    parser.add_argument("--pullback_confirm_window", type=int, default=3)
    parser.add_argument("--pullback_touch_buffer", type=float, default=0.003)
    parser.add_argument("--pullback_swing_window", type=int, default=1)


    return parser.parse_args()


def run_trend_breakout(
    price_df,
    state_df,
    args: argparse.Namespace,
) -> Tuple:
    strat_df = build_trend_breakout_signals(
        close=price_df["Close"],
        high=price_df["High"],
        low=price_df["Low"],
        entry_window=args.breakout_entry_window,
        trend_ma_window=args.breakout_trend_ma_window,
        use_trend_filter=args.breakout_use_trend_filter,
        swing_window=args.breakout_swing_window,
    )
    base_signal = strat_df["base_signal"]

    eng_low = apply_breakout_engine(
        state_df=state_df,
        base_signal=base_signal,
        strictness="low",
    )
    eng_medium = apply_breakout_engine(
        state_df=state_df,
        base_signal=base_signal,
        strictness="medium",
    )
    eng_high = apply_breakout_engine(
        state_df=state_df,
        base_signal=base_signal,
        strictness="high",
    )

    return strat_df, base_signal, {
        "low": eng_low,
        "medium": eng_medium,
        "high": eng_high,
    }


def run_trend_pullback(
    price_df,
    state_df,
    args: argparse.Namespace,
) -> Tuple:
    strat_df = build_trend_pullback_signals(
        close=price_df["Close"],
        high=price_df["High"],
        low=price_df["Low"],
        trend_ma_window=args.pullback_trend_ma_window,
        pullback_ma_window=args.pullback_ma_window,
        pullback_lookback=args.pullback_lookback,
        confirm_window=args.pullback_confirm_window,
        touch_buffer=args.pullback_touch_buffer,
        swing_window=args.pullback_swing_window,
    )
    base_signal = strat_df["base_signal"]

    eng_low = apply_pullback_engine(
        state_df=state_df,
        base_signal=base_signal,
        strictness="low",
    )
    eng_medium = apply_pullback_engine(
        state_df=state_df,
        base_signal=base_signal,
        strictness="medium",
    )
    eng_high = apply_pullback_engine(
        state_df=state_df,
        base_signal=base_signal,
        strictness="high",
    )

    return strat_df, base_signal, {
        "low": eng_low,
        "medium": eng_medium,
        "high": eng_high,
    }


def run_strategy(
    strategy: str,
    price_df,
    state_df,
    args: argparse.Namespace,
) -> Tuple:
    if strategy == "trend_breakout":
        return run_trend_breakout(price_df, state_df, args)
    if strategy == "trend_pullback":
        return run_trend_pullback(price_df, state_df, args)

    raise ValueError(f"Unknown strategy: {strategy}")


def print_header(args: argparse.Namespace):
    print("\n" + "=" * 88)
    print("ENGINE EVALUATION")
    print("=" * 88)
    print(f"strategy : {args.strategy}")
    print(f"ticker   : {args.ticker}")
    print(f"period   : {args.period}")
    print(f"cost_bps : {args.cost_bps}")
    print("-" * 88)

    if args.strategy == "trend_breakout":
        print(
            f"params   : entry_window={args.breakout_entry_window}, "
            f"trend_ma_window={args.breakout_trend_ma_window}, "
            f"use_trend_filter={args.breakout_use_trend_filter}, "
            f"swing_window={args.breakout_swing_window}"
        )
    elif args.strategy == "trend_pullback":
        print(
            f"params   : trend_ma_window={args.pullback_trend_ma_window}, "
            f"pullback_ma_window={args.pullback_ma_window}, "
            f"pullback_lookback={args.pullback_lookback}, "
            f"confirm_window={args.pullback_confirm_window}, "
            f"touch_buffer={args.pullback_touch_buffer}, "
            f"swing_window={args.pullback_swing_window}"
        )
    elif args.strategy == "oscillator_reversal":
        print(
            f"params   : kd_window={args.or_kd_window}, "
            f"kd_smooth_k={args.or_kd_smooth_k}, "
            f"kd_smooth_d={args.or_kd_smooth_d}, "
            f"ma_window={args.or_ma_window}, "
            f"long_k_threshold={args.or_long_k_threshold}, "
            f"short_k_threshold={args.or_short_k_threshold}, "
            f"long_dev_threshold={args.or_long_dev_threshold}, "
            f"short_dev_threshold={args.or_short_dev_threshold}, "
            f"exit_k_mid={args.or_exit_k_mid}"
        )
    print("=" * 88)


def main():
    args = parse_args()
    print_header(args)

    price_df = load_price_data(args.ticker, period=args.period)
    state_df = build_full_market_state(price_df, ticker=args.ticker, period=args.period)

    _, base_signal, engine_result_map = run_strategy(
        strategy=args.strategy,
        price_df=price_df,
        state_df=state_df,
        args=args,
    )

    result = evaluate_engine_variants(
        close=price_df["Close"],
        base_signal=base_signal,
        engine_signal_map={
            "low": engine_result_map["low"]["engine_signal"],
            "medium": engine_result_map["medium"]["engine_signal"],
            "high": engine_result_map["high"]["engine_signal"],
        },
        engine_reason_map={
            "low": engine_result_map["low"]["engine_reason"],
            "medium": engine_result_map["medium"]["engine_reason"],
            "high": engine_result_map["high"]["engine_reason"],
        },
        cost_bps=args.cost_bps,
    )

    print("\n=== SUMMARY ===")
    print(result.summary_df.to_string(index=False))

    for name, df in result.engine_reason_tables.items():
        print(f"\n=== ENGINE REASONS: {name} ===")
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()