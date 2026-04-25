#!/usr/bin/env python3
"""
Estimate A-share "main-force" money behavior for AI-agent reference.

Two modes are supported:

1. ticks: classify tick/transaction rows into small/mid/big/huge trades and
   compute big+huge active net flow. This is closest to vendor "main-force"
   methods when tick side or bid/ask data is available.
2. daily: compute a DAILY PROXY from OHLCV only using close-location value,
   amount expansion, OBV trend, and distribution/accumulation flags. This is
   not real main-force flow and must be labelled as a proxy.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ALIASES = {
    "date": ["date", "日期", "trade_date", "交易日期"],
    "time": ["time", "时间", "trade_time", "成交时间"],
    "open": ["open", "开盘", "open_price"],
    "high": ["high", "最高", "high_price"],
    "low": ["low", "最低", "low_price"],
    "close": ["close", "收盘", "close_price"],
    "price": ["price", "成交价", "现价", "trade_price"],
    "volume": ["volume", "成交量", "vol", "成交量(股)", "成交量(手)"],
    "amount": ["amount", "成交额", "成交金额", "turnover_value"],
    "turnover": ["turnover", "换手率", "turnover_rate"],
    "side": ["side", "方向", "买卖方向", "bs", "trade_side"],
    "bid1": ["bid1", "买一价", "买一", "bid_price1"],
    "ask1": ["ask1", "卖一价", "卖一", "ask_price1"],
}

BUY_VALUES = {"b", "buy", "bid", "主动买入", "买入", "买", "外盘", "1", "+"}
SELL_VALUES = {"s", "sell", "ask", "主动卖出", "卖出", "卖", "内盘", "-1", "-"}


@dataclass
class DailyBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    amount: float | None
    turnover: float | None


@dataclass
class TickTrade:
    date: str
    time: str
    price: float
    volume: float | None
    amount: float
    side: str


def normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "").replace("_", "")


def find_column(headers: list[str], canonical: str) -> str | None:
    normalized = {normalize_header(header): header for header in headers}
    for alias in ALIASES[canonical]:
        key = normalize_header(alias)
        if key in normalized:
            return normalized[key]
    return None


def to_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "-", "None", "none", "nan", "NaN", "--"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def stdev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    average = mean(values)
    if average is None:
        return None
    variance = sum((value - average) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def detect_mode(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
    has_ohlc = all(find_column(headers, key) for key in ["open", "high", "low", "close"])
    has_price = bool(find_column(headers, "price"))
    if has_price and not has_ohlc:
        return "ticks"
    if has_ohlc:
        return "daily"
    raise SystemExit("Cannot detect mode. Use --mode daily or --mode ticks and provide required columns.")


def read_daily(path: Path) -> list[DailyBar]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        columns = {key: find_column(headers, key) for key in ALIASES}
        missing = [key for key in ["date", "open", "high", "low", "close"] if not columns[key]]
        if missing:
            raise SystemExit(f"Missing daily columns: {', '.join(missing)}")

        bars: list[DailyBar] = []
        for row in reader:
            open_ = to_float(row.get(columns["open"]))
            high = to_float(row.get(columns["high"]))
            low = to_float(row.get(columns["low"]))
            close = to_float(row.get(columns["close"]))
            if open_ is None or high is None or low is None or close is None:
                continue
            bars.append(
                DailyBar(
                    date=str(row.get(columns["date"], "")).strip(),
                    open=open_,
                    high=high,
                    low=low,
                    close=close,
                    volume=to_float(row.get(columns["volume"])) if columns["volume"] else None,
                    amount=to_float(row.get(columns["amount"])) if columns["amount"] else None,
                    turnover=to_float(row.get(columns["turnover"])) if columns["turnover"] else None,
                )
            )
    bars.sort(key=lambda bar: bar.date)
    if len(bars) < 20:
        raise SystemExit("Need at least 20 daily bars for a main-force proxy.")
    return bars


def classify_side(raw_side: object, price: float, bid1: float | None, ask1: float | None, previous_price: float | None, previous_side: str) -> str:
    if raw_side is not None:
        text = str(raw_side).strip().lower()
        if text in BUY_VALUES:
            return "buy"
        if text in SELL_VALUES:
            return "sell"

    if bid1 is not None and ask1 is not None:
        if price >= ask1:
            return "buy"
        if price <= bid1:
            return "sell"

    if previous_price is not None:
        if price > previous_price:
            return "buy"
        if price < previous_price:
            return "sell"

    return previous_side if previous_side in {"buy", "sell"} else "neutral"


def read_ticks(path: Path, volume_multiplier: float) -> list[TickTrade]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        columns = {key: find_column(headers, key) for key in ALIASES}
        if not columns["price"]:
            raise SystemExit("Missing tick column: price/成交价")
        if not columns["amount"] and not columns["volume"]:
            raise SystemExit("Ticks need amount/成交额 or volume/成交量.")

        trades: list[TickTrade] = []
        previous_price: float | None = None
        previous_side = "neutral"
        for row in reader:
            price = to_float(row.get(columns["price"]))
            if price is None:
                continue
            volume = to_float(row.get(columns["volume"])) if columns["volume"] else None
            amount = to_float(row.get(columns["amount"])) if columns["amount"] else None
            if amount is None and volume is not None:
                amount = price * volume * volume_multiplier
            if amount is None:
                continue
            bid1 = to_float(row.get(columns["bid1"])) if columns["bid1"] else None
            ask1 = to_float(row.get(columns["ask1"])) if columns["ask1"] else None
            side = classify_side(
                row.get(columns["side"]) if columns["side"] else None,
                price,
                bid1,
                ask1,
                previous_price,
                previous_side,
            )
            trades.append(
                TickTrade(
                    date=str(row.get(columns["date"], "")).strip() if columns["date"] else "",
                    time=str(row.get(columns["time"], "")).strip() if columns["time"] else "",
                    price=price,
                    volume=volume,
                    amount=amount,
                    side=side,
                )
            )
            previous_price = price
            previous_side = side
    if not trades:
        raise SystemExit("No valid tick trades parsed.")
    return trades


def trade_bucket(amount: float, mid_threshold: float, big_threshold: float, huge_threshold: float) -> str:
    if amount >= huge_threshold:
        return "huge"
    if amount >= big_threshold:
        return "big"
    if amount >= mid_threshold:
        return "mid"
    return "small"


def summarize_ticks(trades: list[TickTrade], mid_threshold: float, big_threshold: float, huge_threshold: float) -> dict:
    buckets = {
        name: {"buy": 0.0, "sell": 0.0, "neutral": 0.0, "count": 0}
        for name in ["small", "mid", "big", "huge"]
    }
    total_amount = 0.0
    classified_amount = 0.0
    total_volume = 0.0
    big_huge_net_volume = 0.0
    side_counts = {"buy": 0, "sell": 0, "neutral": 0}
    side_amounts = {"buy": 0.0, "sell": 0.0, "neutral": 0.0}
    for trade in trades:
        bucket = trade_bucket(trade.amount, mid_threshold, big_threshold, huge_threshold)
        side = trade.side if trade.side in {"buy", "sell"} else "neutral"
        buckets[bucket][side] += trade.amount
        buckets[bucket]["count"] += 1
        side_counts[side] += 1
        side_amounts[side] += trade.amount
        total_amount += trade.amount
        if trade.volume is not None:
            total_volume += trade.volume
            if bucket in {"big", "huge"} and side == "buy":
                big_huge_net_volume += trade.volume
            elif bucket in {"big", "huge"} and side == "sell":
                big_huge_net_volume -= trade.volume
        if side != "neutral":
            classified_amount += trade.amount

    for values in buckets.values():
        values["net"] = values["buy"] - values["sell"]
        values["net_ratio"] = values["net"] / total_amount if total_amount else 0.0

    main_buy = buckets["big"]["buy"] + buckets["huge"]["buy"]
    main_sell = buckets["big"]["sell"] + buckets["huge"]["sell"]
    main_net = main_buy - main_sell
    main_gross = main_buy + main_sell
    main_net_ratio = main_net / total_amount if total_amount else 0.0
    main_active_ratio = main_net / main_gross if main_gross else 0.0
    classified_count = side_counts["buy"] + side_counts["sell"]
    count_imbalance = (side_counts["sell"] - side_counts["buy"]) / classified_count if classified_count else 0.0
    average_buy_amount = side_amounts["buy"] / side_counts["buy"] if side_counts["buy"] else None
    average_sell_amount = side_amounts["sell"] / side_counts["sell"] if side_counts["sell"] else None
    average_size_ratio = (
        average_buy_amount / average_sell_amount
        if average_buy_amount is not None and average_sell_amount not in (None, 0)
        else None
    )
    direction_sign = 1 if main_net >= 0 else -1
    ddy_absorption_proxy = count_imbalance * direction_sign * abs(main_active_ratio)
    ddz_attack_proxy = (main_buy / total_amount if total_amount else 0.0) * max(main_active_ratio, 0.0)

    state = "neutral"
    if main_net_ratio >= 0.08 and main_active_ratio >= 0.15:
        state = "main_force_net_inflow"
    elif main_net_ratio <= -0.08 and main_active_ratio <= -0.15:
        state = "main_force_net_outflow"

    warnings = []
    if classified_amount / total_amount < 0.7 if total_amount else True:
        warnings.append("Large neutral/unclassified tick amount; side classification may be weak.")

    return {
        "mode": "ticks",
        "method": "large_order_active_net_flow",
        "definition": "main_force = big + huge trades by amount threshold; net = active_buy - active_sell",
        "thresholds": {
            "mid_min_amount": mid_threshold,
            "big_min_amount": big_threshold,
            "huge_min_amount": huge_threshold,
        },
        "total_amount": total_amount,
        "classified_amount_ratio": classified_amount / total_amount if total_amount else 0.0,
        "buckets": buckets,
        "main_force": {
            "buy": main_buy,
            "sell": main_sell,
            "net": main_net,
            "net_ratio_to_total_amount": main_net_ratio,
            "active_net_ratio_big_huge": main_active_ratio,
            "state": state,
        },
        "level2_proxies": {
            "ddx_amount_proxy": main_net_ratio,
            "ddx_volume_proxy": big_huge_net_volume / total_volume if total_volume else None,
            "ddy_absorption_proxy": ddy_absorption_proxy,
            "ddy_count_imbalance_sell_minus_buy": count_imbalance,
            "buy_count": side_counts["buy"],
            "sell_count": side_counts["sell"],
            "neutral_count": side_counts["neutral"],
            "average_buy_amount": average_buy_amount,
            "average_sell_amount": average_sell_amount,
            "average_buy_sell_size_ratio": average_size_ratio,
            "ddz_attack_proxy": ddz_attack_proxy,
        },
        "warnings": warnings,
        "limitations": [
            "Closest to vendor-style main-force flow only when tick side or bid/ask data is reliable.",
            "Thresholds are configurable and vendor definitions differ.",
            "If the feed aggregates trades, results can differ from Level-2 order-based statistics.",
        ],
    }


def amount_for_bar(bar: DailyBar) -> float | None:
    if bar.amount is not None:
        return bar.amount
    if bar.volume is not None:
        return bar.volume * bar.close
    return None


def close_location_value(bar: DailyBar, previous_close: float | None) -> float:
    high_low = bar.high - bar.low
    if high_low > 0:
        return clamp(((bar.close - bar.low) - (bar.high - bar.close)) / high_low, -1.0, 1.0)
    if previous_close is None:
        return 0.0
    if bar.close > previous_close:
        return 1.0
    if bar.close < previous_close:
        return -1.0
    return 0.0


def obv_series(bars: list[DailyBar]) -> list[float]:
    values = [0.0]
    for index in range(1, len(bars)):
        volume = bars[index].volume or 0.0
        if bars[index].close > bars[index - 1].close:
            values.append(values[-1] + volume)
        elif bars[index].close < bars[index - 1].close:
            values.append(values[-1] - volume)
        else:
            values.append(values[-1])
    return values


def slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values))
    denominator = sum((index - x_mean) ** 2 for index in range(n))
    return numerator / denominator if denominator else 0.0


def summarize_daily_proxy(bars: list[DailyBar], window: int) -> dict:
    rows = []
    missing_amount = False
    for index, bar in enumerate(bars):
        previous_close = bars[index - 1].close if index else None
        amount = amount_for_bar(bar)
        if bar.amount is None:
            missing_amount = True
        if amount is None:
            amount = 0.0
        clv = close_location_value(bar, previous_close)
        proxy_net = clv * amount
        pct_change = ((bar.close / previous_close - 1) * 100) if previous_close else 0.0
        rows.append(
            {
                "date": bar.date,
                "close": bar.close,
                "amount": amount,
                "clv": clv,
                "proxy_net_amount": proxy_net,
                "proxy_net_ratio": proxy_net / amount if amount else 0.0,
                "pct_change": pct_change,
                "turnover": bar.turnover,
            }
        )

    window = min(window, len(rows))
    recent = rows[-window:]
    amount_sum = sum(row["amount"] for row in recent)
    proxy_sum = sum(row["proxy_net_amount"] for row in recent)
    cmf = proxy_sum / amount_sum if amount_sum else 0.0
    amount_values = [row["amount"] for row in rows if row["amount"] > 0]
    recent_amount_average = mean([row["amount"] for row in recent if row["amount"] > 0])
    prior_amount_average = mean(amount_values[-(window * 2) : -window]) if len(amount_values) >= window * 2 else mean(amount_values[:-window])
    latest = rows[-1]
    amount_ratio = latest["amount"] / prior_amount_average if prior_amount_average and latest["amount"] else None

    closes = [bar.close for bar in bars]
    price_change_window = (closes[-1] / closes[-window] - 1) * 100 if window > 1 and closes[-window] else 0.0
    obv_values = obv_series(bars)
    obv_recent_slope = slope(obv_values[-window:])
    obv_scale = stdev(obv_values[-window:]) or abs(mean(obv_values[-window:]) or 1.0) or 1.0
    obv_trend = clamp(obv_recent_slope / obv_scale * window, -1.0, 1.0)

    high_volume_close_weak = (
        amount_ratio is not None
        and amount_ratio >= 2.0
        and latest["clv"] <= -0.35
    )
    high_volume_close_strong = (
        amount_ratio is not None
        and amount_ratio >= 1.5
        and latest["clv"] >= 0.35
    )
    accumulation_like = cmf >= 0.08 and price_change_window <= 5.0 and obv_trend > 0
    distribution_like = cmf <= -0.08 or high_volume_close_weak

    score = 50.0
    score += clamp(cmf, -0.35, 0.35) * 70
    score += obv_trend * 10
    if high_volume_close_strong:
        score += 8
    if high_volume_close_weak:
        score -= 12
    if accumulation_like:
        score += 7
    if distribution_like:
        score -= 7
    score = round(clamp(score, 0, 100), 2)

    if distribution_like and score < 45:
        state = "proxy_distribution_or_outflow"
    elif accumulation_like and score >= 60:
        state = "proxy_accumulation"
    elif score >= 65:
        state = "proxy_inflow_support"
    elif score <= 35:
        state = "proxy_outflow_pressure"
    else:
        state = "neutral_or_mixed"

    warnings = [
        "Daily OHLCV cannot identify real main-force accounts or large-order flow; this is a proxy only.",
        "Use tick/Level-2 data for vendor-style main-force net inflow.",
    ]
    if missing_amount:
        warnings.append("Amount/成交额 missing for some/all rows; amount was approximated by close*volume where possible.")
    if amount_ratio is None:
        warnings.append("Latest amount ratio unavailable; volume-expansion evidence is incomplete.")

    return {
        "mode": "daily",
        "method": "daily_ohlcv_main_force_proxy",
        "definition": "proxy_net_amount = close_location_value * amount; score combines CMF-like flow, amount expansion, OBV trend, and distribution flags",
        "window": window,
        "latest": {
            "date": latest["date"],
            "close": latest["close"],
            "proxy_net_amount": latest["proxy_net_amount"],
            "proxy_net_ratio": latest["proxy_net_ratio"],
            "clv": latest["clv"],
            "amount": latest["amount"],
            "amount_ratio_vs_prior_window": amount_ratio,
        },
        "window_summary": {
            "proxy_net_amount_sum": proxy_sum,
            "cmf_like_ratio": cmf,
            "price_change_pct": price_change_window,
            "recent_amount_average": recent_amount_average,
            "prior_amount_average": prior_amount_average,
            "obv_trend": obv_trend,
        },
        "main_force_proxy": {
            "score_0_100": score,
            "state": state,
            "accumulation_like": accumulation_like,
            "distribution_like": distribution_like,
            "high_volume_close_strong": high_volume_close_strong,
            "high_volume_close_weak": high_volume_close_weak,
        },
        "recent_rows": recent[-5:],
        "warnings": warnings,
        "limitations": [
            "Does not use account identity, order size, or true active buy/sell direction.",
            "Good for AI reference as a volume-price fund proxy, not as factual 主力净流入.",
            "Confirm with price structure, sector context, margin data, Dragon Tiger list, and announcements.",
        ],
    }


def print_markdown(result: dict) -> None:
    print("# A-Share Main-Force Reference")
    print()
    print(f"- Mode: {result['mode']}")
    print(f"- Method: {result['method']}")
    print(f"- Definition: {result['definition']}")
    print()
    if result["mode"] == "ticks":
        main = result["main_force"]
        print("## Main Force")
        print(f"- State: {main['state']}")
        print(f"- Buy: {main['buy']:.2f}")
        print(f"- Sell: {main['sell']:.2f}")
        print(f"- Net: {main['net']:.2f}")
        print(f"- Net / total amount: {main['net_ratio_to_total_amount']:.4f}")
        print(f"- Active net ratio in big+huge: {main['active_net_ratio_big_huge']:.4f}")
        proxies = result.get("level2_proxies", {})
        print(f"- DDX amount proxy: {proxies.get('ddx_amount_proxy', 0):.4f}")
        ddy = proxies.get("ddy_absorption_proxy")
        ddz = proxies.get("ddz_attack_proxy")
        print(f"- DDY absorption proxy: {'n/a' if ddy is None else f'{ddy:.4f}'}")
        print(f"- DDZ attack proxy: {'n/a' if ddz is None else f'{ddz:.4f}'}")
        print()
        print("## Buckets")
        for name, values in result["buckets"].items():
            print(
                f"- {name}: buy={values['buy']:.2f}, sell={values['sell']:.2f}, "
                f"net={values['net']:.2f}, count={values['count']}"
            )
    else:
        proxy = result["main_force_proxy"]
        latest = result["latest"]
        summary = result["window_summary"]
        print("## Main-Force Proxy")
        print(f"- State: {proxy['state']}")
        print(f"- Score: {proxy['score_0_100']}/100")
        print(f"- Latest proxy net amount: {latest['proxy_net_amount']:.2f}")
        print(f"- Latest proxy net ratio: {latest['proxy_net_ratio']:.4f}")
        ratio = latest["amount_ratio_vs_prior_window"]
        print(f"- Latest amount ratio: {'n/a' if ratio is None else f'{ratio:.2f}x'}")
        print(f"- Window CMF-like ratio: {summary['cmf_like_ratio']:.4f}")
        print(f"- Window price change: {summary['price_change_pct']:.2f}%")
        print(f"- OBV trend: {summary['obv_trend']:.4f}")
    print()
    if result.get("warnings"):
        print("## Warnings")
        for warning in result["warnings"]:
            print(f"- {warning}")
        print()
    if result.get("limitations"):
        print("## Limitations")
        for limitation in result["limitations"]:
            print(f"- {limitation}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate A-share main-force flow or daily proxy.")
    parser.add_argument("csv_path", type=Path, help="Daily OHLCV CSV or tick/transaction CSV.")
    parser.add_argument("--mode", choices=["auto", "daily", "ticks"], default="auto")
    parser.add_argument("--window", type=int, default=20, help="Rolling window for daily proxy.")
    parser.add_argument("--mid-threshold", type=float, default=40_000, help="Minimum amount for mid-size trade.")
    parser.add_argument("--big-threshold", type=float, default=200_000, help="Minimum amount for big trade.")
    parser.add_argument("--huge-threshold", type=float, default=1_000_000, help="Minimum amount for huge trade.")
    parser.add_argument("--volume-multiplier", type=float, default=1.0, help="Use 100 if tick volume is in hands.")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown.")
    args = parser.parse_args(argv)

    mode = detect_mode(args.csv_path) if args.mode == "auto" else args.mode
    if mode == "daily":
        result = summarize_daily_proxy(read_daily(args.csv_path), args.window)
    else:
        result = summarize_ticks(
            read_ticks(args.csv_path, args.volume_multiplier),
            args.mid_threshold,
            args.big_threshold,
            args.huge_threshold,
        )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_markdown(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
