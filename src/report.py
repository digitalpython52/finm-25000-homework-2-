"""Final report generation.

Produces:
  * ``report/final_report.pdf`` — multi-page PDF (matplotlib PdfPages, no extra
    dependencies) with strategy descriptions, entry/exit rules, the performance
    comparison table, the discussion, and all charts embedded.
  * ``report/final_report.md`` — the same narrative content as Markdown.
"""

from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from . import config
from .backtest import BacktestResult
from .metrics import metrics_table

PCT = {"Total Return", "CAGR", "Volatility", "Max Drawdown", "Win Rate"}


# ---------------------------------------------------------------------------
# Narrative content
# ---------------------------------------------------------------------------
STRATEGY_DOCS = {
    "Buy & Hold": {
        "desc": "Benchmark. Invest the full $100,000 on the first available bar "
                "and hold to the end. No timing, fully exposed at all times.",
        "entry": "Buy 100% on day 1.",
        "exit": "Never (held to end of sample).",
        "category": "Benchmark",
    },
    "Trend Following": {
        "desc": "Rides confirmed up-trends by combining a momentum-of-trend "
                "signal (MACD), a trend-strength filter (ADX) and a long-term "
                "regime filter (200-day SMA).",
        "entry": "MACD line > MACD signal AND ADX(14) > 25 AND Close > SMA(200).",
        "exit": "MACD line crosses back below its signal line.",
        "category": "Trend",
    },
    "Mean Reversion": {
        "desc": "Buys statistically cheap dips and sells the snap-back, on the "
                "premise that price reverts to its 20-day mean.",
        "entry": "RSI(14) < 30 AND Close < lower Bollinger Band (20, 2).",
        "exit": "RSI(14) > 70 OR Close > upper Bollinger Band (20, 2).",
        "category": "Momentum + Volatility",
    },
    "Custom Multi-Factor": {
        "desc": "Multi-factor strategy spanning three indicator categories. It "
                "only holds when trend, momentum and money-flow all agree, and "
                "steps aside the moment any pillar breaks.",
        "entry": "Close > SMA(50) [trend] AND 50 < RSI(14) < 75 [momentum] "
                 "AND CMF(20) > 0 [volume].",
        "exit": "Close < SMA(50) OR RSI(14) > 75 OR CMF(20) < 0.",
        "category": "Trend + Momentum + Volume",
    },
}


def _fmt(metric: str, value) -> str:
    if pd.isna(value):
        return "—"
    if metric in PCT:
        return f"{value * 100:,.1f}%"
    if metric == "Trades":
        return f"{int(value)}"
    return f"{value:,.2f}"


def format_table(table: pd.DataFrame) -> pd.DataFrame:
    """Return a display-formatted copy of the metrics table."""
    disp = table.copy()
    for col in disp.columns:
        disp[col] = [_fmt(col, v) for v in disp[col]]
    return disp


