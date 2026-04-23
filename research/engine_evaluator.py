from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple, Any

import numpy as np
import pandas as pd


# =========================================================
# Backtest core
# =========================================================
def build_backtest_df(
    close: pd.Series,
    signal: pd.Series,
    cost_bps: float = 0.0,
) -> pd.DataFrame:
    """
    用最基本、可重複使用的方式，把 signal 轉成回測結果。
    - 使用前一根 signal 乘上本根報酬，避免同根偷看
    - 成本用 turnover * bps 扣除
    """
    df = pd.DataFrame(index=close.index.copy())
    df["close"] = close.astype(float)
    df["ret"] = df["close"].pct_change().fillna(0.0)

    df["signal"] = signal.astype(float).fillna(0.0)
    df["position"] = df["signal"].shift(1).fillna(0.0)

    # turnover: 持倉變化
    df["turnover"] = df["signal"].diff().abs().fillna(df["signal"].abs())

    gross_ret = df["position"] * df["ret"]
    trading_cost = df["turnover"] * (cost_bps / 10000.0)

    df["gross_strategy_ret"] = gross_ret
    df["trading_cost"] = trading_cost
    df["strategy_ret"] = gross_ret - trading_cost
    df["equity"] = (1.0 + df["strategy_ret"]).cumprod()

    return df


def calc_max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    return float(dd.min()) if len(dd) > 0 else 0.0


def calc_annualized_return(strategy_ret: pd.Series, bars_per_year: int = 252) -> float:
    n = len(strategy_ret)
    if n == 0:
        return 0.0

    total = float((1.0 + strategy_ret).prod())
    if total <= 0:
        return -1.0

    return total ** (bars_per_year / n) - 1.0


def calc_annualized_vol(strategy_ret: pd.Series, bars_per_year: int = 252) -> float:
    if len(strategy_ret) == 0:
        return 0.0
    return float(strategy_ret.std()) * np.sqrt(bars_per_year)


def calc_sharpe(strategy_ret: pd.Series, bars_per_year: int = 252) -> float:
    ann_vol = calc_annualized_vol(strategy_ret, bars_per_year=bars_per_year)
    if ann_vol == 0:
        return 0.0
    ann_ret = calc_annualized_return(strategy_ret, bars_per_year=bars_per_year)
    return ann_ret / ann_vol


# =========================================================
# Trade stats
# =========================================================
def extract_trade_returns(signal: pd.Series, strategy_ret: pd.Series) -> List[float]:
    """
    用 signal 進出場切段，計算每筆交易報酬。
    簡化版本，但足夠做 engine 研究。
    """
    signal = signal.fillna(0.0).astype(float)
    strategy_ret = strategy_ret.fillna(0.0).astype(float)

    trade_returns: List[float] = []
    current_trade_rets: List[float] = []
    in_trade = False

    for i in range(len(signal)):
        pos = float(signal.iloc[i])
        ret = float(strategy_ret.iloc[i])

        if not in_trade and pos != 0:
            in_trade = True
            current_trade_rets = [ret]
        elif in_trade and pos != 0:
            current_trade_rets.append(ret)
        elif in_trade and pos == 0:
            trade_returns.append(float(np.prod([1.0 + x for x in current_trade_rets]) - 1.0))
            current_trade_rets = []
            in_trade = False

    # 最後一筆如果還沒平倉，也把它算進去
    if in_trade and len(current_trade_rets) > 0:
        trade_returns.append(float(np.prod([1.0 + x for x in current_trade_rets]) - 1.0))

    return trade_returns


def calc_trade_stats(signal: pd.Series, strategy_ret: pd.Series) -> Dict[str, float]:
    trade_returns = extract_trade_returns(signal, strategy_ret)
    trade_count = len(trade_returns)

    if trade_count == 0:
        return {
            "trade_count": 0,
            "win_rate": 0.0,
            "avg_trade_return": 0.0,
            "median_trade_return": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
        }

    arr = np.array(trade_returns, dtype=float)
    win_rate = float((arr > 0).mean())

    return {
        "trade_count": int(trade_count),
        "win_rate": win_rate,
        "avg_trade_return": float(arr.mean()),
        "median_trade_return": float(np.median(arr)),
        "best_trade": float(arr.max()),
        "worst_trade": float(arr.min()),
    }


# =========================================================
# Diagnostic rules
# =========================================================
def diagnose_engine_quality(
    *,
    name: str,
    base_nonzero: int,
    engine_nonzero: int,
    trade_count: int,
    pass_ratio: float,
    sharpe: float,
    max_dd: float,
) -> Tuple[str, str]:
    """
    給一個簡單但實用的品質標記。
    這不是最終真理，而是研究輔助。
    """
    if name == "base":
        return "baseline", "原始策略基準，不做 engine 評分。"

    if engine_nonzero <= 10 or trade_count <= 5:
        return "too_strict", "訊號或交易次數太少，代表 engine 可能過度嚴格。"

    if pass_ratio < 0.10:
        return "too_strict", "通過比例過低，代表 engine 可能把策略過濾得太乾。"

    if pass_ratio > 0.90:
        return "too_loose", "通過比例過高，代表 engine 幾乎沒有發揮過濾作用。"

    if sharpe <= 0 and max_dd < -0.25:
        return "weak", "風險報酬表現偏弱，代表 engine 目前沒有帶來明顯改善。"

    return "reasonable", "engine 的過濾強度大致合理，可進一步比較績效與穩定度。"


