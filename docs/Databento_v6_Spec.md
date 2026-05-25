# Databento Pull Spec — Theta Decay Dynamics v6.0 Validation

**Purpose:** Historical validation appendix for *Theta Decay Dynamics* (currently v5.2).  
**Goal:** Replace simulated claims in Sections 12, 13, 15, and 21 with **real SPY options chain** results using the same management rules.

**Not in scope:** Live trading system, signal optimization (Section 7 constraint preserved), or rewrite of Sections 1–23.

---

## 0. What you already have (do not use for v6)

| Asset | Dataset | Verdict |
|---|---|---|
| `XNAS-20260505-*.zip` | `XNAS.ITCH` — MSFT equity trades/MBO/1m bars | ❌ Wrong asset class; one ~90‑minute slice on 2022‑06‑10 |
| `signal_summary.json` | SPY surface features Mar 2021–Mar 2023 | ✅ Keep for Section 7; too sparse for chain backtest |

---

## 1. Validation targets (map data → report)

| Report claim | Section | v6 metric | Minimum data |
|---|---|---|---|
| 45 DTE / 50% profit / 21 DTE floor | 20 | Managed vs hold P&amp;L distribution | Daily option marks, 3+ years |
| DTE 40–55 “competitive zone” | 12.1 | Sharpe by entry DTE | Same |
| OTM put Sharpe vs ATM | 12.4 | By moneyness bucket (S/K 1.05–1.20) | Strikes + spot |
| Crisis vs calm management value | 21 | 5th %ile P&amp;L by VIX regime | VIX or proxy + dates |
| Transaction drag | 9, 19 | Net P&amp;L after half-spread | Bid/ask at entry/exit |
| Peak theta timing (T*) | 3, 13.3 | Optional Phase 2 | More granular marks |

**Primary strategy (Phase 1):** Short **SPY put**, enter at **~45 DTE**, moneyness **S/K ∈ [1.05, 1.15]** (OTM put), exit on **50% max profit** or **21 DTE**, hold-to-expiry benchmark.

---

## 2. Databento datasets

### 2.1 Options (required)

| Field | Value |
|---|---|
| **Dataset** | `OPRA.PILLAR` |
| **Parent symbol** | `SPY.OPT` |
| **Symbology** | `stype_in="parent"`, `stype_out="instrument_id"` (OPRA maps to `raw_symbol` in output) |
| **History** | Apr 2013+ (trades/OHLCV/CBBO-1m); Mar 2023+ for some consolidated schemas |
| **Pricing model** | ~**$0.04/GB** historical (usage-based) + OPRA licensing if live |

### 2.2 Underlying & regime (required, can be cheap)

| Series | Preferred source | Fallback |
|---|---|---|
| **SPY daily close** | Databento `EQUS.MINI` or `XNAS.ITCH`, schema `ohlcv-1d`, symbol `SPY` | Free: Yahoo / Stooq (validation only) |
| **VIX daily close** | Not on OPRA as spot; use **FRED `VIXCLS`** or CBOE free CSV | Map to Section 8 regime bins |

> Pull SPY equity from Databento only if you want one vendor; otherwise OPRA options + free VIX/SPY saves ~90% of non-options cost.

### 2.3 Do not pull initially

- Full `cmbp-1` / `trades` tick for all `SPY.OPT` (terabytes)
- `XNAS.ITCH` `mbo` unless building equity execution sim (your MSFT sample)
- `ALL_SYMBOLS` on OPRA

---

## 3. Schemas & sampling (cost-optimized)

Pull in this order. **Stop after Phase 1** if budget cap hit.

| Priority | Schema | Granularity | Use |
|---|---|---|---|
| **P0** | `definition` | Daily (UTC midnight snapshot) | Strike, expiry, put/call, listing status |
| **P0** | `statistics` | Daily | Open interest, official session stats |
| **P1** | `cbbo-1m` | 1 bar/min | **EOD mark** = last RTH bar (~15:59 ET); bid/ask for spread |
| **P2** | `ohlcv-1d` | Daily | Mid/close sanity check; volume filters |
| **P3** | `tcbbo` | Per trade | Only if Phase 2 needs fill realism (expensive) |

**EOD convention:** For each `(date, option_symbol)`, take the **last `cbbo-1m` record with `ts_event` in [09:30, 16:00) America/New_York**.

**Mark price for backtest:**
```text
mid = (bid_px_00 + ask_px_00) / 2   # if both > 0
else last sale from statistics / ohlcv close
```

**Spread / costs (from report Section 9):**
```text
half_spread_pct = (ask - bid) / (2 * mid)
round_trip_cost = 2 * half_spread_pct * premium + commission
# Default commission: $0.65/contract/leg retail
```

---

## 4. Universe filters (apply after download)

Filter each **entry date** `t0` (weekly, see §5):

