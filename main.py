"""FINM 25000 — Homework 2: Technical-Analysis Strategy Backtester.

End-to-end pipeline:
    1. Download >= 5 years of daily OHLCV for a user-selected ticker (Alpaca).
    2. Compute technical indicators.
    3. Run three rule-based strategies + a Buy & Hold benchmark.
    4. Report performance metrics and build the comparison charts + PDF report.

Usage
-----
    python main.py                       # default ticker (AAPL), interactive if -i
    python main.py --ticker NVDA
    python main.py --ticker SPY --years 7 --refresh
    python main.py --interactive         # prompt for a ticker
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from src import config, data as data_mod
from src import strategies as strat
from src import backtest as bt
from src import plots, report
from src.metrics import metrics_table


def select_ticker_interactive() -> str:
    print("\nSelect a ticker:")
    for i, t in enumerate(config.DEFAULT_TICKERS, 1):
        print(f"  {i}. {t}")
    print("  (or type any other symbol)")
    choice = input(f"Ticker [{config.DEFAULT_TICKER}]: ").strip()
    if not choice:
        return config.DEFAULT_TICKER
    if choice.isdigit() and 1 <= int(choice) <= len(config.DEFAULT_TICKERS):
        return config.DEFAULT_TICKERS[int(choice) - 1]
    return choice.upper()


def run(ticker: str, years: int, refresh: bool) -> None:
    pd.set_option("display.width", 120)
    print(f"\n[1/5] Downloading {years}y of daily data for {ticker} …")
    df = data_mod.download(ticker, years=years, refresh=refresh)
    start, end = df.index[0].date().isoformat(), df.index[-1].date().isoformat()
    print(f"      {len(df)} bars  ({start} → {end})")

    print("[2/5] Running strategies + Buy & Hold benchmark …")
    results: dict[str, bt.BacktestResult] = {
        "Buy & Hold": bt.buy_and_hold(df, name="Buy & Hold"),
    }
    for name, fn in strat.STRATEGIES.items():
        position = fn(df)
        results[name] = bt.run_backtest(df, position, name=name)
        print(f"      {name:<22} trades={results[name].n_trades}")

    print("[3/5] Computing performance metrics …")
    table = metrics_table(results)
    disp = report.format_table(table)
    print("\n" + disp.to_string())

    print("\n[4/5] Building charts …")
    chart_paths = {
        "equity": plots.equity_curve(results, ticker),
        "drawdown": plots.drawdown_chart(results, ticker),
    }
    for name in strat.STRATEGIES:
        p = plots.price_chart(df, results[name], ticker, name)
        chart_paths[f"price:{name}"] = p
    for k, v in chart_paths.items():
        print(f"      {v}")

    print("[5/5] Writing final report …")
    pdf_path, md_path = report.build_report(
        ticker, results, chart_paths, n_obs=len(df), start=start, end=end
    )
    print(f"      {pdf_path}")
    print(f"      {md_path}")
    print("\nDone.\n")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Technical-analysis strategy backtester")
    p.add_argument("-t", "--ticker", default=None,
                   help=f"Equity symbol (default {config.DEFAULT_TICKER})")
    p.add_argument("-y", "--years", type=int, default=config.YEARS_OF_HISTORY,
                   help="Years of history to download (>= 5)")
    p.add_argument("-i", "--interactive", action="store_true",
                   help="Prompt for a ticker interactively")
    p.add_argument("--refresh", action="store_true",
                   help="Force a fresh API download (ignore cache)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.interactive:
        ticker = select_ticker_interactive()
    else:
        ticker = (args.ticker or config.DEFAULT_TICKER).upper()
    try:
        run(ticker, years=args.years, refresh=args.refresh)
    except Exception as exc:  # surface a clean message
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
