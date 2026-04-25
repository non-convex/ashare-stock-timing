# A-Share Stock Timing Methodology

[中文](./README.zh-CN.md)

`ashare-stock-timing` is an agent-ready methodology package for AI agents that analyze Chinese A-share individual-stock technical timing: trend, buy points, sell points, fund-flow proxies, chip/cost distribution, and risk plans.

It is strictly focused on **technical timing**. It does not perform fundamental analysis, financial-statement analysis, valuation, DCF, target-price modeling, or long-term business-quality research.

## When To Use

Use this skill when the user asks about:

- Technical trend and swing structure of an A-share stock.
- Buy points, sell points, stop-loss, take-profit, add-on, and trim logic.
- Volume-price behavior, breakouts, pullbacks, boxes, markup phases, and distribution risk.
- Main-force funds, Dragon Tiger list, margin financing, block trades, northbound flows, and chip/cost distribution.
- Technical entry/exit timing after a separate fundamental view already exists.

Do not use this skill for:

- Business fundamentals.
- Financial statements, earnings forecasts, industry TAM, business model, or moat.
- PE/PB/PEG, DCF, target price, or intrinsic value.
- Long-term investment merit unless the user explicitly asks for technical timing on top of an existing thesis.

## Methodology

The skill uses a layered evidence chain rather than any single indicator:

```text
market/sector filter
  -> chip lifecycle
  -> stock trend trigger
  -> volume/main-force confirmation
  -> risk and position plan
```

Main modules:

| Module | Purpose |
|---|---|
| Market regime | Decide whether the broad market allows long exposure |
| Sector strength | Decide whether money is moving into the stock's direction |
| Stock trend | Identify phase, moving-average structure, highs, and breakdowns |
| Volume/funds | Confirm breakouts, pullbacks, distribution, and turnover |
| Main-force proxy | Estimate fund behavior from tick large orders or daily proxies |
| Chip distribution | Estimate cost peaks, support/resistance, lock-up, and distribution risk |
| Risk execution | Handle T+1, price limits, liquidity, announcements, and stop distance |

## Data And Scripts

All scripts use only the Python standard library.

### 1. Fetch Daily K-Line Data

```powershell
python scripts/fetch_eastmoney_kline.py 000001 --start 20240101 --end 20260425 --adjust qfq --source auto --output 000001_daily.csv
```

Notes:

- `--source auto` tries Eastmoney first and falls back to Yahoo Chart.
- Eastmoney data usually includes amount and turnover.
- Yahoo fallback may leave `amount` and `turnover` blank; lower confidence for amount/turnover-based conclusions in that case.

### 2. Technical Score Snapshot

```powershell
python scripts/score_ashare_timing.py 000001_daily.csv --entry 10.50 --stop 9.85 --json
```

Outputs include:

- MA5/10/20/60/120/250
- ATR, RSI, CMF, OBV, MACD histogram
- 20-day and 55-day high/low levels
- amount expansion ratio
- trend phase
- CSV-only technical score

### 3. Main-Force Reference

Daily proxy:

```powershell
python scripts/estimate_main_force.py 000001_daily.csv --mode daily --json
```

Tick mode:

```powershell
python scripts/estimate_main_force.py ticks.csv --mode ticks --json
```

Useful tick columns:

```text
date,time,price,volume,amount,side,bid1,ask1
```

Outputs include:

- big/huge active buy, sell, and net amount;
- `ddx_amount_proxy`;
- `ddx_volume_proxy`;
- `ddy_absorption_proxy`;
- `ddz_attack_proxy`.

Daily mode is only a main-force behavior proxy. It cannot identify true account-level main-force net flow.

### 4. Chip / CYQ-Style Cost Distribution Proxy

```powershell
python scripts/estimate_chip_distribution.py 000001_daily.csv --lookback 250 --json
```

Outputs include:

- cost quantiles: `q05/q15/q50/q85/q95`;
- cost peaks: `peaks`;
- support peaks: `support_peaks_below_close`;
- resistance peaks: `resistance_peaks_above_close`;
- profit ratio: `profit_ratio`;
- overhead ratio: `overhead_ratio`;
- concentration state;
- lifecycle state.

This is a local CYQ-style proxy, not a proprietary broker/vendor chip distribution.

## Install / Use With AI Agents

Clone the repository wherever your AI agent can read local tools, references, and scripts:

```bash
git clone https://github.com/non-convex/ashare-stock-timing.git
```

If your agent supports skill-style local folders, clone it into that agent's skill directory. For example:

```bash
git clone https://github.com/non-convex/ashare-stock-timing.git <agent-skills-dir>/ashare-stock-timing
```

On Windows:

```powershell
git clone https://github.com/non-convex/ashare-stock-timing.git C:/path/to/agent-skills/ashare-stock-timing
```

Agents can then load `SKILL.md`, call the scripts in `scripts/`, and selectively read the methodology files in `references/` when users ask about A-share technical trends or buy/sell timing.

## Example Agent Flow

User:

> Analyze the technical trend and buy point for 000001.

Recommended agent commands:

```powershell
python scripts/fetch_eastmoney_kline.py 000001 --start 20240101 --end 20260425 --adjust qfq --source auto --output 000001_daily.csv
python scripts/score_ashare_timing.py 000001_daily.csv --json
python scripts/estimate_main_force.py 000001_daily.csv --mode daily --json
python scripts/estimate_chip_distribution.py 000001_daily.csv --lookback 250 --json
```

Then combine the script output with:

- market and sector regime;
- latest announcements, reduction plans, unlocks, suspension, or ST risk;
- Dragon Tiger list, margin financing, block trades, and stock-connect data;
- T+1, price limits, liquidity, and stop execution risk.

Final output should include:

- actionable / watch / avoid rating;
- buy trigger;
- add-on trigger;
- stop and invalidation;
- trim and exit rules;
- risk notes and missing data.

## Repository Layout

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── chip-distribution-methods.md
│   ├── data-sources.md
│   ├── main-force-methods.md
│   ├── methodology.md
│   └── report-template.md
└── scripts/
    ├── estimate_chip_distribution.py
    ├── estimate_main_force.py
    ├── fetch_eastmoney_kline.py
    └── score_ashare_timing.py
```

## Limitations

- This project is not investment advice and does not guarantee returns.
- It does not perform fundamental or valuation analysis.
- Main-force flow, main-force net inflow, and chip distribution are model-based proxies, not direct exchange-disclosed account data.
- Script outputs must be combined with price structure, sector context, disclosures, liquidity, and real execution constraints.
- A-shares have T+1, price limits, suspensions, announcement gaps, and liquidity-break risks.

## License

MIT License. See [LICENSE](./LICENSE).
