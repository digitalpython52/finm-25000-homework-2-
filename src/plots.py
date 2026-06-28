"""Visualizations: price chart with indicators & signals, equity-curve
comparison, and drawdown comparison.

All functions save a PNG to ``charts/`` and return the file path.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config, indicators as ind
from .backtest import BacktestResult
from .metrics import drawdown_series

plt.rcParams.update({"figure.autolayout": True, "axes.grid": True, "grid.alpha": 0.3})

_COLORS = {
    "Buy & Hold": "#444444",
    "Trend Following": "#1f77b4",
    "Mean Reversion": "#d62728",
    "Custom Multi-Factor": "#2ca02c",
}


def _signal_points(position: pd.Series):
    """Return (buy_dates, sell_dates) where the executed position flips."""
    change = position.diff().fillna(position)
    buys = position.index[change > 0]
    sells = position.index[change < 0]
    return buys, sells


def price_chart(
    df: pd.DataFrame,
    result: BacktestResult,
    ticker: str,
    strategy_name: str,
    filename: str | None = None,
) -> Path:
    """Price + indicators (SMA, Bollinger Bands) with buy/sell markers, plus
    RSI and MACD sub-panels."""
    close = df["close"]
    sma50 = ind.sma(close, 50)
    sma200 = ind.sma(close, 200)
    bb = ind.bollinger_bands(close)
    rsi_ = ind.rsi(close, 14)
    macd_df = ind.macd(close)

    buys, sells = _signal_points(result.position)

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(13, 10), sharex=True,
        gridspec_kw={"height_ratios": [3, 1, 1]},
    )

    ax1.plot(df.index, close, color="black", lw=1.1, label="Close")
    ax1.plot(df.index, sma50, color="#1f77b4", lw=1.0, label="SMA 50")
    ax1.plot(df.index, sma200, color="#ff7f0e", lw=1.0, label="SMA 200")
    ax1.plot(df.index, bb["bb_upper"], color="grey", lw=0.8, ls="--", alpha=0.7)
    ax1.plot(df.index, bb["bb_lower"], color="grey", lw=0.8, ls="--", alpha=0.7,
             label="Bollinger 20,2")
    ax1.fill_between(df.index, bb["bb_lower"], bb["bb_upper"], color="grey", alpha=0.08)

    ax1.scatter(buys, close.reindex(buys), marker="^", color="green", s=70,
                zorder=5, label="Buy")
    ax1.scatter(sells, close.reindex(sells), marker="v", color="red", s=70,
                zorder=5, label="Sell")
    ax1.set_title(f"{ticker} — Price, Indicators & Signals ({strategy_name})")
    ax1.set_ylabel("Price ($)")
    ax1.legend(loc="upper left", fontsize=8, ncol=2)

    ax2.plot(df.index, rsi_, color="#9467bd", lw=1.0)
    ax2.axhline(70, color="red", lw=0.7, ls="--")
    ax2.axhline(30, color="green", lw=0.7, ls="--")
    ax2.set_ylabel("RSI(14)")
    ax2.set_ylim(0, 100)

    ax3.plot(df.index, macd_df["macd"], color="#1f77b4", lw=1.0, label="MACD")
    ax3.plot(df.index, macd_df["macd_signal"], color="#d62728", lw=1.0, label="Signal")
    ax3.bar(df.index, macd_df["macd_hist"], color="grey", alpha=0.4, width=1.0)
    ax3.set_ylabel("MACD")
    ax3.legend(loc="upper left", fontsize=8)
    ax3.xaxis.set_major_locator(mdates.YearLocator())
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fname = filename or f"price_{ticker}_{strategy_name.replace(' ', '_')}.png"
    path = config.CHARTS_DIR / fname
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def equity_curve(
    results: dict[str, BacktestResult],
    ticker: str,
    filename: str = "equity_curve.png",
) -> Path:
    """Overlay equity curves for Buy & Hold + all strategies."""
    fig, ax = plt.subplots(figsize=(13, 6))
    for name, res in results.items():
        ax.plot(res.equity.index, res.equity, lw=1.4,
                color=_COLORS.get(name), label=name)
    ax.set_title(f"{ticker} — Equity Curve Comparison (start ${config.INITIAL_CAPITAL:,.0f})")
    ax.set_ylabel("Portfolio Value ($)")
    ax.legend(loc="upper left", fontsize=9)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    path = config.CHARTS_DIR / filename
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def drawdown_chart(
    results: dict[str, BacktestResult],
    ticker: str,
    filename: str = "drawdown.png",
) -> Path:
    """Overlay drawdown curves for Buy & Hold + all strategies."""
    fig, ax = plt.subplots(figsize=(13, 6))
    for name, res in results.items():
        dd = drawdown_series(res.equity) * 100
        ax.plot(dd.index, dd, lw=1.2, color=_COLORS.get(name), label=name)
        ax.fill_between(dd.index, dd, 0, color=_COLORS.get(name), alpha=0.06)
    ax.set_title(f"{ticker} — Drawdown Comparison")
    ax.set_ylabel("Drawdown (%)")
    ax.legend(loc="lower left", fontsize=9)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    path = config.CHARTS_DIR / filename
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
