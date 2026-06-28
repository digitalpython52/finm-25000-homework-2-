"""Trading strategies.

Each strategy is a function that takes an OHLCV DataFrame and returns a
*target position* Series of 0 / 1 (long-only: 1 = fully invested, 0 = cash),
aligned to the input index. Positions are generated with an explicit
entry/exit state machine so a position is *held* between an entry signal and
the next exit signal (rather than re-evaluated as an instantaneous threshold
every day).

The backtest engine is responsible for execution lag (it trades on the bar
*after* the signal), so these functions may use same-bar indicator values.

Strategies
----------
1. Trend Following  : MACD, ADX, Moving Average            (trend)
2. Mean Reversion   : RSI, Bollinger Bands                 (momentum + volatility)
3. Custom           : SMA trend + RSI momentum + CMF volume (trend+momentum+volume)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind


def _positions_from_signals(
    index: pd.Index, entries: pd.Series, exits: pd.Series
) -> pd.Series:
    e = entries.reindex(index).fillna(False).to_numpy(dtype=bool)
    x = exits.reindex(index).fillna(False).to_numpy(dtype=bool)
    pos = np.zeros(len(index), dtype=float)
    holding = False
    for i in range(len(index)):
        if holding and x[i]:
            holding = False
        elif (not holding) and e[i]:
            holding = True
        pos[i] = 1.0 if holding else 0.0
    return pd.Series(pos, index=index, name="position")


# ---------------------------------------------------------------------------
# Strategy 1: Trend Following
# ---------------------------------------------------------------------------
def trend_following(
    df: pd.DataFrame,
    adx_threshold: float = 25.0,
    ma_window: int = 200,
) -> pd.Series:
    """Buy when MACD > signal AND ADX > 25 AND price > long MA; exit on MACD cross down.

    Combines MACD (momentum of trend), ADX (trend strength) and a long moving
    average (regime filter) so we only take longs in confirmed up-trends.
    """
    close = df["close"]
    macd_df = ind.macd(close)
    adx_df = ind.adx(df)
    long_ma = ind.sma(close, ma_window)

    macd_up = macd_df["macd"] > macd_df["macd_signal"]
    strong = adx_df["adx"] > adx_threshold
    above_ma = close > long_ma

    entries = macd_up & strong & above_ma
    exits = ~macd_up  # MACD crosses back below signal
    return _positions_from_signals(df.index, entries, exits)


# ---------------------------------------------------------------------------
# Strategy 2: Mean Reversion
# ---------------------------------------------------------------------------
def mean_reversion(
    df: pd.DataFrame,
    rsi_low: float = 30.0,
    rsi_high: float = 70.0,
) -> pd.Series:
    """Buy when RSI < 30 AND price below lower Bollinger Band.

    Exit when RSI > 70 OR price above upper Bollinger Band (mean reverted).
    """
    close = df["close"]
    rsi_ = ind.rsi(close, 14)
    bb = ind.bollinger_bands(close)

    entries = (rsi_ < rsi_low) & (close < bb["bb_lower"])
    exits = (rsi_ > rsi_high) | (close > bb["bb_upper"])
    return _positions_from_signals(df.index, entries, exits)


# ---------------------------------------------------------------------------
# Strategy 3: Custom (multi-factor) -- trend + momentum + volume
# ---------------------------------------------------------------------------
def custom_multifactor(
    df: pd.DataFrame,
    sma_window: int = 50,
    rsi_floor: float = 50.0,
    rsi_ceiling: float = 75.0,
) -> pd.Series:
    """Custom multi-factor trend-momentum-volume strategy.

    Rationale: ride established up-trends only while momentum and money flow
    confirm participation, and step aside when any pillar breaks down.

    Entry (all true):
        * Trend   : close > SMA(50)            -> established up-trend
        * Momentum: 50 < RSI(14) < 75          -> healthy, not yet exhausted
        * Volume  : CMF(20) > 0                -> net accumulation

    Exit (any true):
        * close < SMA(50)                      -> trend break
        * RSI(14) > 75                         -> momentum exhaustion / overbought
        * CMF(20) < 0                          -> distribution
    """
    close = df["close"]
    sma_ = ind.sma(close, sma_window)
    rsi_ = ind.rsi(close, 14)
    cmf_ = ind.cmf(df, 20)

    trend_up = close > sma_
    momentum_ok = (rsi_ > rsi_floor) & (rsi_ < rsi_ceiling)
    volume_ok = cmf_ > 0

    entries = trend_up & momentum_ok & volume_ok
    exits = (close < sma_) | (rsi_ > rsi_ceiling) | (cmf_ < 0)
    return _positions_from_signals(df.index, entries, exits)


# Registry used by the runner / report.
STRATEGIES = {
    "Trend Following": trend_following,
    "Mean Reversion": mean_reversion,
    "Custom Multi-Factor": custom_multifactor,
}
