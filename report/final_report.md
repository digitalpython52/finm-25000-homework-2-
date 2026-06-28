# Technical-Analysis Strategy Backtest — AAPL

- **Sample:** 2020-06-24 → 2026-06-26 (1509 trading days)
- **Initial capital:** $100,000
- **Engine:** long-only, no leverage, no shorting, next-bar execution.

## Strategy Descriptions & Rules

### Buy & Hold  _(Benchmark)_

Benchmark. Invest the full $100,000 on the first available bar and hold to the end. No timing, fully exposed at all times.

- **Entry:** Buy 100% on day 1.
- **Exit:** Never (held to end of sample).

### Trend Following  _(Trend)_

Rides confirmed up-trends by combining a momentum-of-trend signal (MACD), a trend-strength filter (ADX) and a long-term regime filter (200-day SMA).

- **Entry:** MACD line > MACD signal AND ADX(14) > 25 AND Close > SMA(200).
- **Exit:** MACD line crosses back below its signal line.

### Mean Reversion  _(Momentum + Volatility)_

Buys statistically cheap dips and sells the snap-back, on the premise that price reverts to its 20-day mean.

- **Entry:** RSI(14) < 30 AND Close < lower Bollinger Band (20, 2).
- **Exit:** RSI(14) > 70 OR Close > upper Bollinger Band (20, 2).

### Custom Multi-Factor  _(Trend + Momentum + Volume)_

Multi-factor strategy spanning three indicator categories. It only holds when trend, momentum and money-flow all agree, and steps aside the moment any pillar breaks.

- **Entry:** Close > SMA(50) [trend] AND 50 < RSI(14) < 75 [momentum] AND CMF(20) > 0 [volume].
- **Exit:** Close < SMA(50) OR RSI(14) > 75 OR CMF(20) < 0.

## Performance Comparison

|                     | Total Return   | CAGR   | Volatility   |   Sharpe |   Sortino | Max Drawdown   | Win Rate   |   Trades |
|:--------------------|:---------------|:-------|:-------------|---------:|----------:|:---------------|:-----------|---------:|
| Buy & Hold          | 225.6%         | 21.8%  | 28.9%        |     0.83 |      1.23 | -33.4%         | 100.0%     |        1 |
| Trend Following     | 20.2%          | 3.1%   | 9.8%         |     0.36 |      0.52 | -11.7%         | 52.9%      |       34 |
| Mean Reversion      | 26.4%          | 4.0%   | 13.5%        |     0.36 |      0.56 | -23.0%         | 83.3%      |        6 |
| Custom Multi-Factor | 34.5%          | 5.1%   | 14.7%        |     0.41 |      0.61 | -26.7%         | 37.3%      |       67 |

## Discussion of Results

Over the test window on AAPL, the highest total return was delivered by 'Buy & Hold' and the best risk-adjusted return (Sharpe) by 'Buy & Hold'. The shallowest maximum drawdown belonged to 'Trend Following'.

Buy & Hold returned 225.6% with a Sharpe of 0.83 and a max drawdown of -33.4%. It is a demanding benchmark for a single strong-trending stock because the active strategies sit in cash for long stretches and therefore forgo upside, but they also tend to trim the deepest drawdowns relative to full exposure.

Among the active strategies, 'Custom Multi-Factor' traded most often (67 round trips) while 'Mean Reversion' traded least (6). More trading is not inherently better: a higher win rate on few trades can still trail a lower win rate on many, depending on the size of the winners. Trend Following only engages in confirmed up-trends (MACD, ADX and the 200-day SMA must all align), which keeps it out of choppy regimes. Mean Reversion needs price to actually revert to its 20-day mean, so on a persistent up-trend its oversold entries are infrequent and can be early. The Custom Multi-Factor strategy seeks a middle ground — holding while trend, momentum and money-flow agree and de-risking the moment any pillar breaks.

Caveats: results assume next-bar execution (no look-ahead), no leverage, long-only positions, and (by default) zero commission/slippage. Indicator parameters are fixed, not optimized, so these figures describe behaviour rather than a tuned, deployable system. Past performance does not guarantee future results.
