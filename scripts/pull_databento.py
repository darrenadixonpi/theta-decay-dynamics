#!/usr/bin/env python3
"""
Batch-download OPRA.PILLAR data for SPY.OPT (see Databento_v6_Spec.md).

Examples:
  python scripts/pull_databento.py smoke
  python scripts/pull_databento.py cost --start 2022-06-01 --end 2022-07-01
  python scripts/pull_databento.py pull --start 2022-06 --end 2022-06 --schema definition
  python scripts/pull_databento.py external
"""

from __future__ import annotations

import argparse
import calendar
import csv
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.request import urlopen

import databento as db
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from db_common import (  # noqa: E402
    DATASET,
    DEFAULT_SCHEMAS,
    EXTERNAL_DIR,
    PARENT_SYMBOL,
    ensure_data_dirs,
    monthly_budget_usd,
    opra_parquet_path,
    require_api_key,
)


def _client() -> db.Historical:
    return db.Historical(require_api_key())


def _month_starts(start: str, end: str) -> list[tuple[str, str, str]]:
    """Return (YYYY-MM label, inclusive start, exclusive end) for each calendar month."""
    start_ts = pd.Timestamp(start + "-01" if len(start) == 7 else start)
    end_ts = pd.Timestamp(end + "-01" if len(end) == 7 else end)
    if len(end) == 7:
        last_day = calendar.monthrange(end_ts.year, end_ts.month)[1]
        end_ts = pd.Timestamp(f"{end_ts.year:04d}-{end_ts.month:02d}-{last_day:02d}") + pd.Timedelta(days=1)
    else:
        end_ts = end_ts + pd.Timedelta(days=1)

    months: list[tuple[str, str, str]] = []
    cursor = pd.Timestamp(start_ts.year, start_ts.month, 1)
    while cursor < end_ts:
        label = f"{cursor.year:04d}-{cursor.month:02d}"
        month_end = cursor + pd.offsets.MonthBegin(1)
        months.append((label, cursor.strftime("%Y-%m-%d"), month_end.strftime("%Y-%m-%d")))
        cursor = month_end
    return months


def _schema_window(schema: str, month_start: str, month_end: str) -> tuple[str, str]:
    if schema == "cbbo-1m":
        return (
            f"{month_start}T09:30:00-04:00",
            f"{(pd.Timestamp(month_end) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')}T16:00:00-04:00",
        )
    return month_start, month_end


def estimate_cost(
    client: db.Historical,
    schema: str,
    start: str,
    end: str,
) -> float:
    win_start, win_end = _schema_window(schema, start, end)
    return float(
        client.metadata.get_cost(
            dataset=DATASET,
            schema=schema,
            stype_in="parent",
            symbols=[PARENT_SYMBOL],
            start=win_start,
            end=win_end,
        )
    )


