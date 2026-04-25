---
name: ashare-stock-timing
description: Technical and trend timing methodology for A-share individual stocks. Use only when the user asks about A股/沪深/创业板/科创板/北交所个股的技术面、趋势、买点、卖点、波段、量价、资金动向、龙虎榜、两融、筹码、主力控盘、突破、回踩、止损、止盈 or AI-agent timing analysis. Do not trigger for fundamental analysis, financial statements, valuation, DCF, target price, intrinsic value, moat, earnings forecasts, or business-quality research unless the user explicitly asks to combine an existing fundamental view with technical timing.
---

# A-Share Stock Timing

Use this skill to produce decision-grade, non-fundamental A-share individual-stock timing analysis for an AI agent. Keep the skill focused on methodology, execution rules, and risk controls. Use scripts for structured price/indicator data. Use web search for current official disclosures or facts that are better obtained from live sources.

## Core Rules

- Treat price, volume, turnover, liquidity, and disclosed exchange data as primary evidence.
- Do not present "主力意图" as fact. Translate it into observable proxies: volume-price behavior, turnover, OBV/CMF, financing balance, Dragon Tiger list, block trades, shareholder count, and disclosed holders.
- Do not rely on vendor "主力净流入" alone; label it as an algorithmic estimate if used.
- Always account for A-share mechanics: T+1, price limits, board-specific volatility, disclosure lag, suspension risk, limit-up/limit-down execution risk, and announcement gaps.
- If the task is fundamental or valuation-only, do not use this skill; switch to a fundamental/valuation workflow instead.
- If the user asks for current/live analysis, verify latest trading rules, announcements, and data before concluding.
- Do not give personalized financial advice or guarantees. Provide scenarios, invalidation levels, and position-risk math.

## Trigger Boundary

Use this skill for:

- “某股票技术面怎么样 / 趋势如何 / 买点卖点在哪里 / 能不能突破 / 回踩怎么看”
- “用资金动向、筹码、龙虎榜、两融、量价判断 A 股个股”
- “设计 A 股个股技术分析 AI agent / 买卖点分析框架 / 波段交易计划”
- “已有基本面结论，只需要判断技术入场、加仓、减仓、退出”

Do not use this skill for:

- “这家公司基本面怎么样 / 财报如何 / 估值贵不贵 / 目标价多少”
- “DCF、PE/PB/PEG、盈利预测、行业空间、竞争壁垒、商业模式”
- “是否值得长期投资” unless the user explicitly requests technical timing after a separate long-term thesis.

## Workflow

1. **Clarify scope**: identify stock code/name, board, horizon (intraday/short swing/medium swing), available data, and whether the task is methodology design, live analysis, or backtest rule design.
2. **Acquire structured data**: use bundled scripts for daily OHLCV and CSV-based indicator scoring when available. Use web search instead of scripts for current announcements, exchange rules, Dragon Tiger list details, disclosure changes, event risks, or source-specific facts that need authoritative/live verification.
3. **Classify market regime**: trend, range, or downtrend using broad index structure, turnover, breadth, and money-making effect.
4. **Rank sector strength**: compare sector relative strength, sector turnover expansion, leader performance, and theme breadth before judging the individual stock.
5. **Analyze individual trend**: classify phase, moving-average stack, new-high/new-low structure, ATR volatility, relative strength, support/resistance, and weekly/daily alignment.
6. **Read volume and funds**: combine breakout volume, pullback volume, turnover, amount, OBV/CMF/MFI/VWAP, margin financing, Dragon Tiger list, northbound/ETF disclosures, and block trades.
7. **Evaluate chips/control**: infer chip concentration and control only from evidence such as range turnover, volatility contraction, support tests, shareholder count, disclosed holders, and concentration changes.
8. **Score and decide**: apply the 100-point model from `references/methodology.md`; reject trades with one-vote veto risks.
9. **Build the plan**: provide candidate buy zones, add-on triggers, hard stops, trend stops, profit-taking logic, position sizing, and scenario table.
10. **State gaps**: list missing data that could change the conclusion.

## Methodology References

- Load `references/methodology.md` for the full framework, scoring rubric, buy/sell patterns, and risk rules.
- Load `references/data-sources.md` when deciding whether to use a script or web search for a specific data need.
- Load `references/main-force-methods.md` when analyzing 主力资金、主力净流入、大单、超大单、控盘、吸筹、派发, or when using local main-force proxy output.
- Load `references/chip-distribution-methods.md` when analyzing 筹码分布、CYQ、成本峰、套牢盘、获利盘、主力锁仓、筹码集中 or 筹码发散.
- Load `references/report-template.md` when producing a standardized final report or JSON-like agent output.

## Data Scripts

Fetch daily K-line data:

```powershell
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/fetch_eastmoney_kline.py 000001 --start 20240101 --end 20260425 --adjust qfq --output 000001_daily.csv
```

For fuller historical fields, optionally install BaoStock/AKShare in the agent environment and use `--source baostock`, `--source akshare`, or the default `--source auto`:

```powershell
pip install -r C:/Users/Administrator/.codex/skills/ashare-stock-timing/requirements-optional.txt
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/fetch_eastmoney_kline.py 000001 --start 20240101 --end 20260425 --adjust qfq --source baostock --output 000001_daily.csv
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/fetch_eastmoney_kline.py 000001 --start 20240101 --end 20260425 --adjust qfq --source akshare --output 000001_daily.csv
```

Score a CSV of daily OHLCV data:

```powershell
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/score_ashare_timing.py path/to/daily.csv --entry 10.50 --stop 9.85
```

Estimate a local main-force reference from daily OHLCV or tick CSV:

```powershell
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/estimate_main_force.py path/to/data.csv --mode auto --json
```

Estimate a local chip/CYQ-style cost distribution proxy:

```powershell
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/estimate_chip_distribution.py path/to/daily.csv --lookback 250 --json
```

Scripts compute structured price/indicator context only. They do not replace market/sector judgment, current disclosure checks, or the full methodology.

## Minimum Output

Every analysis should include:

- Overall rating: actionable / watch / avoid, with score and confidence.
- Market and sector context.
- Individual trend phase and key levels.
- Volume-fund-chip evidence chain.
- Buy point candidates, invalidation conditions, and stop-loss levels.
- Sell/trim rules and trailing-stop logic.
- Position size based on maximum account risk, if account size and stop distance are known.
- Missing data and warnings.
