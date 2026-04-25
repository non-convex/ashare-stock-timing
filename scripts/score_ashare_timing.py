#!/usr/bin/env python3
"""
Compute a deterministic A-share technical timing snapshot from daily OHLCV CSV.

Input columns are flexible. Recognized aliases include:
date, open, high, low, close, volume, amount, and turnover.
The parser also recognizes common local-market CSV column aliases.

This script intentionally scores only what can be inferred from the CSV. It does
not replace market/sector/fund/chip due diligence.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ALIASES = {
    "date": ["date", "\u65e5\u671f", "trade_date", "\u65f6\u95f4"],
    "open": ["open", "\u5f00\u76d8", "open_price"],
    "high": ["high", "\u6700\u9ad8", "high_price"],
    "low": ["low", "\u6700\u4f4e", "low_price"],
    "close": ["close", "\u6536\u76d8", "close_price"],
    "volume": ["volume", "\u6210\u4ea4\u91cf", "vol"],
    "amount": ["amount", "\u6210\u4ea4\u989d", "\u6210\u4ea4\u91d1\u989d", "turnover_value"],
    "turnover": ["turnover", "\u6362\u624b\u7387", "turnover_rate"],
}


@dataclass
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    amount: float | None = None
    turnover: float | None = None


def normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "").replace("_", "")


def find_column(headers: list[str], canonical: str) -> str | None:
    normalized = {normalize_header(header): header for header in headers}
    for alias in ALIASES[canonical]:
        key = normalize_header(alias)
        if key in normalized:
            return normalized[key]
    return None


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "-", "None", "nan", "NaN"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_bars(path: Path) -> list[Bar]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit("CSV has no header row.")
        columns = {key: find_column(reader.fieldnames, key) for key in ALIASES}
        required = ["date", "open", "high", "low", "close"]
        missing = [key for key in required if not columns[key]]
        if missing:
            raise SystemExit(f"Missing required columns: {', '.join(missing)}")

        bars: list[Bar] = []
        for row in reader:
            values = {key: to_float(row.get(column)) if column else None for key, column in columns.items()}
            if values["open"] is None or values["high"] is None or values["low"] is None or values["close"] is None:
                continue
            bars.append(
                Bar(
                    date=str(row[columns["date"]]).strip(),
                    open=values["open"],
                    high=values["high"],
                    low=values["low"],
                    close=values["close"],
                    volume=values["volume"],
                    amount=values["amount"],
                    turnover=values["turnover"],
                )
            )
    bars.sort(key=lambda bar: bar.date)
    if len(bars) < 60:
        raise SystemExit("Need at least 60 valid daily bars for a useful score.")
    return bars


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def prior_sma(values: list[float], period: int, lookback: int = 5) -> float | None:
    if len(values) < period + lookback:
        return None
    subset = values[:-lookback]
    return sum(subset[-period:]) / period


def ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    ema = [values[0]]
    for value in values[1:]:
        ema.append(alpha * value + (1 - alpha) * ema[-1])
    return ema


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains = []
    losses = []
    for index in range(1, len(values)):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(bars: list[Bar], period: int = 14) -> float | None:
    if len(bars) <= period:
        return None
    true_ranges = []
    for index, bar in enumerate(bars):
        if index == 0:
            true_ranges.append(bar.high - bar.low)
        else:
            prev_close = bars[index - 1].close
            true_ranges.append(max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close)))
    return sum(true_ranges[-period:]) / period


def obv(bars: list[Bar]) -> list[float] | None:
    if any(bar.volume is None for bar in bars):
        return None
    values = [0.0]
    for index in range(1, len(bars)):
        direction = 1 if bars[index].close > bars[index - 1].close else -1 if bars[index].close < bars[index - 1].close else 0
        values.append(values[-1] + direction * float(bars[index].volume or 0))
    return values


def cmf(bars: list[Bar], period: int = 20) -> float | None:
    if len(bars) < period or any(bar.volume is None for bar in bars[-period:]):
        return None
    money_flow_volume = 0.0
    total_volume = 0.0
    for bar in bars[-period:]:
        high_low = bar.high - bar.low
        multiplier = 0.0 if high_low == 0 else ((bar.close - bar.low) - (bar.high - bar.close)) / high_low
        volume = float(bar.volume or 0)
        money_flow_volume += multiplier * volume
        total_volume += volume
    if total_volume == 0:
        return None
    return money_flow_volume / total_volume


def pct(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "n/a"
    return f"{value:.2f}%"


def money(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "n/a"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.2f}e8"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.2f}e4"
    return f"{value:.2f}"


def score_snapshot(bars: list[Bar], entry: float | None, stop: float | None) -> dict:
    closes = [bar.close for bar in bars]
    amounts = [bar.amount for bar in bars if bar.amount is not None]
    latest = bars[-1]
    ma = {period: sma(closes, period) for period in [5, 10, 20, 60, 120, 250]}
    ma_prior = {period: prior_sma(closes, period) for period in [20, 60]}
    atr14 = atr(bars)
    atr_pct = (atr14 / latest.close * 100) if atr14 else None
    rsi14 = rsi(closes)
    obv_values = obv(bars)
    cmf20 = cmf(bars)
    amount20 = sum(amounts[-20:]) / 20 if len(amounts) >= 20 else None
    amount_ratio = latest.amount / amount20 if latest.amount is not None and amount20 else None
    high20 = max(closes[-20:])
    high55 = max(closes[-55:])
    low20 = min(closes[-20:])
    ema12 = ema_series(closes, 12)
    ema26 = ema_series(closes, 26)
    macd_line = [a - b for a, b in zip(ema12[-len(ema26):], ema26)] if ema12 and ema26 else []
    signal = ema_series(macd_line, 9) if macd_line else []
    macd_hist = macd_line[-1] - signal[-1] if macd_line and signal else None

    trend_score = 0
    if ma[20] and latest.close > ma[20]:
        trend_score += 4
    if ma[60] and latest.close > ma[60]:
        trend_score += 4
    if ma[120] and latest.close > ma[120]:
        trend_score += 2
    if ma[20] and ma[60] and ma[20] > ma[60]:
        trend_score += 4
    if ma[20] and ma_prior[20] and ma[20] > ma_prior[20]:
        trend_score += 3
    if ma[60] and ma_prior[60] and ma[60] > ma_prior[60]:
        trend_score += 2
    if latest.close >= high20:
        trend_score += 1
    trend_score = min(trend_score, 20)

    volume_score = 0
    if amount_ratio:
        if 1.5 <= amount_ratio <= 3.0:
            volume_score += 6
        elif 1.0 <= amount_ratio < 1.5:
            volume_score += 4
        elif amount_ratio > 3.0 and latest.close >= latest.open:
            volume_score += 3
    if obv_values and len(obv_values) >= 21 and obv_values[-1] > sum(obv_values[-20:]) / 20:
        volume_score += 4
    if cmf20 is not None and cmf20 > 0:
        volume_score += 4
    if rsi14 is not None and 45 <= rsi14 <= 75:
        volume_score += 3
    if latest.close >= latest.low + 0.75 * (latest.high - latest.low if latest.high > latest.low else 0):
        volume_score += 3
    volume_score = min(volume_score, 20)

    risk_score = 10
    warnings = []
    if atr_pct is not None and atr_pct > 8:
        risk_score -= 3
        warnings.append("ATR% is high; volatility risk is elevated")
    if amount20 is not None and amount20 < 100_000_000:
        risk_score -= 2
        warnings.append("20-day average trading amount is below RMB 100 million; watch liquidity")
    if entry is not None and stop is not None:
        if stop >= entry:
            warnings.append("Stop price should not be above or equal to entry price")
            risk_score -= 4
        else:
            stop_pct = (entry - stop) / entry * 100
            if stop_pct > 8:
                risk_score -= 3
                warnings.append("Stop distance exceeds 8%; use a more conservative entry or position size")
            elif stop_pct <= 3:
                risk_score += 1
    risk_score = max(0, min(risk_score, 10))

    technical_total = trend_score + volume_score + risk_score
    technical_max = 50

    if ma[60] and latest.close < ma[60] and ma_prior[60] and ma[60] < ma_prior[60]:
        phase = "downtrend_or_weak_rebound"
    elif ma[20] and ma[60] and latest.close > ma[20] > ma[60]:
        phase = "uptrend"
    elif latest.close >= high55:
        phase = "breakout_or_new_high"
    elif ma[20] and latest.close > ma[20]:
        phase = "repair_or_base_building_with_strength"
    else:
        phase = "range_or_base_building"

    rating = "watch"
    if technical_total >= 40:
        rating = "actionable-if-market-sector-confirm"
    elif technical_total < 28:
        rating = "avoid-or-wait"

    return {
        "date": latest.date,
        "close": latest.close,
        "phase": phase,
        "rating": rating,
        "technical_score": technical_total,
        "technical_score_max": technical_max,
        "scores": {
            "stock_trend": trend_score,
            "volume_funds_csv_only": volume_score,
            "risk_execution_csv_only": risk_score,
        },
        "metrics": {
            "ma5": ma[5],
            "ma10": ma[10],
            "ma20": ma[20],
            "ma60": ma[60],
            "ma120": ma[120],
            "ma250": ma[250],
            "atr14": atr14,
            "atr_pct": atr_pct,
            "rsi14": rsi14,
            "cmf20": cmf20,
            "amount20": amount20,
            "amount_ratio": amount_ratio,
            "high20": high20,
            "high55": high55,
            "low20": low20,
            "macd_hist": macd_hist,
        },
        "warnings": warnings,
        "notes": [
            "This is a CSV-only technical snapshot.",
            "Complete methodology still requires market regime, sector strength, margin, Dragon Tiger list, chips, and announcements.",
        ],
    }


def print_markdown(snapshot: dict) -> None:
    metrics = snapshot["metrics"]
    print("# A-Share Technical Timing Snapshot")
    print()
    print(f"- Date: {snapshot['date']}")
    print(f"- Close: {snapshot['close']:.3f}")
    print(f"- Phase: {snapshot['phase']}")
    print(f"- Rating: {snapshot['rating']}")
    print(f"- CSV technical score: {snapshot['technical_score']}/{snapshot['technical_score_max']}")
    print()
    print("## Scores")
    for key, value in snapshot["scores"].items():
        print(f"- {key}: {value}")
    print()
    print("## Key Metrics")
    for key in ["ma5", "ma10", "ma20", "ma60", "ma120", "ma250"]:
        value = metrics.get(key)
        print(f"- {key}: {'n/a' if value is None else f'{value:.3f}'}")
    print(f"- ATR14%: {pct(metrics.get('atr_pct'))}")
    print(f"- RSI14: {'n/a' if metrics.get('rsi14') is None else f'{metrics['rsi14']:.2f}'}")
    print(f"- CMF20: {'n/a' if metrics.get('cmf20') is None else f'{metrics['cmf20']:.3f}'}")
    print(f"- 20-day average amount: {money(metrics.get('amount20'))}")
    ratio = metrics.get("amount_ratio")
    print(f"- Latest amount / 20-day amount: {'n/a' if ratio is None else f'{ratio:.2f}x'}")
    print(f"- 20-day high/low: {metrics['high20']:.3f} / {metrics['low20']:.3f}")
    print(f"- 55-day high: {metrics['high55']:.3f}")
    print()
    if snapshot["warnings"]:
        print("## Warnings")
        for warning in snapshot["warnings"]:
            print(f"- {warning}")
        print()
    print("## Notes")
    for note in snapshot["notes"]:
        print(f"- {note}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score A-share daily OHLCV technical timing.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--entry", type=float, help="Planned entry price for risk scoring.")
    parser.add_argument("--stop", type=float, help="Planned stop price for risk scoring.")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown.")
    args = parser.parse_args(argv)

    bars = read_bars(args.csv_path)
    snapshot = score_snapshot(bars, args.entry, args.stop)
    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print_markdown(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