| Filter | Rule |
|---|---|
| **Type** | Put only (`instrument_class` / OCC char `P`) |
| **DTE at entry** | 35 ≤ DTE ≤ 55 (target 45) |
| **Moneyness** | 1.05 ≤ S/K ≤ 1.15 using SPY close at `t0` |
| **Liquidity** | OI ≥ 100 **or** daily volume ≥ 10; bid ≥ $0.05 |
| **Quote quality** | bid &lt; ask, spread/mid ≤ 15% (else skip strike) |
| **Exclusions** | Symbols with `security_update_action=Deleted` before exit |

**Optional Phase 2:** add SPX (`SPX.OPT` or `SPXW.OPT`) for index-settled comparison.

---

## 5. Backtest calendar

| Parameter | Value | Report ref |
|---|---|---|
| **Entry cadence** | Weekly — every **Friday** (or Monday if Friday holiday) | Section 20 |
| **Entry DTE target** | Closest expiry with **40 ≤ DTE ≤ 50** | 45 DTE convention |
| **Profit exit** | Close when `open_pnl ≥ 0.50 * entry_premium` | 50% rule |
| **Time exit** | Close when **DTE ≤ 21** | 21 DTE floor |
| **Hold benchmark** | No interim exits; mark to expiry/settlement | Section 21 |
| **Position size** | 1 contract; P&amp;L in $/contract × 100 | Normalize later |

**Date ranges:**

| Phase | Period | Role |
|---|---|---|
| **Phase 1 (MVP)** | 2022‑01‑01 → 2024‑12‑31 | Recent regimes (post‑COVID vol, 2022 bear) |
| **Phase 2** | 2016‑01‑01 → 2024‑12‑31 | Full cycle + OOS split |
| **OOS split** | Train ≤ 2021‑12‑31, test ≥ 2022‑01‑01 | Report Section 12 style |

---

## 6. API pull plan (Python)

### 6.1 Setup

```bash
pip install databento pandas pyarrow
```

Create `.env` (never commit):
```text
DATABENTO_API_KEY=your_key_here
```

### 6.2 Cost estimate before each batch

Use Databento **metadata / cost API** (portal or `client.metadata.get_cost`) for each `(dataset, schema, start, end, symbols)` tuple before downloading.

**Rough order-of-magnitude (SPY puts only, filtered client-side):**

| Phase | Schemas | Calendar | Est. raw size |
|---|---|---|---|
| MVP | `definition` + `statistics` + `cbbo-1m` | 3 years daily | ~1–5 GB |
| Full | same | 9 years | ~5–20 GB |
| Tick (skip) | `cmbp-1` | 1 month | Can exceed MVP entire budget |

At $0.04/GB, MVP historical data might be **$0.20–$2** in platform fees — **licensing** may dominate if you add live; confirm in portal.

### 6.3 Reference pull — definitions (1 day smoke test)

```python
import os
import databento as db

client = db.Historical(os.environ["DATABENTO_API_KEY"])

data = client.timeseries.get_range(
    dataset="OPRA.PILLAR",
    schema="definition",
    stype_in="parent",
    symbols=["SPY.OPT"],
    start="2024-01-02",
    end="2024-01-03",
)
df = data.to_df()
puts = df[df["instrument_class"] == "P"]  # verify column name from schema
print(len(df), len(puts))
```

### 6.4 Reference pull — EOD NBBO (1 week smoke test)

```python
data = client.timeseries.get_range(
    dataset="OPRA.PILLAR",
    schema="cbbo-1m",
    stype_in="parent",
    symbols=["SPY.OPT"],
    start="2024-01-02T09:30:00-05:00",
    end="2024-01-05T16:00:00-05:00",
)
df = data.to_df()
# Downstream: filter puts, compute DTE/moneyness, keep 15:59 ET rows only
```

### 6.5 Batch job pattern (production)

```python
# Pseudocode — one calendar month per job to bound failure/retry
for month in month_range("2022-01", "2024-12"):
    for schema in ["definition", "statistics", "cbbo-1m"]:
        cost = client.metadata.get_cost(
            dataset="OPRA.PILLAR",
            schema=schema,
            stype_in="parent",
            symbols=["SPY.OPT"],
            start=month.start,
            end=month.end,
        )
        if cost > MONTHLY_BUDGET: 
            log_skip(schema, month)
            continue
        client.timeseries.get_range(...).to_parquet(
            f"data/opra/{schema}/SPY.OPT/{month:%Y-%m}.parquet"
        )
```

---

## 7. Local storage layout

