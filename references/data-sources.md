# A-Share Data Routing Guide

## Contents

1. Decision rule: script or web search
2. Script-managed structured data
3. Web-search-managed current facts
4. Field normalization
5. Agent data pipeline checklist

## 1. Decision Rule: Script or Web Search

Use scripts for repeatable structured market data:

- daily OHLCV/K-line;
- amount/volume/turnover;
- repeatable indicator calculation;
- CSV normalization;
- deterministic technical score snapshots.

Use web search or official websites for current or source-sensitive facts:

- latest company announcements, reductions, buybacks, unlocks, ST/delisting, suspensions;
- latest exchange trading rules or disclosure mechanism changes;
- Dragon Tiger list explanations when precise seat names and dates matter;
- margin financing rules or official risk-control thresholds;
- northbound/Stock Connect disclosure details;
- news events that may cause gaps or limit-up/limit-down behavior;
- any fact whose freshness or official source matters.

If a script and web search disagree, prefer the authoritative/latest source and state the discrepancy.

## 2. Script-Managed Structured Data

Bundled scripts:

| Script | Purpose | Typical use |
|---|---|---|
| `scripts/fetch_eastmoney_kline.py` | fetch daily K-line CSV; default `--source auto` tries BaoStock/AKShare if installed, then Eastmoney, Tencent, Yahoo Chart | initial OHLCV data package |
| `scripts/score_ashare_timing.py` | compute MA/ATR/RSI/CMF/OBV-derived technical score from CSV | technical snapshot and consistency check |
| `scripts/estimate_main_force.py` | compute tick-based large-order net flow or daily OHLCV main-force proxy | local 主力资金 reference |
| `scripts/estimate_chip_distribution.py` | compute CYQ-style chip/cost distribution proxy from daily OHLCV | local 筹码分布 reference |

Example:

```powershell
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/fetch_eastmoney_kline.py 600519 --start 20230101 --end 20260425 --adjust qfq --source auto --output 600519_daily.csv
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/score_ashare_timing.py 600519_daily.csv --entry 1800 --stop 1700
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/estimate_main_force.py 600519_daily.csv --mode daily --json
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/estimate_chip_distribution.py 600519_daily.csv --lookback 250 --json
```

The fetch script writes canonical English columns:

`date, open, close, high, low, volume, amount, amplitude_pct, pct_change, change, turnover`

If optional dependencies are installed, `--source auto` tries BaoStock first, then AKShare. Install with `pip install -r requirements-optional.txt`.

BaoStock is currently the preferred optional free source because its query returns amount and turnover and is less coupled to the Eastmoney endpoint in this environment. Use `--source baostock` explicitly for it.

AKShare `stock_zh_a_hist` commonly returns amount and turnover directly, but some AKShare upstream paths may still depend on Eastmoney availability. Use `--source akshare` explicitly when desired.

If Tencent fallback is used, historical `amount` is estimated from unadjusted typical price times volume, and `turnover` is estimated from latest float shares when available. This is usually more useful than missing values but should still be labelled as estimated.

If Yahoo fallback is used, `amount` and `turnover` may be blank. Lower confidence for amount/turnover-based conclusions and prefer web/vendor/exchange data when turnover or成交额 is essential.

Use `--secid` if automatic market inference is wrong:

- `1.600519` for Shanghai-style symbols;
- `0.000001` for Shenzhen-style symbols;
- some index or BSE symbols may require explicit `--secid`.

## 3. Web-Search-Managed Current Facts

| Category | Examples | Use |
|---|---|---|
| Announcements | exchange/CNINFO/company notices | risk veto: reduction, unlock, buyback, ST, suspension |
| Exchange rules | SSE/SZSE/BSE rule pages | current T+1, price limit, after-hours, disclosure rules |
| Dragon Tiger list | exchange/public abnormal trading pages | seat behavior and institution/hot-money clues |
| Margin financing | exchange margin pages | official balance/purchase fields and eligibility |
| Block trades | exchange block trade pages | large chip transfer and discount/premium |
| Stock Connect | SSE/SZSE/HKEX disclosures | northbound/holding proxy |
| Fund reports | official fund reports or exchange/CNINFO documents | lagged institutional participation |

## 4. Field Normalization

Normalize CSV fields before using scripts or analysis:

| Canonical field | Common aliases |
|---|---|
| date | 日期, trade_date, 时间 |
| open | 开盘, open_price |
| high | 最高, high_price |
| low | 最低, low_price |
| close | 收盘, close_price |
| volume | 成交量, vol |
| amount | 成交额, 成交金额, turnover_value |
| turnover | 换手率, turnover_rate |
| pct_change | 涨跌幅, change_pct |
| index_close | benchmark_close, 指数收盘 |
| sector_close | industry_close, 板块收盘 |

Prefer amount over volume when comparing across stocks because A-share share counts and prices differ.

## 5. Disclosure Lag and Interpretation

- Dragon Tiger list is post-trade and selective; use it to explain or confirm, not to predict alone.
- Fund holdings and shareholder counts are lagged; use them for medium-term chip context, not same-day timing.
- Northbound/Stock Connect intraday net-flow conventions have changed; avoid treating old real-time net-buying metrics as reliable current signals.
- Vendor "large order" and "main-force flow" formulas differ; if used, cite vendor and combine with price/amount/turnover.
- Local daily main-force proxy is not true 主力净流入; use `main-force-methods.md` and label conclusions as proxy evidence.
- Local chip distribution is a CYQ-style proxy, not a proprietary broker/vendor cost curve; use it for support/resistance and lifecycle evidence, not as fact.
- Block trades can be bearish, neutral, or structural; interpret discount, lockup, buyer type, subsequent price support, and volume absorption together.
- Margin financing is pro-cyclical; high-level financing growth is often a crowding risk.

## 6. Agent Data Pipeline Checklist

For an automated agent, collect data in this order:

1. Resolve stock code, exchange, board, and sector.
2. Use `fetch_eastmoney_kline.py` to pull at least 250 daily bars; prefer 500-1000 bars.
3. Run `score_ashare_timing.py` for a deterministic CSV technical snapshot.
4. Pull benchmark and sector bars if available; otherwise use web/vender data and state the source.
5. Use web search for announcements, Dragon Tiger list, margin details, block trades, and current event risks when they matter.
6. Compare all data dates; stale disclosure lowers confidence.
7. Emit data-quality score and missing-data list before final recommendation.
