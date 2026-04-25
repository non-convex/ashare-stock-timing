# Chip Distribution / CYQ Proxy Methods

Use this reference when the user asks about 筹码分布、CYQ、成本峰、套牢盘、获利盘、主力锁仓、筹码集中、筹码发散, or when the agent needs chip lifecycle evidence.

## 1. Why Add This Layer

The external methodology correctly emphasizes a major gap in a pure MA/volume framework: price trend tells what happened, but cost distribution helps estimate where supply, trapped holders, and profit-taking pressure may concentrate.

Adopt this layer as evidence, not dogma. Vendor CYQ is model-based and proprietary; local scripts can only approximate it from daily OHLCV.

## 2. Local Script

Use:

```powershell
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/estimate_chip_distribution.py daily.csv --lookback 250 --json
```

The script:

- builds price bins across the lookback range;
- allocates each day's volume/amount across the day's high-low range with close-price bias;
- if turnover is available, models daily float replacement;
- otherwise uses rolling volume/amount-at-price;
- outputs cost quantiles, concentration width, profit/overhead ratio, support/resistance peaks, and lifecycle state.

## 3. Key Outputs

| Output | Meaning |
|---|---|
| `lifecycle` | base/markup/distribution/transition proxy |
| `concentration.state` | single peak, moderate concentration, dispersed multi-peak, or balanced |
| `cost_quantiles.q15/q50/q85` | approximate lower/mid/upper cost area |
| `profit_overhang.profit_ratio` | estimated chips below latest close |
| `profit_overhang.overhead_ratio` | estimated chips above latest close |
| `peaks` | major cost peaks that can act as support/resistance |
| `support_peaks_below_close` | nearby lower cost support zones |
| `resistance_peaks_above_close` | nearby overhead supply zones |

## 4. High-Value Patterns

### Low-Cost Concentration Base

Useful watch condition:

- concentrated low/mid cost peak after long decline or long base;
- overhead ratio falls as trapped chips are digested;
- price stops making lower lows;
- volume contracts on pullbacks;
- main-force proxy or tick large-order signal improves.

Not enough by itself. Buy only after right-side breakout above the cost peak/range with volume and sector confirmation.

### Breakout and Second Entry

First buy candidate:

- price closes above the upper edge of the major cost peak or base range;
- amount expands versus the prior window;
- close is near the day's high;
- main-force proxy/tick signal confirms, or at least does not diverge.

Second buy candidate:

- price pulls back to the broken peak/range upper area;
- volume/amount contracts;
- support holds and price reclaims VWAP/MA5/MA10/MA20 depending on horizon.

### Lock-Up / Hold Evidence

During markup, trend holding is stronger when:

- an old low-cost peak remains visible while price advances;
- pullbacks do not destroy the major support peak;
- new intermediate peaks form above the old cost area without heavy distribution signals;
- volume-fund signals do not show persistent outflow.

Because local scripts only show one current snapshot, compare multiple dates or rerun on historical cutoffs when lock-up evidence is important.

### Distribution Risk

High-risk condition:

- high profit ratio after a large advance;
- bottom/low-cost peak weakens or disappears over time;
- high-level concentration appears;
- price stops rising despite high amount/turnover;
- main-force proxy/tick DDY-like concentration signal diverges downward.

When this appears, tighten stops, trim, or exit rather than treating high-level single peak as support.

## 5. Integration Rule

Use chip distribution as the structural layer:

`market/sector filter -> chip lifecycle -> trend trigger -> volume/main-force confirmation -> risk plan`

Do not replace trend confirmation with chip distribution. A low concentrated peak can remain dormant for months.

## 6. Limitations

- Daily OHLCV cannot reveal real account ownership.
- Turnover-based replacement assumes traded float changes hands, which is only an approximation.
- Vendor CYQ, broker cost curves, and this local proxy can differ materially.
- Always label local output as "chip distribution proxy".