def _discussion(table: pd.DataFrame, ticker: str) -> str:
    best_sharpe = table["Sharpe"].idxmax()
    best_return = table["Total Return"].idxmax()
    smallest_dd = table["Max Drawdown"].idxmax()  # closest to 0
    bh = table.loc["Buy & Hold"]

    active = table.drop(index="Buy & Hold", errors="ignore")
    most_active = active["Trades"].idxmax()
    least_active = active["Trades"].idxmin()

    lines = [
        f"Over the test window on {ticker}, the highest total return was delivered "
        f"by '{best_return}' and the best risk-adjusted return (Sharpe) by "
        f"'{best_sharpe}'. The shallowest maximum drawdown belonged to "
        f"'{smallest_dd}'.",
        "",
        f"Buy & Hold returned {_fmt('Total Return', bh['Total Return'])} with a "
        f"Sharpe of {_fmt('Sharpe', bh['Sharpe'])} and a max drawdown of "
        f"{_fmt('Max Drawdown', bh['Max Drawdown'])}. It is a demanding benchmark "
        "for a single strong-trending stock because the active strategies sit in "
        "cash for long stretches and therefore forgo upside, but they also tend to "
        "trim the deepest drawdowns relative to full exposure.",
        "",
        f"Among the active strategies, '{most_active}' traded most often "
        f"({int(active.loc[most_active, 'Trades'])} round trips) while "
        f"'{least_active}' traded least "
        f"({int(active.loc[least_active, 'Trades'])}). More trading is not "
        "inherently better: a higher win rate on few trades can still trail a "
        "lower win rate on many, depending on the size of the winners. Trend "
        "Following only engages in confirmed up-trends (MACD, ADX and the 200-day "
        "SMA must all align), which keeps it out of choppy regimes. Mean Reversion "
        "needs price to actually revert to its 20-day mean, so on a persistent "
        "up-trend its oversold entries are infrequent and can be early. The Custom "
        "Multi-Factor strategy seeks a middle ground — holding while trend, "
        "momentum and money-flow agree and de-risking the moment any pillar breaks.",
        "",
        "Caveats: results assume next-bar execution (no look-ahead), no leverage, "
        "long-only positions, and (by default) zero commission/slippage. Indicator "
        "parameters are fixed, not optimized, so these figures describe behaviour "
        "rather than a tuned, deployable system. Past performance does not "
        "guarantee future results.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PDF page helpers
# ---------------------------------------------------------------------------
def _text_page(pdf: PdfPages, title: str, blocks: list[tuple[str, str]]):
    fig = plt.figure(figsize=(8.5, 11))
    fig.text(0.06, 0.95, title, fontsize=18, fontweight="bold", va="top")
    y = 0.89
    for heading, body in blocks:
        if heading:
            fig.text(0.06, y, heading, fontsize=12, fontweight="bold", va="top")
            y -= 0.028
        for para in body.split("\n"):
            wrapped = textwrap.wrap(para, width=95) or [""]
            for line in wrapped:
                fig.text(0.06, y, line, fontsize=9.5, va="top")
                y -= 0.020
            y -= 0.006
        y -= 0.012
        if y < 0.08:  # new page if we run out of room
            pdf.savefig(fig)
            plt.close(fig)
            fig = plt.figure(figsize=(8.5, 11))
            y = 0.93
    pdf.savefig(fig)
    plt.close(fig)


def _table_page(pdf: PdfPages, title: str, disp: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
    tbl = ax.table(
        cellText=disp.values,
        rowLabels=disp.index,
        colLabels=disp.columns,
        cellLoc="center",
        rowLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.0, 1.8)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0 or c == -1:
            cell.set_text_props(fontweight="bold")
            cell.set_facecolor("#e6eef7")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _image_page(pdf: PdfPages, image_path: Path, caption: str):
    img = plt.imread(str(image_path))
    h, w = img.shape[0], img.shape[1]
    fig = plt.figure(figsize=(11, 8.5))
    fig.set_layout_engine("none")  # add_axes is incompatible with autolayout
    ax = fig.add_axes([0.04, 0.06, 0.92, 0.86])
    ax.imshow(img)
    ax.axis("off")
    fig.text(0.5, 0.965, caption, ha="center", fontsize=13, fontweight="bold")
    pdf.savefig(fig)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def build_report(
    ticker: str,
    results: dict[str, BacktestResult],
    chart_paths: dict[str, Path],
    n_obs: int,
    start: str,
    end: str,
) -> tuple[Path, Path]:
    table = metrics_table(results)
    disp = format_table(table)
    discussion = _discussion(table, ticker)

    # ---- Markdown ----
    md_path = config.REPORT_DIR / "final_report.md"
    md = _markdown(ticker, disp, discussion, n_obs, start, end)
    md_path.write_text(md)

    # ---- PDF ----
    pdf_path = config.REPORT_DIR / "final_report.pdf"
    with PdfPages(pdf_path) as pdf:
        # Title / overview page
        _text_page(
            pdf,
            f"Technical-Analysis Strategy Backtest — {ticker}",
            [
                ("", f"Generated: {date.today().isoformat()}    |    "
                     f"Sample: {start} → {end}  ({n_obs} trading days)    |    "
                     f"Initial capital: ${config.INITIAL_CAPITAL:,.0f}"),
                ("Overview", "Five-plus years of daily OHLCV bars were pulled from "
                 "Alpaca's Historical Market Data API. Eleven indicators were "
                 "computed and four portfolios compared: a Buy & Hold benchmark "
                 "and three rule-based, long-only strategies. The engine executes "
                 "signals on the next bar (no look-ahead), uses no leverage and "
                 "never shorts."),
            ],
        )
        # Strategy descriptions + rules
        blocks = []
        for name in results:
            doc = STRATEGY_DOCS.get(name, {})
            blocks.append((
                f"{name}  [{doc.get('category', '')}]",
                f"{doc.get('desc', '')}\n"
                f"ENTRY: {doc.get('entry', '')}\n"
                f"EXIT:  {doc.get('exit', '')}",
            ))
        _text_page(pdf, "Strategy Descriptions & Rules", blocks)

        # Performance table
        _table_page(pdf, f"Performance Comparison — {ticker}", disp)

        # Discussion
        _text_page(pdf, "Discussion of Results", [("", discussion)])

        # Charts
        if "equity" in chart_paths:
            _image_page(pdf, chart_paths["equity"], "Equity Curve Comparison")
        if "drawdown" in chart_paths:
            _image_page(pdf, chart_paths["drawdown"], "Drawdown Comparison")
        for key, path in chart_paths.items():
            if key.startswith("price:"):
                _image_page(pdf, path, key.split(":", 1)[1])

    return pdf_path, md_path


def _markdown(ticker, disp, discussion, n_obs, start, end) -> str:
    md = [
        f"# Technical-Analysis Strategy Backtest — {ticker}",
        "",
        f"- **Sample:** {start} → {end} ({n_obs} trading days)",
        f"- **Initial capital:** ${config.INITIAL_CAPITAL:,.0f}",
        "- **Engine:** long-only, no leverage, no shorting, next-bar execution.",
        "",
        "## Strategy Descriptions & Rules",
        "",
    ]
    for name, doc in STRATEGY_DOCS.items():
        if name not in disp.index:
            continue
        md += [
            f"### {name}  _({doc['category']})_",
            "",
            doc["desc"],
            "",
            f"- **Entry:** {doc['entry']}",
            f"- **Exit:** {doc['exit']}",
            "",
        ]
    md += ["## Performance Comparison", "", disp.to_markdown(), "",
           "## Discussion of Results", "", discussion, ""]
    return "\n".join(md)
