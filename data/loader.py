import pandas as pd
import yfinance as yf


REQUIRED_PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def load_price_data(
    ticker: str,
    period: str = "10y",
    auto_adjust: bool = False,
) -> pd.DataFrame:
    """
    使用 yfinance 下載價格資料，並做基本清洗。

    Parameters
    ----------
    ticker : str
        商品代號，例如 AAPL、MSFT、^GSPC。
    period : str
        yfinance 支援的期間，例如 1y / 5y / 10y / max。
    auto_adjust : bool
        是否使用 yfinance 的自動還原價格。

    Returns
    -------
    pd.DataFrame
        至少包含 Open, High, Low, Close, Volume 五欄。
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("ticker 必須是非空字串。")

    df = yf.download(
        tickers=ticker,
        period=period,
        auto_adjust=auto_adjust,
        progress=False,
    )

    if df is None or len(df) == 0:
        raise ValueError(f"下載不到資料：{ticker}")

    df = df.copy()

    # yfinance 有時會回傳 multi-index columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    missing_cols = [col for col in REQUIRED_PRICE_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"資料缺少必要欄位：{missing_cols}")

    df = df[REQUIRED_PRICE_COLUMNS].copy()
    df = df.dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    return df