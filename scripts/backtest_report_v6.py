#!/usr/bin/env python3
"""
Summarize backtest outputs for v6 appendix / build_report.py consumption.

Output: data/v6/v6_summary.json

Usage:
  python scripts/backtest_report_v6.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from db_common import DERIVED_DIR, V6_OUTPUT_DIR, ensure_data_dirs  # noqa: E402

TRADES_PATH = DERIVED_DIR / "trades_backtest.parquet"
OUT_PATH = V6_OUTPUT_DIR / "v6_summary.json"
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 42


def sharpe(series: pd.Series) -> float | None:
    if len(series) < 2:
        return None
    std = series.std(ddof=1)
    if std == 0 or np.isnan(std):
        return None
    return float(series.mean() / std * np.sqrt(52))  # weekly entries


def bootstrap_ci(
    values: pd.Series | np.ndarray,
    stat: str = "median",
    *,
    n: int = BOOTSTRAP_N,
    seed: int = BOOTSTRAP_SEED,
    alpha: float = 0.05,
) -> dict[str, float | None]:
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return {"lo": None, "hi": None, "n": int(len(arr))}

    rng = np.random.default_rng(seed)
    if stat == "median":
        fn = np.median
    elif stat == "p05":
        fn = lambda x: np.quantile(x, 0.05)
    else:
        raise ValueError(stat)

    boots = np.array([fn(rng.choice(arr, size=len(arr), replace=True)) for _ in range(n)])
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return {"lo": float(lo), "hi": float(hi), "n": int(len(arr))}


def _strategy_block(grp: pd.DataFrame) -> dict[str, object]:
    net = grp["pnl_net"]
    med_ci = bootstrap_ci(net, "median")
    p05_ci = bootstrap_ci(net, "p05")
    return {
        "count": int(len(grp)),
        "median_pnl_net": float(net.median()),
        "median_pnl_net_ci": med_ci,
        "p05_pnl_net": float(net.quantile(0.05)),
        "p05_pnl_net_ci": p05_ci,
        "p95_pnl_net": float(net.quantile(0.95)),
        "win_rate": float((net > 0).mean()),
        "sharpe_weekly_ann": sharpe(net),
    }


def summarize(trades: pd.DataFrame) -> dict[str, object]:
    out: dict[str, object] = {
        "n_trades": int(len(trades)),
        "n_entries": int(trades["entry_date"].nunique()) if not trades.empty else 0,
        "date_range": {},
        "bootstrap": {"n_resamples": BOOTSTRAP_N, "ci_level": 0.95},
        "by_strategy": {},
        "by_regime": {},
        "by_moneyness_bucket": {},
        "managed_minus_hold": {},
    }
    if trades.empty:
        return out

    trades = trades.copy()
    trades["entry_date"] = pd.to_datetime(trades["entry_date"])
    out["date_range"] = {
        "start": trades["entry_date"].min().strftime("%Y-%m-%d"),
        "end": trades["entry_date"].max().strftime("%Y-%m-%d"),
    }

    paired = []
    for _, day in trades.groupby("entry_date"):
        h = day[day["strategy"] == "hold"]["pnl_net"]
        m = day[day["strategy"] == "managed"]["pnl_net"]
        if len(h) == 1 and len(m) == 1:
            paired.append(float(m.iloc[0] - h.iloc[0]))
    if paired:
        diff = pd.Series(paired)
        out["managed_minus_hold"] = {
            "count": int(len(diff)),
            "median_diff": float(diff.median()),
            "median_diff_ci": bootstrap_ci(diff, "median"),
            "mean_diff": float(diff.mean()),
        }

    for strategy, grp in trades.groupby("strategy"):
        out["by_strategy"][strategy] = _strategy_block(grp)

    for regime, grp in trades.groupby("regime"):
        block: dict[str, object] = {"count": int(len(grp))}
        for strategy, sub in grp.groupby("strategy"):
            net = sub["pnl_net"]
            block[strategy] = {
                "count": int(len(sub)),
                "median_pnl_net": float(net.median()),
                "median_pnl_net_ci": bootstrap_ci(net, "median"),
                "p05_pnl_net": float(net.quantile(0.05)),
                "p05_pnl_net_ci": bootstrap_ci(net, "p05"),
            }
        out["by_regime"][regime] = block

    trades["m_bucket"] = pd.cut(
        trades["moneyness_sk"],
        bins=[1.05, 1.08, 1.11, 1.15],
        labels=["1.05-1.08", "1.08-1.11", "1.11-1.15"],
        include_lowest=True,
    )
    managed = trades[trades["strategy"] == "managed"]
    for bucket, grp in managed.groupby("m_bucket", observed=True):
        net = grp["pnl_net"]
        out["by_moneyness_bucket"][str(bucket)] = {
            "count": int(len(grp)),
            "median_pnl_net": float(net.median()),
            "sharpe_weekly_ann": sharpe(net),
        }

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build v6 summary JSON from backtest trades")
    parser.add_argument("--trades", type=Path, default=TRADES_PATH)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    ensure_data_dirs()
    if not args.trades.is_file():
        raise SystemExit(f"Missing {args.trades}. Run backtest_managed_put.py first.")

    trades = pd.read_parquet(args.trades)
    summary = summarize(trades)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
