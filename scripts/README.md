# Databento v6 pipeline

See [Databento_v6_Spec.md](../docs/Databento_v6_Spec.md) for scope, schemas, and acceptance criteria.

## Setup

```bash
pip install -r requirements-databento.txt
```

Copy `.env.example` to `.env` and set `DATABENTO_API_KEY`. The project `.gitignore` excludes `.env`, `data/`, and `*.parquet`.

## Run order

```bash
# 1. Sanity check API + schema (1 day, small charge)
python scripts/pull_databento.py smoke

# 2. Free regime overlays
python scripts/pull_databento.py external

# 3. Estimate cost before downloading
python scripts/pull_databento.py cost --start 2022-06 --end 2022-06

# 4. Pull one pilot month (dry-run first)
python scripts/pull_databento.py pull --start 2022-06 --end 2022-06 --dry-run
python scripts/pull_databento.py pull --start 2022-06 --end 2022-06

# 5. Build EOD chain panel (cbbo EOD cached under data/derived/cbbo_eod/)
python scripts/build_chain_eod.py --start 2022-06-01 --end 2022-06-30

# Force rebuild cbbo cache after re-pulling a month:
python scripts/build_chain_eod.py --refresh-cbbo

# 6. Backtest Section 20 rules
python scripts/backtest_managed_put.py --start 2022-06-01 --end 2022-06-30

# 7. Summary JSON for Appendix B
python scripts/backtest_report_v6.py

# 8. Rebuild PDF
python report/build_report.py
```

## Scripts

| Script | Output |
|---|---|
| `pull_databento.py` | `data/opra/{schema}/SPY.OPT/YYYY-MM.parquet` |
| `build_chain_eod.py` | `data/derived/chain_eod.parquet` |
| `backtest_managed_put.py` | `data/derived/trades_backtest.parquet` |
| `backtest_report_v6.py` | `data/v6/v6_summary.json` |
