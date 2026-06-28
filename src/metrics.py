"""Performance metrics for a backtest result.

Implements: Total Return, CAGR, annualized Volatility, Sharpe Ratio,
Sortino Ratio, Maximum Drawdown, and Win Rate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .backtest import BacktestResult


def drawdown_series(equity: pd.Series) -> pd.Series:
    """Drawdown at each point: equity / running-peak - 1 (<= 0)."""
    running_max = equity.cummax()
    return equity / running_max - 1.0


def max_drawdown(equity: pd.Series) -> float:
    return float(drawdown_series(equity).min())


def total_return(equity: pd.Series) -> float:
    return float(equity.iloc[-1] / equity.iloc[0] - 1.0)


def cagr(equity: pd.Series, trading_days: int = config.TRADING_DAYS) -> float:
    n_days = len(equity)
    years = max(n_days / trading_days, 1e-9)
    growth = equity.iloc[-1] / equity.iloc[0]
    if growth <= 0:
        return -1.0
    return float(growth ** (1.0 / years) - 1.0)


def annual_volatility(returns: pd.Series, trading_days: int = config.TRADING_DAYS) -> float:
    return float(returns.std(ddof=0) * np.sqrt(trading_days))


def sharpe_ratio(
    returns: pd.Series,
    risk_free: float = config.RISK_FREE_RATE,
    trading_days: int = config.TRADING_DAYS,
) -> float:
    excess = returns - risk_free / trading_days
    sd = excess.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float(excess.mean() / sd * np.sqrt(trading_days))


def sortino_ratio(
    returns: pd.Series,
    risk_free: float = config.RISK_FREE_RATE,
    trading_days: int = config.TRADING_DAYS,
) -> float:
    excess = returns - risk_free / trading_days
    downside = excess.clip(upper=0.0)
    downside_dev = np.sqrt((downside ** 2).mean())
    if downside_dev == 0 or np.isnan(downside_dev):
        return 0.0
    return float(excess.mean() / downside_dev * np.sqrt(trading_days))


def win_rate(result: BacktestResult) -> float:
    """Fraction of round-trip trades that were profitable."""
    if result.trades.empty:
        return float("nan")
    return float(result.trades["win"].mean())


def compute_metrics(result: BacktestResult) -> dict:
    """Return a dict of all headline metrics for a backtest result."""
    eq, ret = result.equity, result.returns
    return {
        "Total Return": total_return(eq),
        "CAGR": cagr(eq),
        "Volatility": annual_volatility(ret),
        "Sharpe": sharpe_ratio(ret),
        "Sortino": sortino_ratio(ret),
        "Max Drawdown": max_drawdown(eq),
        "Win Rate": win_rate(result),
        "Trades": result.n_trades,
    }


def metrics_table(results: dict[str, BacktestResult]) -> pd.DataFrame:
    """Build a comparison DataFrame: one row per strategy/result."""
    rows = {name: compute_metrics(res) for name, res in results.items()}
    return pd.DataFrame(rows).T
