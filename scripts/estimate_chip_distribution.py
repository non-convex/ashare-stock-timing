#!/usr/bin/env python3
"""
Estimate A-share chip/cost distribution from daily OHLCV data.

This is a local CYQ-style proxy, not a vendor's proprietary chip distribution.
If turnover is available, the script models daily float replacement. Otherwise
it falls back to a rolling volume/amount-at-price distribution.
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
    "open": ["open", "开盘", "open_price"],
    "high": ["high", "最高", "high_price"],
    "low": ["low", "最低", "low_price"],
    "close": ["close", "收盘", "close_price"],
    "volume": ["volume", "成交量", "vol"],
    "amount": ["amount", "成交额", "成交金额", "turnover_value"],
    "turnover": ["turnover", "换手率", "turnover_rate"],
}


@dataclass
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    amount: float | None
    turnover: float | None


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


def read_bars(path: Path) -> list[Bar]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        columns = {key: find_column(headers, key) for key in ALIASES}
        missing = [key for key in ["date", "open", "high", "low", "close"] if not columns[key]]
        if missing:
            raise SystemExit(f"Missing required columns: {', '.join(missing)}")
        bars: list[Bar] = []
        for row in reader:
            open_ = to_float(row.get(columns["open"]))
            high = to_float(row.get(columns["high"]))
            low = to_float(row.get(columns["low"]))
            close = to_float(row.get(columns["close"]))
            if open_ is None or high is None or low is None or close is None:
                continue
            bars.append(
                Bar(
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
    if len(bars) < 30:
        raise SystemExit("Need at least 30 daily bars for chip distribution proxy.")
    return bars


def amount_weight(bar: Bar) -> float:
    if bar.amount is not None and bar.amount > 0:
        return bar.amount
    if bar.volume is not None and bar.volume > 0:
        return bar.volume * bar.close
    return 0.0


def make_bins(low: float, high: float, bins: int) -> list[float]:
    if high <= low:
        return [low]
    step = (high - low) / bins
    return [low + step * (index + 0.5) for index in range(bins)]


def distribute_bar(bar: Bar, centers: list[float]) -> list[float]:
    if not centers:
        return []
    low = min(bar.low, bar.high)
    high = max(bar.low, bar.high)
    typical = (bar.high + bar.low + 2 * bar.close) / 4
    half_range = max((high - low) / 2, 1e-9)
    weights = []
    for center in centers:
        if center < low or center > high:
            weights.append(0.0)
            continue
        triangular = max(0.05, 1 - abs(center - typical) / half_range)
        close_bias = 1 / (1 + abs(center - bar.close) / max(bar.close * 0.01, 1e-9))
        weights.append(triangular * (0.7 + 0.3 * close_bias))
    total = sum(weights)
    if total <= 0:
        nearest = min(range(len(centers)), key=lambda index: abs(centers[index] - bar.close))
        weights[nearest] = 1.0
        total = 1.0
    return [weight / total for weight in weights]


def weighted_quantile(centers: list[float], weights: list[float], quantile: float) -> float | None:
    total = sum(weights)
    if total <= 0:
        return None
    threshold = total * quantile
    running = 0.0
    for center, weight in sorted(zip(centers, weights), key=lambda item: item[0]):
        running += weight
        if running >= threshold:
            return center
    return centers[-1] if centers else None


def local_peaks(centers: list[float], weights: list[float], top_n: int) -> list[dict]:
    if not centers:
        return []
    candidates = []
    for index, weight in enumerate(weights):
        left = weights[index - 1] if index > 0 else -1
        right = weights[index + 1] if index < len(weights) - 1 else -1
        if weight >= left and weight >= right and weight > 0:
            candidates.append((index, weight))
    if not candidates:
        candidates = list(enumerate(weights))
    candidates.sort(key=lambda item: item[1], reverse=True)
    peaks = []
    used: set[int] = set()
    min_gap = max(1, len(centers) // 30)
    for index, weight in candidates:
        if any(abs(index - used_index) <= min_gap for used_index in used):
            continue
        used.add(index)
        peaks.append({"price": centers[index], "weight": weight})
        if len(peaks) >= top_n:
            break
    total = sum(weights)
    for peak in peaks:
        peak["weight_pct"] = peak["weight"] / total * 100 if total else 0.0
    return peaks


def concentration_state(concentration_70: float | None, top_peak_share: float, peak_dominance: float) -> str:
    if concentration_70 is None:
        return "unknown"
    if concentration_70 <= 0.16 and top_peak_share >= 2.0 and peak_dominance >= 1.4:
        return "single_peak_concentrated"
    if concentration_70 <= 0.22:
        return "moderately_concentrated"
    if concentration_70 >= 0.38:
        return "dispersed_multi_peak"
    return "balanced"


def estimate_distribution(bars: list[Bar], lookback: int, bins: int, peak_count: int) -> dict:
    window = bars[-lookback:] if len(bars) > lookback else bars
    latest = window[-1]
    low = min(bar.low for bar in window)
    high = max(bar.high for bar in window)
    centers = make_bins(low, high, bins)
    use_turnover = sum(1 for bar in window if bar.turnover is not None and bar.turnover > 0) >= len(window) * 0.7
    distribution = [0.0 for _ in centers]

    for bar in window:
        day_shape = distribute_bar(bar, centers)
        if use_turnover:
            turnover_fraction = min(max((bar.turnover or 0.0) / 100, 0.0), 1.0)
            distribution = [value * (1 - turnover_fraction) for value in distribution]
            distribution = [value + turnover_fraction * shape for value, shape in zip(distribution, day_shape)]
        else:
            weight = amount_weight(bar)
            distribution = [value + weight * shape for value, shape in zip(distribution, day_shape)]

    total = sum(distribution)
    if total <= 0:
        raise SystemExit("Cannot build distribution: volume/amount/turnover data are insufficient.")
    weights = [value / total for value in distribution]

    q05 = weighted_quantile(centers, weights, 0.05)
    q15 = weighted_quantile(centers, weights, 0.15)
    q50 = weighted_quantile(centers, weights, 0.50)
    q85 = weighted_quantile(centers, weights, 0.85)
    q95 = weighted_quantile(centers, weights, 0.95)
    concentration_70 = ((q85 - q15) / q50) if q15 and q50 and q85 else None
    concentration_90 = ((q95 - q05) / q50) if q05 and q50 and q95 else None
    profit_ratio = sum(weight for center, weight in zip(centers, weights) if center <= latest.close)
    overhead_ratio = 1 - profit_ratio
    peaks = local_peaks(centers, weights, peak_count)
    top_peak_share = peaks[0]["weight_pct"] if peaks else 0.0
    second_peak_share = peaks[1]["weight_pct"] if len(peaks) > 1 else 0.0
    peak_dominance = top_peak_share / second_peak_share if second_peak_share > 0 else 99.0
    price_position = (latest.close - low) / (high - low) if high > low else 0.5
    top_peak_position = (peaks[0]["price"] - low) / (high - low) if peaks and high > low else None
    state = concentration_state(concentration_70, top_peak_share, peak_dominance)

    lifecycle = "mixed_or_unclear"
    if state in {"single_peak_concentrated", "moderately_concentrated"} and top_peak_position is not None and top_peak_position <= 0.45 and price_position <= 0.60:
        lifecycle = "low_cost_concentration_base"
    elif profit_ratio >= 0.85 and price_position >= 0.70 and state in {"single_peak_concentrated", "moderately_concentrated"}:
        lifecycle = "high_profit_concentration_distribution_risk"
    elif state == "dispersed_multi_peak":
        lifecycle = "dispersed_transition"
    elif profit_ratio >= 0.75 and price_position >= 0.65:
        lifecycle = "markup_or_profit_zone"

    supports = [
        peak for peak in peaks
        if peak["price"] < latest.close
    ][:3]
    resistances = [
        peak for peak in peaks
        if peak["price"] > latest.close
    ][:3]

    warnings = [
        "This is a CYQ-style proxy from daily OHLCV, not a vendor/proprietary chip distribution.",
        "Use as support/resistance and lifecycle evidence only after confirming trend, volume, and event risks.",
    ]
    if not use_turnover:
        warnings.append("Turnover is missing or sparse; distribution used rolling amount/volume-at-price rather than float replacement.")

    return {
        "mode": "daily_chip_distribution_proxy",
        "lookback_bars": len(window),
        "latest": {
            "date": latest.date,
            "close": latest.close,
            "price_position_in_lookback_range": price_position,
        },
        "method": "turnover_replacement" if use_turnover else "rolling_volume_amount_at_price",
        "cost_quantiles": {
            "q05": q05,
            "q15": q15,
            "q50": q50,
            "q85": q85,
            "q95": q95,
        },
        "concentration": {
            "state": state,
            "concentration_70_width_pct": concentration_70,
            "concentration_90_width_pct": concentration_90,
            "top_peak_share_pct": top_peak_share,
            "peak_dominance": peak_dominance,
        },
        "profit_overhang": {
            "profit_ratio": profit_ratio,
            "overhead_ratio": overhead_ratio,
        },
        "peaks": peaks,
        "support_peaks_below_close": supports,
        "resistance_peaks_above_close": resistances,
        "lifecycle": lifecycle,
        "warnings": warnings,
        "usage_rules": [
            "Low-cost concentrated base is only a watch condition; buy requires right-side breakout and volume/fund confirmation.",
            "Pullback to a broken cost-peak upper area with shrinking volume can be a second-entry candidate.",
            "High profit ratio plus high-level concentration or bottom-peak disappearance is distribution risk, not a hold signal.",
        ],
    }


def print_markdown(result: dict) -> None:
    latest = result["latest"]
    concentration = result["concentration"]
    profit = result["profit_overhang"]
    print("# A-Share Chip Distribution Proxy")
    print()
    print(f"- Date: {latest['date']}")
    print(f"- Close: {latest['close']:.3f}")
    print(f"- Method: {result['method']}")
    print(f"- Lifecycle: {result['lifecycle']}")
    print(f"- Concentration state: {concentration['state']}")
    width = concentration["concentration_70_width_pct"]
    print(f"- 70% cost width: {'n/a' if width is None else f'{width:.2%}'}")
    print(f"- Profit ratio: {profit['profit_ratio']:.2%}")
    print(f"- Overhead ratio: {profit['overhead_ratio']:.2%}")
    print()
    print("## Peaks")
    for peak in result["peaks"]:
        print(f"- price={peak['price']:.3f}, weight={peak['weight_pct']:.2f}%")
    print()
    if result["warnings"]:
        print("## Warnings")
        for warning in result["warnings"]:
            print(f"- {warning}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate CYQ-style chip/cost distribution from daily OHLCV CSV.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--lookback", type=int, default=250, help="Number of recent bars to use.")
    parser.add_argument("--bins", type=int, default=120, help="Number of price bins.")
    parser.add_argument("--peaks", type=int, default=5, help="Number of distribution peaks to output.")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown.")
    args = parser.parse_args(argv)

    result = estimate_distribution(read_bars(args.csv_path), args.lookback, args.bins, args.peaks)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_markdown(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