def pull_month(
    client: db.Historical,
    schema: str,
    month_label: str,
    month_start: str,
    month_end: str,
    *,
    dry_run: bool,
    force: bool,
    budget: float,
) -> None:
    out = opra_parquet_path(schema, month_label)
    if out.exists() and not force:
        print(f"  skip {out.name} (exists; use --force)")
        return

    win_start, win_end = _schema_window(schema, month_start, month_end)
    cost = estimate_cost(client, schema, month_start, month_end)
    print(f"  {schema} {month_label}: est. ${cost:.4f} -> {out.name}")

    if dry_run:
        return
    if cost > budget:
        print(f"  SKIP: ${cost:.4f} exceeds budget ${budget:.2f}")
        return

    store = client.timeseries.get_range(
        dataset=DATASET,
        schema=schema,
        stype_in="parent",
        stype_out="instrument_id",
        symbols=[PARENT_SYMBOL],
        start=win_start,
        end=win_end,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    store.to_parquet(str(out), pretty_ts=True, map_symbols=True)
    print(f"  wrote {out}")


def cmd_smoke(_: argparse.Namespace) -> None:
    client = _client()
    ensure_data_dirs()
    print("Smoke test: definition (1 day)")
    store = client.timeseries.get_range(
        dataset=DATASET,
        schema="definition",
        stype_in="parent",
        stype_out="instrument_id",
        symbols=[PARENT_SYMBOL],
        start="2024-01-02",
        end="2024-01-03",
    )
    df = store.to_df()
    puts = df[df.get("instrument_class", pd.Series(dtype=str)) == "P"] if "instrument_class" in df.columns else df
    print(f"  rows={len(df)} puts={len(puts)} cols={list(df.columns)[:8]}...")


def cmd_cost(args: argparse.Namespace) -> None:
    client = _client()
    total = 0.0
    schemas = args.schema or list(DEFAULT_SCHEMAS)
    for label, m_start, m_end in _month_starts(args.start, args.end):
        for schema in schemas:
            cost = estimate_cost(client, schema, m_start, m_end)
            total += cost
            print(f"{label} {schema}: ${cost:.4f}")
    print(f"TOTAL: ${total:.4f}")


def cmd_pull(args: argparse.Namespace) -> None:
    client = _client()
    ensure_data_dirs()
    schemas = args.schema or list(DEFAULT_SCHEMAS)
    budget = args.budget if args.budget is not None else monthly_budget_usd()

    for label, m_start, m_end in _month_starts(args.start, args.end):
        print(f"Month {label}")
        for schema in schemas:
            pull_month(
                client,
                schema,
                label,
                m_start,
                m_end,
                dry_run=args.dry_run,
                force=args.force,
                budget=budget,
            )


def _download_csv(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=60) as resp:
        dest.write_bytes(resp.read())
    print(f"  wrote {dest}")


def cmd_external(_: argparse.Namespace) -> None:
    """Fetch free SPY/VIX daily series (no Databento spend)."""
    ensure_data_dirs()
    vix_url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"
        "&cos=1&observation_start=2016-01-01"
    )
    _download_csv(vix_url, EXTERNAL_DIR / "vixcls.csv")

    try:
        import yfinance as yf
    except ImportError as exc:
        raise SystemExit("Install yfinance for SPY download: pip install yfinance") from exc

    spy = yf.download("SPY", start="2016-01-01", progress=False, auto_adjust=True)
    if spy.empty:
        raise SystemExit("yfinance returned no SPY data")
    spy = spy.reset_index()
    spy["Date"] = pd.to_datetime(spy["Date"]).dt.strftime("%Y-%m-%d")
    out = EXTERNAL_DIR / "spy_daily.csv"
    spy[["Date", "Close"]].rename(columns={"Date": "date", "Close": "close"}).to_csv(out, index=False)
    print(f"  wrote {out}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Databento pull helper for Theta Decay Dynamics v6")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("smoke", help="1-day definition pull sanity check")

    cost = sub.add_parser("cost", help="Estimate API cost for a date range")
    cost.add_argument("--start", required=True, help="YYYY-MM or YYYY-MM-DD")
    cost.add_argument("--end", required=True, help="YYYY-MM or YYYY-MM-DD")
    cost.add_argument("--schema", action="append", help="Repeatable; default all P0/P1 schemas")

    pull = sub.add_parser("pull", help="Download monthly parquet batches")
    pull.add_argument("--start", required=True, help="YYYY-MM or YYYY-MM-DD")
    pull.add_argument("--end", required=True, help="YYYY-MM or YYYY-MM-DD")
    pull.add_argument("--schema", action="append", help="Repeatable; default definition+statistics+cbbo-1m")
    pull.add_argument("--dry-run", action="store_true", help="Cost only; no download")
    pull.add_argument("--force", action="store_true", help="Overwrite existing parquet")
    pull.add_argument("--budget", type=float, help="Max USD per month-schema (default: DATABENTO_MONTHLY_BUDGET)")

    sub.add_parser("external", help="Download VIX (FRED) and SPY (yfinance) CSVs")
    return p


def main() -> None:
    args = build_parser().parse_args()
    dispatch = {
        "smoke": cmd_smoke,
        "cost": cmd_cost,
        "pull": cmd_pull,
        "external": cmd_external,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
