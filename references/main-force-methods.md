# Main-Force Information Methods

Use this reference when the user asks about 主力资金、主力净流入、大单、超大单、控盘、吸筹、派发, or when the agent needs a local main-force reference signal.

## 1. What "Main Force" Usually Means

"主力资金" is not an official exchange identity. Vendors usually estimate it from transaction/order data:

- classify trades/orders by amount or shares into small/mid/big/huge buckets;
- infer active buy/sell direction from trade side, bid/ask, or tick rule;
- aggregate large buckets as "main force";
- compute main-force net flow = large active buy amount - large active sell amount.

The exact thresholds and side-classification algorithms differ by vendor. Treat vendor values as estimates, not facts.

## 2. Common Vendor-Style Construction

Typical fixed amount buckets used by many Chinese data products and tutorials:

| Bucket | Typical amount threshold |
|---|---:|
| Small order | < 40,000 RMB |
| Mid order | 40,000-200,000 RMB |
| Big order | 200,000-1,000,000 RMB |
| Huge/super order | >= 1,000,000 RMB |

Then:

`main_force_net = big_buy + huge_buy - big_sell - huge_sell`

Some products use share-count thresholds, dynamic thresholds by liquidity/market cap, or Level-2 order reconstruction. Do not mix values from different vendors without noting口径差异.

## 3. Required Data Quality

| Data | Can compute true-ish main-force flow? | Note |
|---|---|---|
| Level-2 order/transaction data with side | Best | closest to vendor methods |
| Tick trades with bid/ask or side | Good | can classify active buy/sell |
| Tick trades with only price | Medium | tick-rule side inference is noisy |
| Daily OHLCV only | No | can only compute volume-price proxy |
| Vendor "主力净流入" field | Depends | cite vendor; formula may be opaque |

## 4. Local Script

Use:

```powershell
python C:/Users/Administrator/.codex/skills/ashare-stock-timing/scripts/estimate_main_force.py data.csv --mode auto --json
```

For daily OHLCV:

- computes a proxy, not true main-force flow;
- uses `proxy_net_amount = close_location_value * amount`;
- combines CMF-like ratio, amount expansion, OBV trend, and high-volume distribution flags;
- outputs `main_force_proxy.score_0_100` and `state`.

For tick data:

- classifies trades by amount thresholds;
- infers side using `side` column, bid/ask, or tick rule;
- outputs big+huge buy/sell/net and ratios;
- outputs local DDX/DDY/DDZ-style proxies when tick data is available.

Useful tick columns:

`date,time,price,volume,amount,side,bid1,ask1`

If tick volume is in hands, pass `--volume-multiplier 100`.

## 5. How To Use The Script Output

### Daily Proxy Interpretation

| State | Meaning |
|---|---|
| `proxy_accumulation` | positive CMF-like flow while price has not overextended; possible accumulation proxy |
| `proxy_inflow_support` | volume-price structure supports trend continuation |
| `neutral_or_mixed` | no clear fund-flow edge |
| `proxy_outflow_pressure` | daily proxy suggests selling pressure |
| `proxy_distribution_or_outflow` | high risk of distribution/outflow proxy |

### Tick Mode Interpretation

| Signal | Interpretation |
|---|---|
| main net / total amount > 8% and active net ratio > 15% | meaningful large-order net inflow |
| main net / total amount < -8% and active net ratio < -15% | meaningful large-order net outflow |
| high neutral/unclassified ratio | side inference weak; lower confidence |
| huge buy but price fails | possible absorption or distribution; confirm with price |
| huge sell but price holds | possible strong承接; confirm with support and sector |

### Local DDX/DDY/DDZ Proxies

| Output | Meaning |
|---|---|
| `ddx_amount_proxy` | big+huge active net amount / total amount |
| `ddx_volume_proxy` | big+huge active net volume / total volume when volume is available |
| `ddy_absorption_proxy` | count-concentration proxy; positive supports concentrated absorption, while negative means absorption is not confirmed and must be judged with net flow and price |
| `ddz_attack_proxy` | large-buy attack strength; higher when big+huge buy amount dominates and active net ratio is positive |

These are local approximations, not vendor DDX/DDY/DDZ. Use them only as reference evidence.

## 6. Never Use Alone

Do not buy/sell only because a local main-force score is high/low. Confirm with:

- market regime;
- sector strength;
- trend phase;
- support/resistance;
- breakout/pullback volume;
- margin financing;
- Dragon Tiger list;
- announcements and event risks.

If the conclusion mainly depends on main-force net inflow without price/volume confirmation, downgrade or reject the setup.
