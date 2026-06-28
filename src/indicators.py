"""Technical indicators implemented from scratch with pandas / numpy.

Categories covered (11 indicators, well beyond the required 6):

  Trend       : SMA, EMA, MACD, ADX
  Momentum    : RSI, Stochastic Oscillator, Williams %R
  Volatility  : Bollinger Bands, ATR
  Volume      : OBV, Chaikin Money Flow (CMF)

Each function takes the OHLCV DataFrame (or relevant Series) and returns a
Series / DataFrame aligned to the input index. ``add_all`` appends every
indicator as columns onto a copy of the input frame for convenience.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------
def sma(series: pd.Series, window: int = 20) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int = 20) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=window, adjust=False).mean()


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Moving Average Convergence Divergence.

    Returns columns: ``macd``, ``macd_signal``, ``macd_hist``.
    """
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "macd_signal": signal_line, "macd_hist": hist}
    )


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr


def adx(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """Average Directional Index (Wilder).

    Returns columns: ``plus_di``, ``minus_di``, ``adx``.
    """
    high, low = df["high"], df["low"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    tr = _true_range(df)
    # Wilder smoothing == EMA with alpha = 1/window
    atr_ = tr.ewm(alpha=1 / window, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr_
    minus_di = 100 * minus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr_

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_ = dx.ewm(alpha=1 / window, adjust=False).mean()
    return pd.DataFrame({"plus_di": plus_di, "minus_di": minus_di, "adx": adx_})


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------
def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder smoothing)."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(100)  # if avg_loss == 0 -> RSI 100


def stochastic(
    df: pd.DataFrame,
    k_window: int = 14,
    d_window: int = 3,
) -> pd.DataFrame:
    """Stochastic Oscillator. Returns ``stoch_k`` and ``stoch_d`` (%)."""
    low_min = df["low"].rolling(k_window, min_periods=k_window).min()
    high_max = df["high"].rolling(k_window, min_periods=k_window).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    d = k.rolling(d_window, min_periods=d_window).mean()
    return pd.DataFrame({"stoch_k": k, "stoch_d": d})


def williams_r(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Williams %R (ranges -100 .. 0)."""
    high_max = df["high"].rolling(window, min_periods=window).max()
    low_min = df["low"].rolling(window, min_periods=window).min()
    wr = -100 * (high_max - df["close"]) / (high_max - low_min).replace(0, np.nan)
    return wr


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------
def bollinger_bands(
    series: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Bollinger Bands. Returns ``bb_mid``, ``bb_upper``, ``bb_lower``, ``bb_pct``."""
    mid = sma(series, window)
    std = series.rolling(window, min_periods=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    pct_b = (series - lower) / (upper - lower).replace(0, np.nan)
    return pd.DataFrame(
        {"bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "bb_pct": pct_b}
    )


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Average True Range (Wilder)."""
    tr = _true_range(df)
    return tr.ewm(alpha=1 / window, adjust=False).mean()


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------
def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(df["close"].diff()).fillna(0.0)
    return (direction * df["volume"]).cumsum()


def cmf(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Chaikin Money Flow."""
    hl = (df["high"] - df["low"]).replace(0, np.nan)
    mf_mult = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / hl
    mf_vol = mf_mult.fillna(0.0) * df["volume"]
    return (
        mf_vol.rolling(window, min_periods=window).sum()
        / df["volume"].rolling(window, min_periods=window).sum()
    )


# ---------------------------------------------------------------------------
# Convenience: attach everything
# ---------------------------------------------------------------------------
def add_all(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with a standard set of indicator columns added."""
    out = df.copy()
    close = out["close"]

    out["sma_20"] = sma(close, 20)
    out["sma_50"] = sma(close, 50)
    out["sma_200"] = sma(close, 200)
    out["ema_20"] = ema(close, 20)
    out["ema_50"] = ema(close, 50)

    out = out.join(macd(close))
    out = out.join(adx(out))

    out["rsi_14"] = rsi(close, 14)
    out = out.join(stochastic(out))
    out["williams_r"] = williams_r(out)

    out = out.join(bollinger_bands(close))
    out["atr_14"] = atr(out, 14)

    out["obv"] = obv(out)
    out["cmf_20"] = cmf(out, 20)
    return out
