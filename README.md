# FINM 25000 — Homework 2: Technical-Analysis Strategy Backtester

An end-to-end Python toolkit that downloads historical market data from
**Alpaca**, computes **11 technical indicators**, runs **three rule-based
trading strategies** (plus a Buy & Hold benchmark) through a reusable
**long-only backtesting engine**, and produces a full set of **charts** and a
**PDF report**.

---

## Features

| Requirement | Where |
|---|---|
| ≥ 5 yrs daily OHLCV from Alpaca, user-selectable ticker, in a DataFrame | `src/data.py` |
| ≥ 6 indicators (11 implemented) | `src/indicators.py` |
| Trend-Following, Mean-Reversion, Custom strategies | `src/strategies.py` |
| Reusable backtest engine ($100k, long-only, no leverage/short) | `src/backtest.py` |
| Total Return, CAGR, Vol, Sharpe, Sortino, Max DD, Win Rate | `src/metrics.py` |
| Price/indicator/signal, equity-curve & drawdown charts | `src/plots.py` |
| Final report (PDF + Markdown) | `src/report.py` |

### Indicators
- **Trend:** SMA, EMA, MACD, ADX
- **Momentum:** RSI, Stochastic Oscillator, Williams %R
- **Volatility:** Bollinger Bands, ATR
- **Volume:** OBV, Chaikin Money Flow (CMF)

### Strategies
1. **Trend Following** — *Buy* when `MACD > Signal` **and** `ADX(14) > 25` **and**
   `Close > SMA(200)`; *Sell* when MACD crosses back below its signal.
2. **Mean Reversion** — *Buy* when `RSI(14) < 30` **and** `Close < lower Bollinger
   Band`; *Sell* when `RSI(14) > 70` **or** `Close > upper Bollinger Band`.
3. **Custom Multi-Factor** (trend + momentum + volume) — *Buy* when
   `Close > SMA(50)` **and** `50 < RSI(14) < 75` **and** `CMF(20) > 0`; *Sell*
   when `Close < SMA(50)` **or** `RSI(14) > 75` **or** `CMF(20) < 0`.

---

## Setup

```bash
pip install -r requirements.txt
```

**Alpaca credentials** are read from environment variables or a git-ignored
`.env` file in the project root:

```bash
# .env
APCA_API_KEY_ID=your_key_id
APCA_API_SECRET_KEY=your_secret_key
```

A free Alpaca account works (free plans can't query the most recent ~15 min of
SIP data, so the downloader automatically backs the end time off — daily bars
are unaffected).

---

## Usage

```bash
# Default ticker (AAPL), 6 years of history
python main.py

# Pick a ticker
python main.py --ticker NVDA
python main.py -t SPY --years 7

# Interactive ticker selection
python main.py --interactive

# Force a fresh API pull (ignore the local cache)
python main.py --ticker AAPL --refresh
```

The pipeline prints the performance table and writes:

```
charts/equity_curve.png
charts/drawdown.png
charts/price_<TICKER>_<Strategy>.png   (one per strategy)
report/final_report.pdf
report/final_report.md
```

Downloads are cached under `data_cache/` so re-runs are instant.

---

## Backtest assumptions

- Initial capital **$100,000**, **long-only**, **no leverage**, **no shorting**
  (target position ∈ {0, 1}).
- Signals execute on the **next bar's close** (1-day lag) to avoid look-ahead.
- Commission/slippage default to **0** (configurable in `src/config.py`).
- Data is **split- and dividend-adjusted** (`Adjustment.ALL`).

---

## Example results (AAPL, 2020-06 → 2026-06)

| Strategy | Total Return | CAGR | Sharpe | Sortino | Max Drawdown |
|---|---|---|---|---|---|
| Buy & Hold | 225.6% | 21.8% | 0.83 | 1.23 | -33.4% |
| Trend Following | 20.2% | 3.1% | 0.36 | 0.52 | -11.7% |
| Mean Reversion | 26.4% | 4.0% | 0.36 | 0.56 | -23.0% |
| Custom Multi-Factor | 34.5% | 5.1% | 0.41 | 0.61 | -26.7% |

> Figures regenerate every run from live Alpaca data and will drift with new
> bars. See `report/final_report.pdf` for the full report. Buy & Hold is a hard
> benchmark on a single strong-trending name; the active strategies trade
> infrequently and hold cash for long stretches by design.

---

## Project structure

```
finm-25000-homework-2-/
├── main.py                 # CLI entry point / full pipeline
├── requirements.txt
├── README.md
├── src/
│   ├── config.py           # paths, assumptions, credential loading
│   ├── data.py             # Alpaca download + caching
│   ├── indicators.py       # 11 technical indicators
│   ├── strategies.py       # 3 strategy signal generators
│   ├── backtest.py         # reusable long-only engine
│   ├── metrics.py          # performance metrics
│   ├── plots.py            # price / equity / drawdown charts
│   └── report.py           # PDF + Markdown report
├── charts/                 # generated PNGs
├── report/                 # generated final_report.pdf / .md
└── data_cache/             # cached downloads (git-ignored)
```

---

*Educational project. Not investment advice; past performance does not
guarantee future results.*
