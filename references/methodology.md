# A-Share Stock Timing Methodology

## Contents

1. Principles
2. Participant behavior map
3. Data quality hierarchy
4. Market and sector filters
5. Individual trend model
6. Volume/fund/chip interpretation
7. Buy setups
8. Sell setups
9. Risk and position sizing
10. Scoring model
11. One-vote veto rules

## 1. Principles

- Prefer multi-evidence confirmation over any single indicator.
- Use "market regime -> sector strength -> stock trend -> volume/funds -> chips -> risk plan" in that order.
- Buy only when uncertainty has decreased and stop distance is acceptable.
- Sell when the original hypothesis fails, distribution evidence appears, or risk/reward deteriorates.
- Separate the analysis horizon:
  - Intraday/1-3 days: VWAP, opening auction, limit-up ecology, Dragon Tiger list, theme breadth.
  - Short swing/2-10 days: MA5/MA10, breakout follow-through, volume continuation, sector heat.
  - Medium swing/2-8 weeks: MA20/MA60, 20/55-day highs, pullback quality, weekly structure.
  - Position trend/2-6 months: MA60/MA120/MA250, sector cycle, institutional ownership proxies.

## 2. Participant Behavior Map

| Participant | Typical behavior | Useful evidence | Trap |
|---|---|---|---|
| Retail | Chases hot themes, reacts to headlines, sells into fear | sudden turnover, late-stage volume expansion, social heat | often appears strongest near distribution |
| Hot money/游资 | short-term theme leadership, limit-up relay, fast exit | Dragon Tiger list, limit-up quality, opening auction, board breadth | list is delayed and seats can sell next day |
| Public funds | industry allocation, liquidity preference, ranking pressure | periodic fund reports, institutional holdings, large-cap trend | disclosure lag |
| Private/quant | statistical trading, intraday liquidity, factor crowding | mean reversion, high turnover, abnormal intraday oscillation | difficult to infer from public data |
| Margin funds | leveraged trend reinforcement | financing balance, financing purchases, price-financing combinations | high-level leverage can become forced selling |
| Northbound/ETF | allocation flows and index-related trading | stock connect holdings, active list, ETF turnover | live net-flow disclosure changed; avoid old "real-time northbound" assumptions |
| Industrial capital | reduction, buyback, pledge, unlock, block transfer | announcements, block trades, unlock schedule | supply events can dominate technicals |

## 3. Data Quality Hierarchy

| Tier | Data | Use | Caution |
|---|---|---|---|
| A | exchange OHLCV, amount, turnover | trend, volume, liquidity | ensure consistent adjustment |
| A | margin financing/securities lending | leveraged sentiment | combine with price, not standalone |
| A | Dragon Tiger list | short-term seat behavior | delayed and selective |
| A | block trades | large chip transfer | discount does not always mean bearish |
| A | shareholder count, top float holders | chip concentration | reported with lag |
| B | stock connect holdings/active list | external allocation proxy | not an intraday signal |
| B | fund holdings | institutional ownership | quarterly lag |
| C | vendor large-order flow/main-force net inflow | supplementary microstructure clue | algorithm-dependent estimate |
| C | chip distribution/cost curve | support/resistance approximation | usually model-estimated |
| D | rumors/social posts | sentiment/crowding | never use as fact |

## 4. Market and Sector Filters

### Market Regime

Classify before analyzing the stock:

- **Trend regime**: broad index above MA20/MA60, MA20 rising, turnover above 20-day average, breadth positive. Favor breakouts and pullbacks.
- **Range regime**: broad index oscillates around MA60, turnover inconsistent, rotation fast. Favor support buys and faster profit-taking.
- **Downtrend regime**: broad index below MA60/MA120, moving averages falling, weak breadth. Stay defensive; only strongest leaders or no trade.

Use broad indices appropriate to the stock: CSI 300 for large caps, CSI 500/1000 or all-A index for mid/small caps, ChiNext/Kechuang indices for growth boards, Beijing Stock Exchange index for BSE names.

### Sector Strength

Use at least two:

- sector return minus benchmark return over 20/60 days;
- sector index above MA20/MA60 with rising slope;
- sector turnover ranking in the top 30%;
- number of sector constituents making 20/55-day highs;
- leader strength vs follow-through of second-tier names;
- sector pullbacks on shrinking volume.

Reduce position size if the stock is strong but the sector is weak. Avoid late-stage laggards after sector leaders distribute.

## 5. Individual Trend Model

Classify phase:

| Phase | Evidence | Action |
|---|---|---|
| Downtrend | below MA60/MA120, rallies fail at MA20/MA60 | avoid right-side buys |
| Base | volatility contraction, volume dries, lows stabilize | wait for breakout or second entry |
| Early uptrend | range breakout, MA20/MA60 flatten and turn up | best risk/reward zone |
| Main uptrend | MA20 rising, pullbacks hold MA10/MA20, sector confirms | hold and trail |
| High-level range | large advance, turnover expands, upper shadows | trim and tighten stops |
| Distribution/downtrend | volume break, weak rebound, MA20/MA60 roll over | exit |

