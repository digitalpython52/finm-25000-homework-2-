"""Reusable long-only backtesting engine.

Assumptions (per assignment):
    * Initial capital: $100,000
    * Long-only, no leverage, no short-selling (target position in {0, 1})
    * Signals are executed on the *next* bar's close (1-day lag) to avoid
      look-ahead bias.
    * Optional proportional commission on traded notional.

The engine consumes a target-position Series (0/1) and the price DataFrame,
and produces a :class:`BacktestResult` exposing the equity curve, daily
returns, and the list of executed round-trip trades.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config


@dataclass
class BacktestResult:
    equity: pd.Series                 # portfolio value over time
    returns: pd.Series                # daily portfolio returns
    position: pd.Series               # executed position (0/1), lagged
    trades: pd.DataFrame              # round-trip trades
    name: str = "Strategy"
    initial_capital: float = config.INITIAL_CAPITAL

    @property
    def n_trades(self) -> int:
        return len(self.trades)


def _build_trades(
    dates: pd.DatetimeIndex,
    price: pd.Series,
    position: pd.Series,
) -> pd.DataFrame:
    """Reconstruct round-trip trades from an executed position series."""
    pos = position.to_numpy()
    px = price.to_numpy()
    records = []
    entry_i = None
    for i in range(len(pos)):
        if entry_i is None and pos[i] == 1:
            entry_i = i
        elif entry_i is not None and pos[i] == 0:
            records.append((entry_i, i))
            entry_i = None
    if entry_i is not None:  # still open at the end -> close on last bar
        records.append((entry_i, len(pos) - 1))

    rows = []
    for a, b in records:
        entry_px, exit_px = px[a], px[b]
        ret = exit_px / entry_px - 1.0
        rows.append(
            {
                "entry_date": dates[a],
                "exit_date": dates[b],
                "entry_price": entry_px,
                "exit_price": exit_px,
                "return": ret,
                "win": ret > 0,
                "bars_held": b - a,
            }
        )
    return pd.DataFrame(rows)


def run_backtest(
    df: pd.DataFrame,
    target_position: pd.Series,
    name: str = "Strategy",
    initial_capital: float = config.INITIAL_CAPITAL,
    commission: float = config.COMMISSION,
    execution_lag: int = 1,
) -> BacktestResult:
    """Backtest a 0/1 target-position series against price data.

    Parameters
    ----------
    df : DataFrame
        Must contain a ``close`` column.
    target_position : Series
        Desired position (0 or 1) decided using info available on each bar.
    execution_lag : int
        Bars between decision and execution (1 = trade next bar -> no look-ahead).
    """
    price = df["close"].astype(float)
    target = target_position.reindex(df.index).fillna(0.0).clip(0, 1)

    # Execute on the next bar: the position we actually hold today was decided
    # using data through yesterday.
    position = target.shift(execution_lag).fillna(0.0)

    asset_ret = price.pct_change().fillna(0.0)

    # Strategy daily return before costs = yesterday's held position * today's
    # asset return.
    strat_ret = position * asset_ret

    # Commission charged on the day a position changes (turnover * commission).
    turnover = position.diff().abs().fillna(position.abs())
    cost = turnover * commission
    net_ret = strat_ret - cost

    equity = initial_capital * (1.0 + net_ret).cumprod()
    equity.name = name

    trades = _build_trades(df.index, price, position)

    return BacktestResult(
        equity=equity,
        returns=net_ret,
        position=position,
        trades=trades,
        name=name,
        initial_capital=initial_capital,
    )


def buy_and_hold(
    df: pd.DataFrame,
    name: str = "Buy & Hold",
    initial_capital: float = config.INITIAL_CAPITAL,
) -> BacktestResult:
    """Benchmark: invest fully on the first bar and hold."""
    target = pd.Series(1.0, index=df.index)
    res = run_backtest(
        df, target, name=name, initial_capital=initial_capital,
        commission=0.0, execution_lag=0,
    )
    return res
