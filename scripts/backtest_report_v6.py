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

from db_common import (  # noqa: E402
    CENSORED_EXIT_REASONS,
    DERIVED_DIR,
    IV_RANK_MIN,
    V6_OUTPUT_DIR,
    ensure_data_dirs,
)

TRADES_PATH = DERIVED_DIR / "trades_backtest.parquet"
CHAIN_PATH = DERIVED_DIR / "chain_eod.parquet"
OUT_PATH = V6_OUTPUT_DIR / "v6_summary.json"
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 42
METHODOLOGY_VERSION = "6.4"


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


def _managed_minus_hold(trades: pd.DataFrame) -> dict[str, object]:
    paired = []
    for _, day in trades.groupby("entry_date"):
        h = day[day["strategy"] == "hold"]["pnl_net"]
        m = day[day["strategy"] == "managed"]["pnl_net"]
        if len(h) == 1 and len(m) == 1:
            paired.append(float(m.iloc[0] - h.iloc[0]))
    if not paired:
        return {}
    diff = pd.Series(paired)
    return {
        "count": int(len(diff)),
        "median_diff": float(diff.median()),
        "median_diff_ci": bootstrap_ci(diff, "median"),
        "mean_diff": float(diff.mean()),
    }


def _core_summary(trades: pd.DataFrame) -> dict[str, object]:
    out: dict[str, object] = {
        "n_trades": int(len(trades)),
        "n_entries": int(trades["entry_date"].nunique()) if not trades.empty else 0,
        "date_range": {},
        "by_strategy": {},
        "by_regime": {},
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
    out["managed_minus_hold"] = _managed_minus_hold(trades)

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

    return out


def _exit_reason_counts(trades: pd.DataFrame) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for strategy, grp in trades.groupby("strategy"):
        vc = grp["exit_reason"].value_counts()
        counts[strategy] = {str(k): int(v) for k, v in vc.items()}
    return counts


def _by_regime_paired(trades: pd.DataFrame) -> dict[str, object]:
    out: dict[str, object] = {}
    for regime, grp in trades.groupby("regime"):
        diffs: list[float] = []
        identical = 0
        hold_higher = 0
        managed_higher = 0
        for _, day in grp.groupby("entry_date"):
            h = day[day["strategy"] == "hold"]["pnl_net"]
            m = day[day["strategy"] == "managed"]["pnl_net"]
            if len(h) != 1 or len(m) != 1:
                continue
            diff = float(m.iloc[0] - h.iloc[0])
            diffs.append(diff)
            if abs(diff) < 1e-6:
                identical += 1
            elif diff > 0:
                managed_higher += 1
            else:
                hold_higher += 1
        if not diffs:
            continue
        series = pd.Series(diffs)
        out[str(regime)] = {
            "count": int(len(diffs)),
            "median_diff": float(series.median()),
            "mean_diff": float(series.mean()),
            "weeks_identical_pnl": identical,
            "weeks_hold_higher": hold_higher,
            "weeks_managed_higher": managed_higher,
        }
    return out


def _pilot_paired_summary(trades: pd.DataFrame) -> dict[str, object]:
    diffs: list[float] = []
    identical = hold_higher = managed_higher = 0
    for _, day in trades.groupby("entry_date"):
        h = day[day["strategy"] == "hold"]["pnl_net"]
        m = day[day["strategy"] == "managed"]["pnl_net"]
        if len(h) != 1 or len(m) != 1:
            continue
        diff = float(m.iloc[0] - h.iloc[0])
        diffs.append(diff)
        if abs(diff) < 1e-6:
            identical += 1
        elif diff > 0:
            managed_higher += 1
        else:
            hold_higher += 1
    if not diffs:
        return {}
    series = pd.Series(diffs)
    return {
        "weeks_total": int(len(diffs)),
        "weeks_identical_pnl": identical,
        "weeks_hold_higher": hold_higher,
        "weeks_managed_higher": managed_higher,
        "median_diff": float(series.median()),
        "mean_diff": float(series.mean()),
    }


def _chain_scope() -> dict[str, object]:
    if not CHAIN_PATH.is_file():
        return {}
    chain = pd.read_parquet(CHAIN_PATH)
    chain["date"] = pd.to_datetime(chain["date"])
    return {
        "n_sessions": int(chain["date"].nunique()),
        "n_rows": int(len(chain)),
        "date_start": chain["date"].min().strftime("%Y-%m-%d"),
        "date_end": chain["date"].max().strftime("%Y-%m-%d"),
    }


def _by_entry_dte_managed(trades: pd.DataFrame) -> dict[str, object]:
    managed = trades[trades["strategy"] == "managed"].copy()
    if managed.empty:
        return {}
    managed["dte_bucket"] = pd.cut(
        managed["entry_dte"],
        bins=[39, 42, 45, 50],
        labels=["40-42", "43-45", "46-50"],
        include_lowest=True,
    )
    out: dict[str, object] = {}
    for bucket, grp in managed.groupby("dte_bucket", observed=True):
        net = grp["pnl_net"]
        out[str(bucket)] = {
            "count": int(len(grp)),
            "median_pnl_net": float(net.median()),
            "win_rate": float((net > 0).mean()),
        }
    return out


def summarize(trades: pd.DataFrame) -> dict[str, object]:
    trades = trades.copy()
    if not trades.empty:
        trades["entry_date"] = pd.to_datetime(trades["entry_date"])

    out = _core_summary(trades)
    out["methodology_version"] = METHODOLOGY_VERSION
    out["bootstrap"] = {"n_resamples": BOOTSTRAP_N, "ci_level": 0.95}
    out["by_moneyness_bucket"] = {}
    out["exit_reason_counts"] = _exit_reason_counts(trades) if not trades.empty else {}
    out["by_entry_dte_managed"] = _by_entry_dte_managed(trades) if not trades.empty else {}
    out["by_regime_paired_diff"] = _by_regime_paired(trades) if not trades.empty else {}
    out["pilot_paired_summary"] = _pilot_paired_summary(trades) if not trades.empty else {}
    out["chain_scope"] = _chain_scope()

    if trades.empty:
        out["censoring"] = {}
        out["summary_excluding_censored"] = _core_summary(trades)
        out["summary_iv_rank_proxy_ge_50"] = _core_summary(trades)
        return out

    managed = trades[trades["strategy"] == "managed"]
    censored_mask = managed["exit_reason"].isin(CENSORED_EXIT_REASONS)
    out["censoring"] = {
        "n_censored_managed": int(censored_mask.sum()),
        "n_managed": int(len(managed)),
        "pct_censored": float(censored_mask.mean()),
        "reasons": list(CENSORED_EXIT_REASONS),
    }

    uncensored = trades[~trades["exit_reason"].isin(CENSORED_EXIT_REASONS)]
    out["summary_excluding_censored"] = _core_summary(uncensored)

    iv_pass_dates = trades.groupby("entry_date")["iv_rank_pass"].first()
    iv_dates = iv_pass_dates[iv_pass_dates].index
    iv_trades = trades[trades["entry_date"].isin(iv_dates)]
    out["summary_iv_rank_proxy_ge_50"] = _core_summary(iv_trades)
    out["iv_rank_proxy"] = {
        "lookback_days": 252,
        "min_percentile": IV_RANK_MIN,
        "n_entries_passing": int(len(iv_dates)),
        "n_entries_total": int(trades["entry_date"].nunique()),
        "note": "252-day VIXCLS percentile rank; proxy for Section 20 IV Rank, not SPY IV rank.",
    }

    trades["m_bucket"] = pd.cut(
        trades["moneyness_sk"],
        bins=[1.05, 1.08, 1.11, 1.15],
        labels=["1.05-1.08", "1.08-1.11", "1.11-1.15"],
        include_lowest=True,
    )
    managed_only = trades[trades["strategy"] == "managed"]
    for bucket, grp in managed_only.groupby("m_bucket", observed=True):
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
