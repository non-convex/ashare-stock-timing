# A-Share Timing Report Template

Use this template for final reports. Keep conclusions actionable and separate score from confidence.

## Executive Summary

- Rating: actionable / watch / avoid.
- Total score: `/100`.
- Confidence: high / medium / low, with reason.
- Primary setup: breakout / pullback / reversal / short-term momentum / no setup.
- Bias: bullish / neutral / bearish.
- Key invalidation: exact price/condition.

## Data Quality

| Data item | Status | Note |
|---|---|---|
| OHLCV | available/missing | dates, adjustment |
| Benchmark | available/missing | index used |
| Sector | available/missing | sector used |
| Margin financing | available/missing/not eligible | latest date |
| Dragon Tiger list | available/missing/not triggered | recent entries |
| Block trades | available/missing | recent entries |
| Shareholder/chips | available/missing | reporting date |
| Announcements | checked/not checked | reduction/unlock/ST/suspension |

## Scorecard

| Module | Score | Weight | Evidence |
|---|---:|---:|---|
| Market regime |  | 20 |  |
| Sector strength |  | 15 |  |
| Stock trend |  | 20 |  |
| Volume/fund behavior |  | 20 |  |
| Chip/control |  | 15 |  |
| Risk/execution |  | 10 |  |

## Market and Sector

- Market regime:
- Sector rank/relative strength:
- Money-making effect:
- Impact on position sizing:

## Individual Trend

- Phase:
- Moving averages:
- Support:
- Resistance:
- Volatility/ATR:
- Relative strength:
- Weekly/daily alignment:

## Volume, Funds, and Chips

- Volume-price chain:
- OBV/CMF/MFI/VWAP:
- Margin financing:
- Dragon Tiger list:
- Block trades:
- Shareholder/chip evidence:
- Main conclusion:

## Trading Plan

| Scenario | Trigger | Action | Stop/Invalidation | Position |
|---|---|---|---|---|
| Breakout buy |  |  |  |  |
| Pullback buy |  |  |  |  |
| No-trade |  |  |  |  |
| Add-on |  |  |  |  |
| Trim/exit |  |  |  |  |

## Risk Controls

- Maximum account risk per trade:
- Planned entry:
- Stop:
- Per-share risk:
- Suggested shares/position if account size is known:
- T+1/limit risk:
- Event risks:

## Missing Data That Could Change The View

- 

## Agent JSON Skeleton

```json
{
  "rating": "watch",
  "score": 0,
  "confidence": "low",
  "primary_setup": "none",
  "bias": "neutral",
  "key_levels": {
    "support": [],
    "resistance": [],
    "invalidation": null
  },
  "scorecard": {
    "market_regime": 0,
    "sector_strength": 0,
    "stock_trend": 0,
    "volume_funds": 0,
    "chips_control": 0,
    "risk_execution": 0
  },
  "buy_plan": [],
  "sell_plan": [],
  "risk_plan": {
    "max_account_risk_pct": null,
    "entry": null,
    "stop": null,
    "position_size": null
  },
  "missing_data": [],
  "warnings": []
}
```

