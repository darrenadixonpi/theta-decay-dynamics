# Local data (not in git)

Generated and downloaded artifacts for the Databento validation pipeline. Expect **several GB** once OPRA months are pulled. Parquet files are gitignored everywhere (`*.parquet`).

## Layout

```text
data/
├── opra/                    # Raw Databento pulls
│   ├── definition/SPY.OPT/  #   YYYY-MM.parquet
│   ├── statistics/SPY.OPT/
│   └── cbbo-1m/SPY.OPT/
├── external/                # Free overlays (SPY daily, FRED VIX)
├── derived/                 # Built panels
│   ├── chain_eod.parquet    #   EOD option marks + Greeks inputs
│   ├── trades_backtest.parquet
│   └── cbbo_eod/            #   Per-session cbbo cache (speeds rebuilds)
└── v6/
    └── v6_summary.json      # Appendix B stats → consumed by build_report.py
```

## Populate

See [`scripts/README.md`](../scripts/README.md). Requires `DATABENTO_API_KEY` in `.env` (see `.env.example`).

Nothing here is required to rebuild the PDF from charts alone — only needed to refresh Appendix B chain results.
