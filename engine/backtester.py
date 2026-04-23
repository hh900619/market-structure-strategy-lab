import numpy as np
import pandas as pd


def run_backtest(
    close: pd.Series,
    signal: pd.Series,
    cost_bps: float = 0.0,
) -> pd.DataFrame:
    """
    核心回測函式。

    Parameters
    ----------
    close : pd.Series
        收盤價序列，index 建議為 DatetimeIndex。
    signal : pd.Series
        訊號序列，可為 -1 / 0 / 1，也可為連續權重。
    cost_bps : float
        換手成本（bps）。

    Returns
    -------
    pd.DataFrame
        回測結果表。
    """
    if close is None or signal is None:
        raise ValueError("close 和 signal 不能是 None。")

    if len(close) == 0:
        raise ValueError("close 為空，無法回測。")

    close = close.astype(float).copy()
    signal = signal.reindex(close.index).fillna(0.0).astype(float)

    asset_ret = close.pct_change().fillna(0.0)

    # 用前一根 signal 作為本根持倉，避免偷看未來
    position = signal.shift(1).fillna(0.0)

    gross_ret = position * asset_ret

    turnover = position.diff().abs().fillna(position.abs())
    cost_rate = float(cost_bps) / 10000.0
    cost = turnover * cost_rate

    net_ret = gross_ret - cost
    equity = (1.0 + net_ret).cumprod()
    drawdown = equity / equity.cummax() - 1.0

    bt = pd.DataFrame(
        {
            "close": close,
            "signal": signal,
            "position": position,
            "asset_ret": asset_ret,
            "gross_ret": gross_ret,
            "cost": cost,
            "returns": net_ret,
            "equity": equity,
            "drawdown": drawdown,
            "turnover": turnover,
        },
        index=close.index,
    )

    return bt


def compute_stats(
    bt: pd.DataFrame,
    annual_bars: int = 252,
) -> dict[str, float]:
    """
    基本績效統計。
    """
    if bt is None or len(bt) == 0:
        return {
            "total_return": 0.0,
            "annual_return": 0.0,
            "annual_vol": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
        }

    required_cols = ["returns", "equity", "drawdown"]
    for col in required_cols:
        if col not in bt.columns:
            raise ValueError(f"bt 缺少必要欄位：{col}")

    ret = bt["returns"].dropna()

    if len(ret) == 0:
        return {
            "total_return": 0.0,
            "annual_return": 0.0,
            "annual_vol": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
        }

    final_equity = float(bt["equity"].iloc[-1])
    total_return = final_equity - 1.0

    n = len(ret)
    if n > 0 and final_equity > 0:
        annual_return = final_equity ** (annual_bars / n) - 1.0
    else:
        annual_return = 0.0

    vol = float(ret.std(ddof=0))
    annual_vol = vol * np.sqrt(annual_bars)

    if vol == 0:
        sharpe = 0.0
    else:
        sharpe = float(ret.mean() / vol * np.sqrt(annual_bars))

    max_drawdown = float(bt["drawdown"].min())

    return {
        "total_return": float(total_return),
        "annual_return": float(annual_return),
        "annual_vol": float(annual_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_drawdown),
    }