# =========================================================
# Evaluation row
# =========================================================
def build_evaluation_row(
    *,
    name: str,
    signal: pd.Series,
    close: pd.Series,
    base_nonzero: int,
    cost_bps: float = 0.0,
) -> Dict[str, Any]:
    bt = build_backtest_df(close=close, signal=signal, cost_bps=cost_bps)

    total_return = float(bt["equity"].iloc[-1] - 1.0) if len(bt) > 0 else 0.0
    ann_return = calc_annualized_return(bt["strategy_ret"])
    ann_vol = calc_annualized_vol(bt["strategy_ret"])
    sharpe = calc_sharpe(bt["strategy_ret"])
    max_dd = calc_max_drawdown(bt["equity"])
    exposure = float((signal != 0).mean()) if len(signal) > 0 else 0.0
    turnover = int(signal.fillna(0).diff().fillna(0).ne(0).sum())
    engine_nonzero = int((signal != 0).sum())
    filtered_signals = int(base_nonzero - engine_nonzero)
    pass_ratio = float(engine_nonzero / base_nonzero) if base_nonzero > 0 else 0.0
    block_rate = 1.0 - pass_ratio if base_nonzero > 0 else 0.0

    trade_stats = calc_trade_stats(signal=signal, strategy_ret=bt["strategy_ret"])
    quality_flag, comment = diagnose_engine_quality(
        name=name,
        base_nonzero=base_nonzero,
        engine_nonzero=engine_nonzero,
        trade_count=trade_stats["trade_count"],
        pass_ratio=pass_ratio,
        sharpe=sharpe,
        max_dd=max_dd,
    )

    row = {
        "variant": name,
        "total_return": total_return,
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "exposure": exposure,
        "turnover": turnover,
        "kept_signals": engine_nonzero,
        "filtered_signals": filtered_signals,
        "pass_ratio": pass_ratio,
        "block_rate": block_rate,
        "trade_count": trade_stats["trade_count"],
        "win_rate": trade_stats["win_rate"],
        "avg_trade_return": trade_stats["avg_trade_return"],
        "median_trade_return": trade_stats["median_trade_return"],
        "best_trade": trade_stats["best_trade"],
        "worst_trade": trade_stats["worst_trade"],
        "quality_flag": quality_flag,
        "comment": comment,
    }
    return row


# =========================================================
# Main evaluator
# =========================================================
@dataclass
class EngineEvaluationResult:
    summary_df: pd.DataFrame
    signal_map: Dict[str, pd.Series]
    engine_reason_tables: Dict[str, pd.DataFrame]


def evaluate_engine_variants(
    *,
    close: pd.Series,
    base_signal: pd.Series,
    engine_signal_map: Dict[str, pd.Series],
    engine_reason_map: Dict[str, pd.Series] | None = None,
    cost_bps: float = 0.0,
) -> EngineEvaluationResult:
    """
    輸入：
    - close
    - base_signal
    - engine_signal_map: {"low": ..., "medium": ..., "high": ...}
    - engine_reason_map: {"low": eng_df["engine_reason"], ...}

    輸出：
    - summary_df：總比較表
    - signal_map：方便外部再畫圖
    - engine_reason_tables：各 strictness 的 reason 統計
    """
    summary_rows: List[Dict[str, Any]] = []
    signal_map: Dict[str, pd.Series] = {}
    engine_reason_tables: Dict[str, pd.DataFrame] = {}

    base_nonzero = int((base_signal != 0).sum())

    # base
    signal_map["base"] = base_signal
    summary_rows.append(
        build_evaluation_row(
            name="base",
            signal=base_signal,
            close=close,
            base_nonzero=base_nonzero,
            cost_bps=cost_bps,
        )
    )

    # engine variants
    for name, sig in engine_signal_map.items():
        signal_map[name] = sig

        summary_rows.append(
            build_evaluation_row(
                name=name,
                signal=sig,
                close=close,
                base_nonzero=base_nonzero,
                cost_bps=cost_bps,
            )
        )

        if engine_reason_map is not None and name in engine_reason_map:
            reason_counts = (
                engine_reason_map[name]
                .astype(str)
                .value_counts(dropna=False)
                .rename_axis("engine_reason")
                .reset_index(name="count")
            )
            engine_reason_tables[name] = reason_counts

    summary_df = pd.DataFrame(summary_rows)

    # 比較 base 的增減
    base_row = summary_df.loc[summary_df["variant"] == "base"].iloc[0]
    summary_df["delta_total_return_vs_base"] = summary_df["total_return"] - float(base_row["total_return"])
    summary_df["delta_sharpe_vs_base"] = summary_df["sharpe"] - float(base_row["sharpe"])
    summary_df["delta_max_dd_vs_base"] = summary_df["max_dd"] - float(base_row["max_dd"])
    summary_df["delta_trade_count_vs_base"] = summary_df["trade_count"] - int(base_row["trade_count"])

    # 欄位排序
    ordered_cols = [
        "variant",
        "total_return",
        "ann_return",
        "ann_vol",
        "sharpe",
        "max_dd",
        "exposure",
        "turnover",
        "trade_count",
        "win_rate",
        "avg_trade_return",
        "median_trade_return",
        "best_trade",
        "worst_trade",
        "kept_signals",
        "filtered_signals",
        "pass_ratio",
        "block_rate",
        "delta_total_return_vs_base",
        "delta_sharpe_vs_base",
        "delta_max_dd_vs_base",
        "delta_trade_count_vs_base",
        "quality_flag",
        "comment",
    ]
    summary_df = summary_df[ordered_cols].copy()

    return EngineEvaluationResult(
        summary_df=summary_df,
        signal_map=signal_map,
        engine_reason_tables=engine_reason_tables,
    )