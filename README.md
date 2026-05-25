# Theta Decay Dynamics

Research report on short-premium theta timing, Greek interactions, regime behavior, and Section 20 management rules — with a pilot SPY options-chain validation (Appendix B).

**Current release:** [`report/output/Theta_Decay_Dynamics_v6.2.pdf`](report/output/Theta_Decay_Dynamics_v6.2.pdf)

**Project history:** [`docs/HISTORY.md`](docs/HISTORY.md) — version timeline, reconstruction story, archived PDFs, and v6 pilot results.

## Repository layout

```text
├── report/           # PDF build — see report/README.md
│   ├── build_report.py
│   ├── generate_all_charts.py
│   ├── charts/       # PNG figures
│   └── output/       # Generated PDF
├── scripts/          # Databento pull + backtest — see scripts/README.md
├── docs/             # Spec & handoff notes — see docs/README.md
├── data/             # Local only — see data/README.md
└── archive/          # Report history — see archive/README.md
```

## Quick start (PDF only)

See [`report/README.md`](report/README.md) for file inventory. From the repo root:
```bash
pip install -r requirements.txt
python report/generate_all_charts.py
python report/build_report.py
python report/audit_report.py
```

## Optional: chain validation pipeline

Requires a Databento API key. See [`docs/Databento_v6_Spec.md`](docs/Databento_v6_Spec.md) and [`scripts/README.md`](scripts/README.md).

```bash
pip install -r requirements-databento.txt
cp .env.example .env   # add DATABENTO_API_KEY
python scripts/pull_databento.py external
python scripts/build_chain_eod.py
python scripts/backtest_managed_put.py
python scripts/backtest_report_v6.py
python report/build_report.py
```

## Not in git

- `.env` — API keys
- `data/*` — OPRA parquet and backtest outputs (~10 GB locally; layout described in `data/README.md`)
- `archive/scratch/`, `archive/cursor-skills/` — local reconstruction scratch and personal tooling
- Intermediate PDF builds in `archive/old_pdfs/` (`*_draft`, `*_build`, `*_layout`, `*_rebuilt`)

**In git:** milestone PDFs (`archive/old_pdfs/`), legacy source bundle (`archive/legacy/`), and `archive/README.md`.

## License

Add a license before public release if required.
