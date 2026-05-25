#!/usr/bin/env python3
"""
Build daily EOD option chain panel from pulled OPRA parquet files.

Output: data/derived/chain_eod.parquet

Usage:
  python scripts/build_chain_eod.py
  python scripts/build_chain_eod.py --start 2022-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from db_common import (  # noqa: E402
    CBBO_EOD_CACHE_DIR,
    CONTRACT_MULTIPLIER,
    DERIVED_DIR,
    EXTERNAL_DIR,
    MAX_SPREAD_PCT,
    MIN_BID,
    MIN_OI,
    MIN_VOLUME,
    MONEYNESS_MAX,
    MONEYNESS_MIN,
    OPRA_DIR,
    PARENT_SYMBOL,
    ensure_data_dirs,
)

ET = "America/New_York"
OUT_PATH = DERIVED_DIR / "chain_eod.parquet"
OCC_RE = re.compile(
    r"^(?P<root>[A-Z]{1,6})\s+(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})(?P<cp>[CP])(?P<strike>\d{8})$"
)


def _glob_parquet(schema: str) -> list[Path]:
    folder = OPRA_DIR / schema / PARENT_SYMBOL
    return sorted(folder.glob("*.parquet")) if folder.is_dir() else []


def _first_col(df: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None


def _price_series(df: pd.DataFrame, bid_col: str, ask_col: str) -> pd.Series:
    bid = pd.to_numeric(df[bid_col], errors="coerce")
    ask = pd.to_numeric(df[ask_col], errors="coerce")
    mid = (bid + ask) / 2.0
    mid = mid.where((bid > 0) & (ask > 0) & (ask >= bid), other=pd.NA)
    return mid


def _parse_occ(symbol: str) -> dict[str, object] | None:
    m = OCC_RE.match(str(symbol).strip().upper())
    if not m:
        return None
    strike = int(m.group("strike")) / 1000.0
    expiry = pd.Timestamp(
        2000 + int(m.group("yy")),
        int(m.group("mm")),
        int(m.group("dd")),
    ).date()
    return {
        "symbol": str(symbol).strip(),
        "option_type": m.group("cp"),
        "strike": strike,
        "expiry": expiry,
    }


def load_spy_daily() -> pd.DataFrame:
    path = EXTERNAL_DIR / "spy_daily.csv"
    if not path.is_file():
        raise SystemExit(
            f"Missing {path}. Run: python scripts/pull_databento.py external"
        )
    spy = pd.read_csv(path, parse_dates=["date"])
    spy["date"] = pd.to_datetime(spy["date"]).dt.tz_localize(None).dt.normalize()
    return spy.rename(columns={"close": "spot"})


def load_definitions() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in _glob_parquet("definition"):
        df = _read_parquet(path)
        if df.empty:
            continue
        sym_col = _first_col(df, ("raw_symbol", "symbol"))
        if sym_col is None:
            continue
        chunk = df.copy()
        chunk["symbol"] = chunk[sym_col].astype(str)
        if "instrument_class" in chunk.columns:
            chunk["option_type"] = chunk["instrument_class"].astype(str).str.upper().str[0]
        if "strike_price" in chunk.columns:
            strike = pd.to_numeric(chunk["strike_price"], errors="coerce")
            chunk["strike"] = strike.where(strike < 1e4, strike / 1e9)
        if "expiration" in chunk.columns:
            chunk["expiry"] = pd.to_datetime(chunk["expiration"], utc=True).dt.tz_convert(ET).dt.date
        frames.append(chunk[["symbol"] + [c for c in ("option_type", "strike", "expiry") if c in chunk.columns]])
    if not frames:
        return pd.DataFrame(columns=["symbol", "option_type", "strike", "expiry"])
    out = pd.concat(frames, ignore_index=True)
    if "ts_recv" in out.columns:
        out = out.sort_values("ts_recv")
    elif "ts_event" in out.columns:
        out = out.sort_values("ts_event")
    out = out.drop_duplicates("symbol", keep="last")
    parsed = out["symbol"].map(_parse_occ)
    for col in ("option_type", "strike", "expiry"):
        if col not in out.columns:
            out[col] = parsed.map(lambda x: x[col] if x else None)
        else:
            fill = parsed.map(lambda x: x[col] if x else None)
            out[col] = out[col].where(out[col].notna(), fill)
    out["option_type"] = out["option_type"].astype(str).str.upper().str[0]
    out["strike"] = pd.to_numeric(out["strike"], errors="coerce")
    out["expiry"] = pd.to_datetime(out["expiry"], errors="coerce").dt.date
    return out.dropna(subset=["symbol", "strike", "expiry"])


def _read_parquet(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "ts_recv" not in df.columns and df.index.name in {"ts_recv", "ts_event"}:
        df = df.reset_index()
    return df


def _timestamp_series(df: pd.DataFrame) -> pd.Series:
    for col in ("ts_recv", "ts_event"):
        if col in df.columns and df[col].notna().any():
            return pd.to_datetime(df[col], utc=True)
    raise ValueError("No usable timestamp column found")


def load_statistics() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in _glob_parquet("statistics"):
        df = _read_parquet(path)
        if df.empty:
            continue
        sym_col = _first_col(df, ("raw_symbol", "symbol"))
        if sym_col is None:
            continue
        chunk = df.copy()
        chunk["symbol"] = chunk[sym_col].astype(str)
        ts = _timestamp_series(chunk).dt.tz_convert(ET)
        chunk["date"] = ts.dt.normalize().dt.tz_localize(None)
        oi_col = _first_col(chunk, ("open_interest", "oi"))
        vol_col = _first_col(chunk, ("volume", "total_volume"))
        if oi_col:
            chunk["oi"] = pd.to_numeric(chunk[oi_col], errors="coerce")
        elif "quantity" in chunk.columns:
            # stat_type 9 = open interest in OPRA statistics schema
            chunk["oi"] = pd.to_numeric(chunk["quantity"], errors="coerce")
        if vol_col:
            chunk["volume"] = pd.to_numeric(chunk[vol_col], errors="coerce")
        keep = ["symbol", "date"] + [c for c in ("oi", "volume") if c in chunk.columns]
        if len(keep) <= 2:
            continue
        frames.append(chunk[keep])
    if not frames:
        return pd.DataFrame(columns=["symbol", "date", "oi", "volume"])
    out = pd.concat(frames, ignore_index=True)
    agg = {col: "max" for col in ("oi", "volume") if col in out.columns}
    if not agg:
        return pd.DataFrame(columns=["symbol", "date", "oi", "volume"])
    return out.groupby(["symbol", "date"], as_index=False).agg(agg)


def _cbbo_cache_path(source: Path) -> Path:
    return CBBO_EOD_CACHE_DIR / source.name


def _process_cbbo_month(source: Path) -> pd.DataFrame:
    import pyarrow.parquet as pq

    accumulated: pd.DataFrame | None = None
    pf = pq.ParquetFile(source)
    for batch in pf.iter_batches(
        batch_size=2_000_000,
        columns=["ts_recv", "symbol", "bid_px_00", "ask_px_00"],
    ):
        chunk = batch.to_pandas()
        if chunk.index.name in {"ts_recv", "ts_event"}:
            chunk = chunk.reset_index()
        if chunk.empty:
            continue
        ts = pd.to_datetime(chunk["ts_recv"], utc=True).dt.tz_convert(ET)
        rth = (ts.dt.time >= pd.Timestamp("09:30").time()) & (
            ts.dt.time < pd.Timestamp("16:00").time()
        )
        chunk = chunk.loc[rth].copy()
        if chunk.empty:
            continue
        ts = ts.loc[rth]
        chunk["_ts"] = ts
        chunk["date"] = ts.dt.normalize().dt.tz_localize(None)
        chunk["bid"] = pd.to_numeric(chunk["bid_px_00"], errors="coerce")
        chunk["ask"] = pd.to_numeric(chunk["ask_px_00"], errors="coerce")
        chunk["mid"] = _price_series(chunk, "bid", "ask")
        chunk["symbol"] = chunk["symbol"].astype(str)
        batch_eod = (
            chunk.sort_values("_ts")
            .groupby(["symbol", "date"], as_index=False)
            .tail(1)[["symbol", "date", "bid", "ask", "mid", "_ts"]]
        )
        accumulated = (
            batch_eod
            if accumulated is None
            else (
                pd.concat([accumulated, batch_eod], ignore_index=True)
                .sort_values("_ts")
                .groupby(["symbol", "date"], as_index=False)
                .tail(1)
            )
        )
    if accumulated is None or accumulated.empty:
        return pd.DataFrame(columns=["symbol", "date", "bid", "ask", "mid", "spread_pct"])
    out = accumulated.drop(columns="_ts")
    out["spread_pct"] = (out["ask"] - out["bid"]) / out["mid"]
    return out


def load_cbbo_eod(*, refresh: bool = False) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in _glob_parquet("cbbo-1m"):
        cache = _cbbo_cache_path(path)
        stale = not cache.is_file() or cache.stat().st_mtime < path.stat().st_mtime
        if not refresh and not stale:
            print(f"  cbbo cache hit: {cache.name}")
            frames.append(pd.read_parquet(cache))
            continue
        print(f"  cbbo cache build: {path.name} -> {cache.name}")
        eod = _process_cbbo_month(path)
        cache.parent.mkdir(parents=True, exist_ok=True)
        eod.to_parquet(cache, index=False)
        print(f"  cached {len(eod):,} eod rows")
        frames.append(eod)
    if not frames:
        return pd.DataFrame(columns=["symbol", "date", "bid", "ask", "mid", "spread_pct"])
    return pd.concat(frames, ignore_index=True)


def build_chain(start: str | None, end: str | None, *, refresh_cbbo: bool = False) -> pd.DataFrame:
    defs = load_definitions()
    stats = load_statistics()
    quotes = load_cbbo_eod(refresh=refresh_cbbo)
    spy = load_spy_daily()

    if quotes.empty:
        raise SystemExit("No cbbo-1m parquet found under data/opra/cbbo-1m/SPY.OPT/")

    chain = quotes.merge(defs, on="symbol", how="left")
    if not stats.empty:
        chain = chain.merge(stats, on=["symbol", "date"], how="left")

    chain = chain[chain["option_type"] == "P"].copy()
    chain = chain.merge(spy, on="date", how="inner")
    chain["strike"] = pd.to_numeric(chain["strike"], errors="coerce")
    chain["spot"] = pd.to_numeric(chain["spot"], errors="coerce")
    chain["dte"] = (pd.to_datetime(chain["expiry"]) - chain["date"]).dt.days
    chain["moneyness_sk"] = chain["spot"] / chain["strike"]

    if start:
        chain = chain[chain["date"] >= pd.Timestamp(start)]
    if end:
        chain = chain[chain["date"] <= pd.Timestamp(end)]

    oi_ok = chain["oi"].fillna(0) >= MIN_OI if "oi" in chain.columns else False
    vol_ok = chain["volume"].fillna(0) >= MIN_VOLUME if "volume" in chain.columns else False
    chain = chain[
        chain["mid"].notna()
        & (chain["bid"] >= MIN_BID)
        & (chain["ask"] > chain["bid"])
        & (chain["spread_pct"] <= MAX_SPREAD_PCT)
        & (chain["moneyness_sk"].between(MONEYNESS_MIN, MONEYNESS_MAX))
        & (oi_ok | vol_ok)
    ]
    return chain.sort_values(["date", "symbol"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build chain_eod.parquet from OPRA pulls")
    parser.add_argument("--start", help="Inclusive YYYY-MM-DD")
    parser.add_argument("--end", help="Inclusive YYYY-MM-DD")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument(
        "--refresh-cbbo",
        action="store_true",
        help="Rebuild per-month cbbo EOD cache from raw cbbo-1m pulls",
    )
    args = parser.parse_args()

    ensure_data_dirs()
    chain = build_chain(args.start, args.end, refresh_cbbo=args.refresh_cbbo)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    chain.to_parquet(args.out, index=False)
    print(f"Wrote {args.out} ({len(chain):,} rows, {chain['date'].nunique()} sessions)")


if __name__ == "__main__":
    main()
