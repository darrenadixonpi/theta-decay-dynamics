"""Shared paths, env loading, and Databento constants for v6 validation."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OPRA_DIR = DATA_DIR / "opra"
EQUITY_DIR = DATA_DIR / "equity"
EXTERNAL_DIR = DATA_DIR / "external"
DERIVED_DIR = DATA_DIR / "derived"
CBBO_EOD_CACHE_DIR = DERIVED_DIR / "cbbo_eod"
V6_OUTPUT_DIR = DATA_DIR / "v6"

DATASET = "OPRA.PILLAR"
PARENT_SYMBOL = "SPY.OPT"
DEFAULT_SCHEMAS = ("definition", "statistics", "cbbo-1m")

# Section 20 / spec defaults
COMMISSION_PER_LEG = 0.65
CONTRACT_MULTIPLIER = 100
MONEYNESS_MIN = 1.05
MONEYNESS_MAX = 1.15
ENTRY_DTE_MIN = 35
ENTRY_DTE_MAX = 55
ENTRY_DTE_TARGET = 45
ENTRY_DTE_BAND = (40, 50)
PROFIT_FRACTION = 0.50
EXIT_DTE = 21
MAX_SPREAD_PCT = 0.15
MIN_BID = 0.05
MIN_OI = 100
MIN_VOLUME = 10

# Section 8 VIX regime bins
VIX_REGIMES = (
    ("low", 0.0, 15.0),
    ("normal", 15.0, 20.0),
    ("elevated", 20.0, 30.0),
    ("crisis", 30.0, float("inf")),
)


def load_env() -> None:
    """Load KEY=VALUE pairs from project-root .env (does not override existing env)."""
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_api_key() -> str:
    load_env()
    key = os.environ.get("DATABENTO_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "DATABENTO_API_KEY not set. Add it to .env or export it in your shell."
        )
    return key


def monthly_budget_usd() -> float:
    load_env()
    raw = os.environ.get("DATABENTO_MONTHLY_BUDGET", "25").strip()
    try:
        return float(raw)
    except ValueError:
        return 25.0


def ensure_data_dirs() -> None:
    for path in (
        OPRA_DIR,
        EQUITY_DIR,
        EXTERNAL_DIR,
        DERIVED_DIR,
        CBBO_EOD_CACHE_DIR,
        V6_OUTPUT_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
    for schema in DEFAULT_SCHEMAS:
        (OPRA_DIR / schema / PARENT_SYMBOL).mkdir(parents=True, exist_ok=True)


def opra_parquet_path(schema: str, year_month: str) -> Path:
    return OPRA_DIR / schema / PARENT_SYMBOL / f"{year_month}.parquet"


def vix_regime(vix: float) -> str:
    for name, lo, hi in VIX_REGIMES:
        if lo <= vix < hi:
            return name
    return "crisis"