Core indicators:

- MA20: swing life line.
- MA60: trend boundary.
- MA120/MA250: long-term trend and institutional cost proxy.
- 20/55-day high: breakout confirmation.
- ATR14/ATR%: stop distance and volatility regime.
- MACD: trend confirmation only.
- RSI: use for divergence/extremes; do not sell strong trends solely because RSI is high.
- Relative strength: stock vs sector and stock vs broad benchmark.

## 6. Volume, Fund, and Chip Interpretation

### Healthy Accumulation Chain

- decline slows, lows stop expanding downward;
- volume contracts during weakness and expands on up days;
- price resists market weakness;
- OBV/CMF improves before price;
- base has sufficient cumulative turnover while price center does not fall;
- shareholder count decreases or holder concentration increases if disclosed;
- breakout volume is strong but not exhaustion-level;
- pullback after breakout is shallow and on lower volume.

### Distribution Chain

- high-level volume explodes but price stops rising;
- repeated upper shadows and failed breakouts;
- turnover enters extreme historical percentile;
- financing balance rises sharply while price stalls;
- shareholder count rises or chips spread;
- Dragon Tiger list shows concentrated hot money but next-day support is weak;
- breaks MA20, rebounds on low volume, then breaks MA60.

### Margin Financing Matrix

| Price | Financing balance | Interpretation |
|---|---|---|
| rising | mild rise | leveraged confirmation, usually constructive |
| rising | rapid rise | crowded; chase less |
| flat | rapid rise | leverage builds without price progress; risk |
| falling | rising | trapped leverage; beware forced selling |
| falling | falling | deleveraging; pressure but risk release |

### Chip/Control Evidence

Infer "control" only through observable chip behavior:

- 20-60 trading-day base with narrowing amplitude;
- cumulative turnover 100%-300% within range without breakdown;
- up-day amount/down-day amount ratio above 1.2;
- support tests at MA20/range top with lower volume;
- shareholder count falls or top float holder concentration rises;
- breakout closes near day high on 1.5-3.0x 20-day amount;
- avoid illiquid "庄股" patterns: very low turnover, unnatural smoothness, no diverse liquidity, sudden gap risk.

### Chip Distribution / CYQ Proxy Layer

Use `scripts/estimate_chip_distribution.py` when daily OHLCV with turnover/amount is available. Treat the output as a local cost-distribution proxy:

- `low_cost_concentration_base`: high-value watch condition, not an automatic buy;
- `support_peaks_below_close`: likely cost support zones for pullback planning;
- `resistance_peaks_above_close`: overhead supply zones that can cap rebounds;
- `profit_ratio`: high values after large advances increase profit-taking risk;
- `concentration_70_width_pct`: narrower cost width means more unified market cost, but it can be bullish at low levels and bearish at high levels.

Significant rule upgrade:

`market/sector filter -> chip lifecycle -> trend trigger -> volume/main-force confirmation -> risk plan`

Prefer this sequence over using moving-average crossover alone. A concentrated low-cost peak is only a setup condition; the actual buy still requires a right-side breakout or a confirmed shrinking-volume pullback.

### CYQ-Informed Lifecycle Signals

| Local proxy state | Interpretation | Action |
|---|---|---|
| low-cost concentrated base | possible completed exchange of chips after long base | watch for breakout; no blind bottom-fishing |
| breakout above major cost peak | supply area converts to support if volume confirms | first buy candidate |
| pullback to broken cost peak on lower amount | confirms support and lower floating supply | second buy/add candidate |
| old low-cost peak persists during markup | possible lock-up/holding evidence | trail with trend, avoid noise selling |
| high profit ratio + high-level concentration | possible distribution/crowded profit zone | tighten stops/trim |
| dispersed multi-peak | no stable cost consensus | reduce confidence or wait |

If price rises sharply without a prior cost-distribution base and tick/DDY-like concentration fails to confirm, classify it as fast-money/theme momentum rather than institutional markup. Use shorter exits such as VWAP/MA5/previous-day-low instead of medium-swing holding rules.

### Local Main-Force Reference

When the user asks about 主力资金 or 主力控盘, use `scripts/estimate_main_force.py` if local daily/tick data is available:

- tick mode: use big+huge active net flow as a closer vendor-style main-force estimate;
- daily mode: use only as a volume-price proxy, never as factual 主力净流入;
- read tick-mode `ddx_proxy`, `ddy_absorption_proxy`, and `ddz_attack_proxy` as DDX/DDY/DDZ-style local references if available;
- require price/volume confirmation before using the signal in a buy/sell plan;
- downgrade confidence when the script reports missing amount, weak side classification, or high neutral tick amount.

## 7. Buy Setups

### A. Trend Breakout

Require:

