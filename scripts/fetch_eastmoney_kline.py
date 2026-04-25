#!/usr/bin/env python3
"""
Fetch A-share daily K-line data from free public quote endpoints.

This script is for structured OHLCV data acquisition inside the
ashare-stock-timing skill. Use web search or official sources for current
announcements, Dragon Tiger list details, rule changes, and event risks.
"""

from __future__ import annotations

import argparse
import csv
import http.client
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


FIELDS = [
    "date",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "amplitude_pct",
    "pct_change",
    "change",
    "turnover",
]


def infer_secid(symbol: str) -> str:
    code = symbol.strip().split(".")[-1]
    if not code.isdigit() or len(code) != 6:
        raise SystemExit("Symbol must be a 6-digit A-share/index code or pass --secid explicitly.")
    if code.startswith(("5", "6", "9")):
        market = "1"
    else:
        market = "0"
    return f"{market}.{code}"


def normalize_adjust(adjust: str) -> str:
    mapping = {
        "none": "0",
        "": "0",
        "qfq": "1",
        "front": "1",
        "hfq": "2",
        "back": "2",
    }
    if adjust not in mapping:
        raise SystemExit("--adjust must be one of: none, qfq, hfq")
    return mapping[adjust]


def fetch_eastmoney_kline(secid: str, start: str, end: str, adjust: str) -> dict:
    query = {
        "secid": secid,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": normalize_adjust(adjust),
        "beg": start,
        "end": end,
    }
    encoded = urllib.parse.urlencode(query)
    urls = [
        "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + encoded,
        "http://push2his.eastmoney.com/api/qt/stock/kline/get?" + encoded,
    ]
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "close",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }
    last_error: Exception | None = None
    payload = ""
    for url in urls:
        for _ in range(3):
            request = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    payload = response.read().decode("utf-8")
                break
            except (urllib.error.URLError, TimeoutError, http.client.RemoteDisconnected) as exc:
                last_error = exc
        if payload:
            break
    if not payload:
        raise RuntimeError(f"Failed to fetch Eastmoney K-line data: {last_error}")
    parsed = json.loads(payload)
    if parsed.get("rc") not in (0, None):
        raise RuntimeError(f"Eastmoney returned rc={parsed.get('rc')}: {parsed.get('rt')}")
    data = parsed.get("data")
    if not data or not data.get("klines"):
        raise RuntimeError("No Eastmoney K-line data returned. Check symbol/secid, date range, and market prefix.")
    return data


def fetch_akshare_kline(symbol: str, start: str, end: str, adjust: str) -> dict:
    try:
        import akshare as ak  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("AKShare is not installed. Install optional dependency with: pip install akshare") from exc

    code = symbol.strip().split(".")[-1]
    if not code.isdigit() or len(code) != 6:
        raise SystemExit("AKShare source needs a 6-digit A-share code.")
    adjust_value = {"none": "", "qfq": "qfq", "hfq": "hfq"}[adjust]
    try:
        frame = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start,
            end_date=end,
            adjust=adjust_value,
        )
    except Exception as exc:  # noqa: BLE001 - preserve upstream message for diagnostics
        raise RuntimeError(f"Failed to fetch AKShare K-line data: {exc}") from exc

    if frame is None or frame.empty:
        raise RuntimeError(f"No AKShare K-line data returned for {code}.")

    column_map = {
        "date": "\u65e5\u671f",
        "open": "\u5f00\u76d8",
        "close": "\u6536\u76d8",
        "high": "\u6700\u9ad8",
        "low": "\u6700\u4f4e",
        "volume": "\u6210\u4ea4\u91cf",
        "amount": "\u6210\u4ea4\u989d",
        "amplitude_pct": "\u632f\u5e45",
        "pct_change": "\u6da8\u8dcc\u5e45",
        "change": "\u6da8\u8dcc\u989d",
        "turnover": "\u6362\u624b\u7387",
    }
    missing = [source for source in column_map.values() if source not in frame.columns]
    if missing:
        raise RuntimeError(f"AKShare response missing expected columns: {', '.join(missing)}")

    klines: list[str] = []
    for _, row in frame.iterrows():
        values = []
        for field in FIELDS:
            value = row[column_map[field]]
            if field == "date":
                values.append(str(value)[:10])
            else:
                values.append("" if value is None else str(value))
        klines.append(",".join(values))
    return {
        "name": code,
        "code": code,
        "market": "akshare",
        "klines": klines,
        "notes": [
            "AKShare stock_zh_a_hist is an optional dependency source.",
            "Columns are normalized from AKShare Chinese field names.",
        ],
    }


def baostock_code(symbol: str) -> str:
    code = symbol.strip().split(".")[-1]
    if not code.isdigit() or len(code) != 6:
        raise SystemExit("BaoStock source needs a 6-digit A-share code.")
    if code.startswith(("5", "6", "9")):
        prefix = "sh"
    else:
        prefix = "sz"
    return f"{prefix}.{code}"


