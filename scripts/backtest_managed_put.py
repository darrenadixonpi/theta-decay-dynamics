#!/usr/bin/env python3
"""
Backtest Section 20 managed short SPY put rules on chain_eod.parquet.

Output: data/derived/trades_backtest.parquet

Usage:
  python scripts/backtest_managed_put.py
  python scripts/backtest_managed_put.py --start 2022-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from db_common import (  # noqa: E402
    COMMISSION_PER_LEG,
    CONTRACT_MULTIPLIER,
    DERIVED_DIR,
    ENTRY_DTE_BAND,
    ENTRY_DTE_TARGET,
    EXIT_DTE,
    EXTERNAL_DIR,
    MONEYNESS_MAX,
    MONEYNESS_MIN,
    PROFIT_FRACTION,
    vix_regime,
)

CHAIN_PATH = DERIVED_DIR / "chain_eod.parquet"
OUT_PATH = DERIVED_DIR / "trades_backtest.parquet"


def load_vix() -> pd.DataFrame:
    path = EXTERNAL_DIR / "vixcls.csv"
    if not path.is_file():
        return pd.DataFrame(columns=["date", "vix"])
    vix = pd.read_csv(path)
    date_col = next(
        (c for c in ("DATE", "date", "observation_date") if c in vix.columns),
        vix.columns[0],
    )
    val_col = "VIXCLS" if "VIXCLS" in vix.columns else "vix"
    vix = vix[[date_col, val_col]].rename(columns={date_col: "date", val_col: "vix"})
    vix["date"] = pd.to_datetime(vix["date"], errors="coerce")
    vix["vix"] = pd.to_numeric(vix["vix"], errors="coerce")
    return vix.dropna().sort_values("date")


def entry_dates(dates: pd.Series) -> pd.DatetimeIndex:
    """Weekly entries on Fridays within each contiguous session block."""
    uniq = pd.DatetimeIndex(sorted(dates.unique()))
    if len(uniq) == 0:
        return pd.DatetimeIndex([])

    blocks: list[pd.DatetimeIndex] = []
    start = 0
    for i in range(1, len(uniq)):
        if (uniq[i] - uniq[i - 1]).days > 7:
            blocks.append(uniq[start:i])
            start = i
    blocks.append(uniq[start:])

    mapped: list[pd.Timestamp] = []
    for block in blocks:
        fridays = pd.date_range(block.min(), block.max(), freq="W-FRI")
        for friday in fridays:
            if friday in block:
                mapped.append(friday)
                continue
            prior = block[block <= friday]
            if len(prior):
                mapped.append(prior[-1])

    return pd.DatetimeIndex(sorted(set(mapped)))


def pick_entry(chain: pd.DataFrame, day: pd.Timestamp) -> pd.Series | None:
    day_chain = chain[chain["date"] == day].copy()
    if day_chain.empty:
        return None
    lo, hi = ENTRY_DTE_BAND
    day_chain = day_chain[day_chain["dte"].between(lo, hi)]
    day_chain = day_chain[day_chain["moneyness_sk"].between(MONEYNESS_MIN, MONEYNESS_MAX)]
    if day_chain.empty:
        return None
    day_chain["dte_dist"] = (day_chain["dte"] - ENTRY_DTE_TARGET).abs()
    day_chain["m_dist"] = (day_chain["moneyness_sk"] - 1.10).abs()
    day_chain = day_chain.sort_values(["dte_dist", "m_dist", "spread_pct"])
    return day_chain.iloc[0]


def round_trip_cost(entry_mid: float, exit_mid: float, entry_spread_pct: float, exit_spread_pct: float) -> float:
    entry_half = entry_spread_pct * entry_mid / 2.0
    exit_half = exit_spread_pct * exit_mid / 2.0
    spread_cost = (entry_half + exit_half) * CONTRACT_MULTIPLIER
    commission = 2 * COMMISSION_PER_LEG
    return spread_cost + commission


def simulate_trade(
    chain: pd.DataFrame,
    symbol: str,
    entry_date: pd.Timestamp,
    entry_mid: float,
    entry_spread_pct: float,
    expiry: object,
    *,
    managed: bool,
) -> dict[str, object]:
    path = chain[(chain["symbol"] == symbol) & (chain["date"] >= entry_date)].sort_values("date")
    if path.empty:
        return {}

    profit_target = PROFIT_FRACTION * entry_mid
    exit_date = path.iloc[-1]["date"]
    exit_mid = float(path.iloc[-1]["mid"])
    exit_spread_pct = float(path.iloc[-1]["spread_pct"])
    exit_reason = "last_mark"

    for _, row in path.iloc[1:].iterrows():
        mark = float(row["mid"])
        if managed:
            pnl_per_share = entry_mid - mark
            if pnl_per_share >= profit_target:
                exit_date = row["date"]
                exit_mid = mark
                exit_spread_pct = float(row["spread_pct"])
                exit_reason = "profit_50"
                break
            if int(row["dte"]) <= EXIT_DTE:
                exit_date = row["date"]
                exit_mid = mark
                exit_spread_pct = float(row["spread_pct"])
                exit_reason = "dte_21"
                break
        else:
            if pd.Timestamp(row["expiry"]) <= row["date"] or int(row["dte"]) <= 0:
                intrinsic = max(float(row["strike"]) - float(row["spot"]), 0.0)
                exit_date = row["date"]
                exit_mid = intrinsic
                exit_spread_pct = 0.0
                exit_reason = "expiry"
                break

    pnl_gross = (entry_mid - exit_mid) * CONTRACT_MULTIPLIER
    costs = round_trip_cost(entry_mid, exit_mid, entry_spread_pct, exit_spread_pct)
    return {
        "symbol": symbol,
        "entry_date": entry_date,
        "exit_date": exit_date,
        "expiry": expiry,
        "exit_reason": exit_reason,
        "entry_mid": entry_mid,
        "exit_mid": exit_mid,
        "pnl_gross": pnl_gross,
        "costs": costs,
        "pnl_net": pnl_gross - costs,
    }


def run_backtest(chain: pd.DataFrame, vix: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    if start:
        chain = chain[chain["date"] >= pd.Timestamp(start)]
    if end:
        chain = chain[chain["date"] <= pd.Timestamp(end)]

    entries = entry_dates(chain["date"])
    rows: list[dict[str, object]] = []

    for day in entries:
        pick = pick_entry(chain, day)
        if pick is None:
            continue
        base = {
            "entry_date": day,
            "strike": float(pick["strike"]),
            "spot": float(pick["spot"]),
            "moneyness_sk": float(pick["moneyness_sk"]),
            "entry_dte": int(pick["dte"]),
        }
        vix_row = vix[vix["date"] == day]
        regime = vix_regime(float(vix_row.iloc[0]["vix"])) if len(vix_row) else "unknown"

        for strategy, managed in (("managed", True), ("hold", False)):
            result = simulate_trade(
                chain,
                pick["symbol"],
                day,
                float(pick["mid"]),
                float(pick["spread_pct"]),
                pick["expiry"],
                managed=managed,
            )
            if not result:
                continue
            rows.append({**base, **result, "strategy": strategy, "regime": regime})

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest managed short put rules")
    parser.add_argument("--chain", type=Path, default=CHAIN_PATH)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--start", help="Inclusive YYYY-MM-DD")
    parser.add_argument("--end", help="Inclusive YYYY-MM-DD")
    args = parser.parse_args()

    if not args.chain.is_file():
        raise SystemExit(f"Missing {args.chain}. Run build_chain_eod.py first.")

    chain = pd.read_parquet(args.chain)
    chain["date"] = pd.to_datetime(chain["date"])
    vix = load_vix()
    trades = run_backtest(chain, vix, args.start, args.end)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    trades.to_parquet(args.out, index=False)
    n = trades["entry_date"].nunique() if not trades.empty else 0
    print(f"Wrote {args.out} ({len(trades):,} rows, {n} entry weeks)")


if __name__ == "__main__":
    main()
