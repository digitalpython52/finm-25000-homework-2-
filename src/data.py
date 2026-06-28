"""Historical market-data download via Alpaca's Historical Market Data API.

Downloads >= 5 years of daily OHLCV bars for a user-selected ticker and
returns a clean Pandas DataFrame indexed by date with columns:
``open, high, low, close, volume`` (plus ``trade_count`` / ``vwap`` if present).

Results are cached to ``data_cache/<TICKER>_<years>y.parquet`` (falls back to
CSV) so repeated runs are fast and do not re-hit the API.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

from . import config

OHLCV_COLS = ["open", "high", "low", "close", "volume"]


def _cache_path(ticker: str, years: int):
    return config.DATA_DIR / f"{ticker.upper()}_{years}y.parquet"


def _load_cache(ticker: str, years: int) -> pd.DataFrame | None:
    path = _cache_path(ticker, years)
    try:
        if path.exists():
            return pd.read_parquet(path)
    except Exception:
        # parquet engine may be unavailable; try the CSV sibling
        csv = path.with_suffix(".csv")
        if csv.exists():
            return pd.read_csv(csv, index_col=0, parse_dates=True)
    return None


def _save_cache(df: pd.DataFrame, ticker: str, years: int) -> None:
    path = _cache_path(ticker, years)
    try:
        df.to_parquet(path)
    except Exception:
        df.to_csv(path.with_suffix(".csv"))


def download(
    ticker: str = config.DEFAULT_TICKER,
    years: int = config.YEARS_OF_HISTORY,
    use_cache: bool = True,
    refresh: bool = False,
) -> pd.DataFrame:
    """Download daily OHLCV bars for ``ticker`` covering ``years`` of history.

    Parameters
    ----------
    ticker : str
        Equity symbol, e.g. ``"AAPL"``.
    years : int
        Years of history to request (must be >= 5 per the assignment).
    use_cache / refresh :
        ``use_cache`` reads a local copy if present; ``refresh`` forces a
        fresh API pull and overwrites the cache.
    """
    ticker = ticker.upper().strip()
    if years < 5:
        raise ValueError("The assignment requires at least 5 years of data.")

    if use_cache and not refresh:
        cached = _load_cache(ticker, years)
        if cached is not None and not cached.empty:
            return cached

    key_id, secret = config.get_alpaca_credentials()
    client = StockHistoricalDataClient(key_id, secret)

    # Free Alpaca plans cannot query the most recent ~15 min of SIP data, so
    # back the end time off comfortably; daily bars are unaffected.
    end = datetime.now(timezone.utc) - timedelta(minutes=20)
    start = end - timedelta(days=int(years * 365.25) + 5)

    request = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        adjustment=Adjustment.ALL,   # split + dividend adjusted for realism
    )
    bars = client.get_stock_bars(request)
    df = bars.df

    if df is None or df.empty:
        raise RuntimeError(f"No data returned for {ticker!r}.")

    # Alpaca returns a MultiIndex (symbol, timestamp). Flatten to a date index.
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(ticker, level="symbol")

    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "date"
    df = df[~df.index.duplicated(keep="last")].sort_index()

    # Keep a tidy, predictable column set.
    keep = [c for c in OHLCV_COLS + ["trade_count", "vwap"] if c in df.columns]
    df = df[keep]

    if use_cache:
        _save_cache(df, ticker, years)
    return df


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    d = download("AAPL")
    print(d.shape)
    print(d.head())
    print(d.tail())