def fetch_baostock_kline(symbol: str, start: str, end: str, adjust: str) -> dict:
    try:
        import baostock as bs  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("BaoStock is not installed. Install optional dependency with: pip install baostock") from exc

    code = baostock_code(symbol)
    adjust_flag = {"none": "3", "qfq": "2", "hfq": "1"}[adjust]
    start_date = yyyymmdd_to_dash(start)
    end_date = yyyymmdd_to_dash(end)
    fields = "date,code,open,high,low,close,volume,amount,pctChg,turn"

    login = bs.login()
    if getattr(login, "error_code", "0") != "0":
        raise RuntimeError(f"BaoStock login failed: {getattr(login, 'error_msg', '')}")
    try:
        result = bs.query_history_k_data_plus(
            code,
            fields,
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag=adjust_flag,
        )
        if getattr(result, "error_code", "0") != "0":
            raise RuntimeError(f"BaoStock query failed: {getattr(result, 'error_msg', '')}")

        klines: list[str] = []
        previous_close: float | None = None
        while result.next():
            item = dict(zip(result.fields, result.get_row_data()))
            if not item.get("open") or not item.get("close"):
                continue
            open_ = float(item["open"])
            high = float(item["high"])
            low = float(item["low"])
            close = float(item["close"])
            volume = item.get("volume", "")
            amount = item.get("amount", "")
            pct_change = float(item["pctChg"]) if item.get("pctChg") else 0.0
            change = close - previous_close if previous_close else 0.0
            amplitude = ((high - low) / previous_close * 100) if previous_close else 0.0
            turnover = item.get("turn", "")
            klines.append(
                ",".join(
                    [
                        item["date"],
                        f"{open_:.4f}",
                        f"{close:.4f}",
                        f"{high:.4f}",
                        f"{low:.4f}",
                        volume,
                        amount,
                        f"{amplitude:.4f}",
                        f"{pct_change:.4f}",
                        f"{change:.4f}",
                        turnover,
                    ]
                )
            )
            previous_close = close
    finally:
        bs.logout()

    if not klines:
        raise RuntimeError(f"No BaoStock K-line data returned for {code}.")
    return {
        "name": code,
        "code": code,
        "market": "baostock",
        "klines": klines,
        "notes": [
            "BaoStock is an optional dependency source.",
            "Adjustment flags: none=3, qfq=2, hfq=1.",
            "Amount and turnover are returned by BaoStock when available.",
        ],
    }


def yahoo_symbol(symbol: str) -> str:
    code = symbol.strip().split(".")[-1]
    if not code.isdigit() or len(code) != 6:
        raise SystemExit("Yahoo fallback needs a 6-digit A-share code.")
    if code.startswith(("5", "6", "9")):
        suffix = ".SS"
    elif code.startswith(("0", "2", "3")):
        suffix = ".SZ"
    elif code.startswith(("4", "8")):
        suffix = ".BJ"
    else:
        suffix = ".SZ"
    return f"{code}{suffix}"


def tencent_symbol(symbol: str) -> str:
    code = symbol.strip().split(".")[-1]
    if not code.isdigit() or len(code) != 6:
        raise SystemExit("Tencent fallback needs a 6-digit A-share code.")
    if code.startswith(("5", "6", "9")):
        prefix = "sh"
    elif code.startswith(("4", "8")):
        prefix = "bj"
    else:
        prefix = "sz"
    return f"{prefix}{code}"