```text
Theta Decay Dynamics/
  report/
    build_report.py                 # PDF assembly (Appendix B reads data/v6/)
    output/Theta_Decay_Dynamics_v6.2.pdf
  data/
    opra/
      definition/SPY.OPT/YYYY-MM.parquet
      statistics/SPY.OPT/YYYY-MM.parquet
      cbbo-1m/SPY.OPT/YYYY-MM.parquet
    equity/
      SPY_ohlcv_1d.parquet          # optional Databento pull
    external/
      vixcls.csv                    # FRED VIX daily
      spy_daily.csv                 # if not from Databento
  scripts/
    pull_databento.py               # batch downloader
    build_chain_eod.py              # filter → daily chain panel
    backtest_managed_put.py         # Section 20 rules
    backtest_report_v6.py           # tables → PDF appendix inputs
  .env                              # gitignored
  .env.example
```

Add to `.gitignore`:
```text
.env
data/
*.parquet
```

---

## 8. Derived tables (pipeline outputs)

### 8.1 `chain_eod.parquet` (one row per option-day)

| Column | Source |
|---|---|
| `date` | ET session date |
| `symbol` | OCC raw symbol |
| `expiry` | From definition |
| `strike` | From definition |
| `spot` | SPY close |
| `dte` | calendar days to expiry |
| `moneyness_sk` | spot / strike |
| `bid`, `ask`, `mid` | cbbo-1m EOD |
| `oi`, `volume` | statistics |
| `spread_pct` | (ask-bid)/mid |

### 8.2 `trades_backtest.parquet` (one row per entry)

| Column | Description |
|---|---|
| `entry_date`, `exit_date`, `exit_reason` | `profit_50`, `dte_21`, `expiry` |
| `strike`, `entry_mid`, `exit_mid` | Marks |
| `pnl_gross`, `pnl_net`, `costs` | Per contract |
| `regime` | VIX bin (Section 8) |
| `strategy` | `managed` or `hold` |

### 8.3 v6 report outputs (feed `build_report.py` Appendix B)

| Output table | Replaces / validates |
|---|---|
| DTE × profit sweep (real) | Section 12.1 figure |
| Managed vs hold CDF by regime | Section 21 figure |
| 5th %ile / median by regime | Section 21 summary table |
| Cost-adjusted Sharpe by moneyness | Section 12.4 |

---

## 9. Acceptance criteria (Phase 1 done when…)

- [ ] ≥ 150 weekly entries after filters (2022–2024)
- [ ] Managed strategy **5th percentile** P&amp;L ≥ hold in **VIX &gt; 25** months (directional match Section 21)
- [ ] Net Sharpe &gt; 0 in **low/normal VIX** after **Section 9** costs (directional; not required to match MC magnitudes)
- [ ] Document **where real results diverge** from simulation (surface stickiness, gaps, spread widening)
- [ ] Section 7 unchanged except cross-reference: “not validated by chain backtest”

---

## 10. Phased rollout & budget guardrails

| Step | Action | Est. cost | Gate |
|---|---|---|---|
| **0** | Rotate API key; add `.env` | $0 | Must |
| **1** | 1-day smoke (`definition` + `cbbo-1m`) | &lt; $1 | Schema OK |
| **2** | 1 month MVP pull (2022‑06) | Check portal | Pipeline OK |
| **3** | Full MVP 2022–2024 | Check portal | Phase 1 metrics |
| **4** | Extend to 2016+ | Check portal | OOS appendix |
| **5** | Optional SPX + tick fills | High | Only if needed |

**Hard stop:** If projected pull &gt; **$100**, narrow to:
- `definition` + `statistics` + **`ohlcv-1d` only** (skip `cbbo-1m`; use daily close + fixed 2.2% spread assumption from Section 9)

---

## 11. Known limitations (disclose in Appendix B)

1. **American exercise / early assignment** — European BS in report; SPY options are American.
2. **Assignment on ex-div** — not modeled in Phase 1.
3. **Sticky-delta surface** — EOD marks don’t capture intraday spot-vol joint moves (Section 17).
4. **Survivorship** — use point-in-time `definition` records, not today’s chain.
5. **SPY vs SPX** — report mixes conventions; Phase 1 is SPY-only ETF options.
6. **IV rank filter** (Section 20) — needs historical IV series; derive from chain or add ORATS later.

---

## 12. Next code artifacts (after spec approval)

1. `scripts/pull_databento.py` — batch downloader with cost gate  
2. `scripts/build_chain_eod.py` — universe filter + EOD panel  
3. `scripts/backtest_managed_put.py` — Section 20 rules engine  
4. `Appendix B: Historical Validation` in `build_report.py` — only after Phase 1 metrics exist  

---

## 13. API key hygiene

- **Rotate** any key ever pasted into chat or logs.  
- Store only in `.env`; load via `os.environ`.  
- Never commit keys to git or embed in notebooks.  
- Use Databento portal to set **spend alerts** if available.

---

*Spec version: 1.0 — aligned to Theta Decay Dynamics v5.2 (May 2026)*