- market regime is trend/range, not broad downtrend;
- sector is top 30% or clearly strengthening;
- close > MA20 > MA60 and both slopes rising;
- base at least 20 trading days, ideally 4-12 weeks;
- volatility contracts before breakout;
- breakout above range top or 55-day high;
- amount is 1.5-3.0x 20-day average;
- close is in the top 25% of daily range;
- relative strength line makes a new high;
- stop distance is acceptable.

Execution:

- aggressive: buy 1/3 near close after confirmed breakout;
- balanced: buy after next-day hold above range top;
- add: buy pullback to MA10/MA20 or range top with lower volume.

Invalidation:

- falls back into range within 1-3 days;
- breaks breakout-day low;
- breaks MA20 with sector weakening;
- no follow-through after volume breakout.

### B. Pullback Second Entry

Require:

- existing uptrend, price above rising MA60;
- prior advance had volume confirmation;
- pullback lasts 3-8 trading days and volume contracts;
- support at MA20, prior high, range top, trendline, or VWAP area;
- sector remains intact;
- reversal confirmation: closes above prior high, bullish reversal candle, reclaim VWAP/MA5, or strong close.

Stop:

- below pullback low or decisive MA20 loss.

### C. Bottom Reversal

Use smaller size. Require:

- long decline has slowed or false breakdown quickly recovered;
- divergence is supported by price reclaiming MA20;
- MA20 flattens/rises, then price attacks MA60 or neckline;
- a higher low forms;
- sector stabilizes.

Avoid buying the first bounce in a clear downtrend.

### D. Short-Term Limit-Up/Theme Momentum

Only for agents explicitly asked to analyze short-term trading:

- market short-term sentiment is improving: more limit-ups, fewer limit-downs;
- theme has a clear leader and breadth;
- target is leader/front-row, not late back-row laggard;
- limit-up quality is good: decisive seal, strong re-seal, next-day auction not weak;
- intraday price holds VWAP after open.

Warn that T+1 makes failed chase trades highly asymmetric.

## 8. Sell Setups

### Hard Stop

Define before entry. Common choices:

- breakout: back below range top or breakout-day low;
- pullback: below pullback low;
- trend: close below MA20 and no quick reclaim;
- reversal: below right-side confirmation low.

### Trend Failure

- close below MA20 and fails to reclaim next day;
- breaks prior swing low;
- MA20 turns down and rebound fails at MA20;
- volume break below MA60;
- relative strength breaks 20-day low;
- sector leader breaks down.

### Distribution/Profit Protection

- high-level amount > 3x 20-day average with long upper shadow;
- new price high without OBV/CMF confirmation;
- high turnover and no price progress;
- failed limit-up/board break followed by weak open;
- financing crowding while price stalls;
- stock underperforms sector on rebound.

### Trailing Exit

- ordinary swing: take partial profits at 2R, trail remainder with MA20 or 2ATR;
- strong leader: use MA10/MA20/swing low, do not guess top;
- high-volatility theme: take partial profits faster.

## 9. Risk and Position Sizing

Use risk-first sizing:

`shares = account_equity * risk_pct / abs(entry - stop)`

Then adjust to A-share board lot rules and liquidity.

Defaults:

- single-trade risk: 0.5%-1.0% of account;
- reduce size when stop distance > 8%, stock is small/illiquid, board has 20%/30% limit, or market regime is weak;
- never increase size because the analyst "feels certain";
- if limit-down risk makes the planned stop non-executable, reduce size or avoid.

## 10. 100-Point Scoring Model

| Module | Weight | Evidence |
|---|---:|---|
| Market regime | 20 | index MA structure, turnover, breadth, risk appetite |
| Sector strength | 15 | relative strength, turnover rank, leader breadth |
| Stock trend | 20 | MA stack/slope, new highs, phase, relative strength |
| Volume/fund behavior | 20 | breakout amount, pullback shrinkage, OBV/CMF/MFI, VWAP, margin/Dragon Tiger where relevant |
| Chip/control | 15 | range turnover, volatility contraction, shareholder/holder evidence, support quality |
| Risk/execution | 10 | stop distance, liquidity, announcements, unlock/reduction, limit risk |

Decision bands:

- 90-100: excellent setup, still obey risk;
- 80-89: actionable standard setup;
- 70-79: small trial or watch for confirmation;
- 60-69: watch only;
- below 60: avoid.

Confidence must be separate from score. Low data quality lowers confidence even if technical score is high.

## 11. One-Vote Veto Rules

Reject or downgrade sharply if:

- market and sector both break down;
- price below falling MA60 for right-side trend trades;
- breakout has no volume and fails to close above resistance;
- high-level volume shock with long upper shadow and next-day weak support;
- liquidity is too low for planned position;
- stop distance implies loss above risk budget;
- relevant reduction/unlock/suspension/delisting risk is not checked;
- stock is limit-up/limit-down in a way that makes intended execution unrealistic;
- analysis relies primarily on "main-force net inflow" without price/volume confirmation.