def parse_yyyymmdd(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d").replace(tzinfo=timezone.utc)


def yyyymmdd_to_dash(value: str) -> str:
    return datetime.strptime(value, "%Y%m%d").strftime("%Y-%m-%d")


def urlopen_text(url: str, encoding: str = "utf-8", referer: str = "https://quote.eastmoney.com/") -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "close",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Referer": referer,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode(encoding, errors="replace")


def fetch_tencent_float_shares(ticker: str) -> float | None:
    url = f"https://qt.gtimg.cn/q={urllib.parse.quote(ticker)}"
    try:
        payload = urlopen_text(url, encoding="gbk", referer="https://gu.qq.com/")
    except (urllib.error.URLError, TimeoutError, http.client.RemoteDisconnected):
        return None
    if '="' not in payload:
        return None
    parts = payload.split('="', 1)[1].strip().rstrip('";').split("~")
    for index in [73, 72, 76]:
        if index < len(parts):
            try:
                shares = float(parts[index])
            except ValueError:
                continue
            if shares > 0:
                return shares
    return None


def fetch_tencent_kline(symbol: str, start: str, end: str, adjust: str) -> dict:
    ticker = tencent_symbol(symbol)
    start_dash = yyyymmdd_to_dash(start)
    end_dash = yyyymmdd_to_dash(end)
    calendar_days = (datetime.strptime(end, "%Y%m%d") - datetime.strptime(start, "%Y%m%d")).days + 1
    count = max(800, min(3000, int(calendar_days * 1.8)))
    adjust_key = {"none": "day", "qfq": "qfqday", "hfq": "hfqday"}[adjust]

    if adjust == "none":
        url = (
            "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?"
            f"param={ticker},day,{start_dash},{end_dash},{count}"
        )
    else:
        url = (
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?"
            f"param={ticker},day,{start_dash},{end_dash},{count},{adjust}"
        )
    raw_url = (
        "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?"
        f"param={ticker},day,{start_dash},{end_dash},{count}"
    )
    try:
        parsed = json.loads(urlopen_text(url, referer="https://gu.qq.com/"))
        raw_parsed = json.loads(urlopen_text(raw_url, referer="https://gu.qq.com/"))
    except (urllib.error.URLError, TimeoutError, http.client.RemoteDisconnected, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to fetch Tencent K-line data: {exc}") from exc

    data = parsed.get("data", {}).get(ticker)
    raw_data = raw_parsed.get("data", {}).get(ticker)
    if not data or adjust_key not in data:
        raise RuntimeError(f"No Tencent K-line data returned for {ticker}.")
    raw_rows = {row[0]: row for row in (raw_data or {}).get("day", [])}
    float_shares = fetch_tencent_float_shares(ticker)

    klines: list[str] = []
    previous_close: float | None = None
    for row in data[adjust_key]:
        if len(row) < 6:
            continue
        row_date = row[0]
        open_, close, high, low = [float(value) for value in row[1:5]]
        volume_hands = float(row[5])
        volume_shares = volume_hands * 100
        raw_row = raw_rows.get(row_date)
        amount = ""
        if raw_row and len(raw_row) >= 6:
            raw_open, raw_close, raw_high, raw_low = [float(value) for value in raw_row[1:5]]
            typical_price = (raw_open + raw_close + raw_high + raw_low) / 4
            amount = f"{typical_price * volume_shares:.2f}"
        turnover = ""
        if float_shares:
            turnover = f"{volume_shares / float_shares * 100:.4f}"
        amplitude = ((high - low) / previous_close * 100) if previous_close else 0.0
        change = (close - previous_close) if previous_close else 0.0
        pct_change = (change / previous_close * 100) if previous_close else 0.0
        klines.append(
            ",".join(
                [
                    row_date,
                    f"{open_:.4f}",
                    f"{close:.4f}",
                    f"{high:.4f}",
                    f"{low:.4f}",
                    f"{volume_shares:.0f}",
                    amount,
                    f"{amplitude:.4f}",
                    f"{pct_change:.4f}",
                    f"{change:.4f}",
                    turnover,
                ]
            )
        )
        previous_close = close
    if not klines:
        raise RuntimeError("Tencent payload contained no parseable K-line rows.")
    return {
        "name": ticker,
        "code": symbol,
        "market": "tencent",
        "klines": klines,
        "notes": [
            "Tencent K-line volume is converted from hands to shares.",
            "Historical amount is estimated from unadjusted typical price * volume because Tencent K-line does not expose exact historical amount.",
            "Turnover is estimated using latest float shares from Tencent quote when available.",
        ],
    }


def fetch_yahoo_kline(symbol: str, start: str, end: str, adjust: str) -> dict:
    ticker = yahoo_symbol(symbol)
    period1 = int(parse_yyyymmdd(start).timestamp())
    period2 = int((parse_yyyymmdd(end) + timedelta(days=1)).timestamp())
    query = {
        "period1": str(period1),
        "period2": str(period2),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "Connection": "close",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, http.client.RemoteDisconnected, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to fetch Yahoo K-line data: {exc}") from exc

    result = parsed.get("chart", {}).get("result")
    if not result:
        error = parsed.get("chart", {}).get("error")
        raise RuntimeError(f"No Yahoo K-line data returned: {error}")
    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = (item.get("indicators", {}).get("quote") or [{}])[0]
    adjclose = (item.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose") or []
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    klines: list[str] = []
    prior_close: float | None = None
    for index, timestamp in enumerate(timestamps):
        raw_open = opens[index] if index < len(opens) else None
        raw_high = highs[index] if index < len(highs) else None
        raw_low = lows[index] if index < len(lows) else None
        raw_close = closes[index] if index < len(closes) else None
        if raw_open is None or raw_high is None or raw_low is None or raw_close is None:
            continue
        scale = 1.0
        if adjust != "none" and index < len(adjclose) and adjclose[index] and raw_close:
            scale = float(adjclose[index]) / float(raw_close)
        open_ = float(raw_open) * scale
        high = float(raw_high) * scale
        low = float(raw_low) * scale
        close = float(raw_close) * scale
        volume = volumes[index] if index < len(volumes) and volumes[index] is not None else ""
        amplitude = ((high - low) / prior_close * 100) if prior_close else 0.0
        change = (close - prior_close) if prior_close else 0.0
        pct_change = (change / prior_close * 100) if prior_close else 0.0
        row_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
        klines.append(
            ",".join(
                [
                    row_date,
                    f"{open_:.4f}",
                    f"{close:.4f}",
                    f"{high:.4f}",
                    f"{low:.4f}",
                    str(volume),
                    "",
                    f"{amplitude:.4f}",
                    f"{pct_change:.4f}",
                    f"{change:.4f}",
                    "",
                ]
            )
        )
        prior_close = close
    if not klines:
        raise RuntimeError("Yahoo payload contained no parseable K-line rows.")
    return {
        "name": ticker,
        "code": symbol,
        "market": "yahoo",
        "klines": klines,
    }


def parse_rows(klines: list[str]) -> list[dict[str, str]]:
    rows = []
    for line in klines:
        parts = line.split(",")
        if len(parts) < len(FIELDS):
            continue
        rows.append(dict(zip(FIELDS, parts[: len(FIELDS)])))
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch A-share daily K-line CSV from free public data sources.")
    parser.add_argument("symbol", help="6-digit code, e.g. 000001, 600519, 300750. Ignored if --secid is set.")
    parser.add_argument("--secid", help="Eastmoney secid, e.g. 0.000001 or 1.600519.")
    parser.add_argument("--start", default="20180101", help="Start date YYYYMMDD.")
    parser.add_argument("--end", default=date.today().strftime("%Y%m%d"), help="End date YYYYMMDD.")
    parser.add_argument("--adjust", default="qfq", choices=["none", "qfq", "hfq"], help="Price adjustment mode.")
    parser.add_argument(
        "--source",
        default="auto",
        choices=["auto", "baostock", "akshare", "eastmoney", "tencent", "yahoo"],
        help="Data source. auto tries BaoStock/AKShare if installed, then Eastmoney, Tencent, Yahoo.",
    )
    parser.add_argument("--output", type=Path, help="Output CSV path. Defaults to <symbol>_daily.csv.")
    parser.add_argument("--json", action="store_true", help="Print metadata JSON after writing CSV.")
    args = parser.parse_args(argv)

    secid = args.secid or infer_secid(args.symbol)
    output = args.output or Path(f"{args.symbol}_daily.csv")
    data = None
    errors: list[str] = []
    if args.source in {"auto", "baostock"}:
        try:
            data = fetch_baostock_kline(args.symbol, args.start, args.end, args.adjust)
        except RuntimeError as exc:
            errors.append(str(exc))
            if args.source == "baostock":
                raise SystemExit(str(exc))
    if data is None and args.source in {"auto", "akshare"}:
        try:
            data = fetch_akshare_kline(args.symbol, args.start, args.end, args.adjust)
        except RuntimeError as exc:
            errors.append(str(exc))
            if args.source == "akshare":
                raise SystemExit(str(exc))
    if data is None and args.source in {"auto", "eastmoney"}:
        try:
            data = fetch_eastmoney_kline(secid, args.start, args.end, args.adjust)
        except RuntimeError as exc:
            errors.append(str(exc))
            if args.source == "eastmoney":
                raise SystemExit(str(exc))
    if data is None and args.source in {"auto", "tencent"}:
        try:
            data = fetch_tencent_kline(args.symbol, args.start, args.end, args.adjust)
        except RuntimeError as exc:
            errors.append(str(exc))
            if args.source == "tencent":
                raise SystemExit(str(exc))
    if data is None and args.source in {"auto", "yahoo"}:
        try:
            data = fetch_yahoo_kline(args.symbol, args.start, args.end, args.adjust)
        except RuntimeError as exc:
            errors.append(str(exc))
            raise SystemExit("; ".join(errors))
    rows = parse_rows(data["klines"])
    if not rows:
        raise SystemExit("K-line payload contained no parseable rows.")
    write_csv(output, rows)

    metadata = {
        "symbol": args.symbol,
        "secid": secid,
        "name": data.get("name"),
        "code": data.get("code"),
        "market": data.get("market"),
        "source": args.source if args.source != "auto" else data.get("market", "eastmoney"),
        "notes": data.get("notes", []),
        "adjust": args.adjust,
        "start": args.start,
        "end": args.end,
        "rows": len(rows),
        "output": str(output),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
    }
    if args.json:
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote {len(rows)} rows to {output}")
        print(f"{metadata['name'] or args.symbol} {rows[0]['date']} -> {rows[-1]['date']} adjust={args.adjust}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
