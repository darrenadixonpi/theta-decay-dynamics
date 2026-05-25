# Project history

How *Theta Decay Dynamics* was built, lost, reconstructed, expanded, and partially validated on real options chains. This page is the **reading guide**; milestone PDFs and session notes live in linked paths below.

**Current release:** [`report/output/Theta_Decay_Dynamics_v6.2.pdf`](../report/output/Theta_Decay_Dynamics_v6.2.pdf)

---

## At a glance

| Era | Versions | Focus |
|-----|----------|--------|
| Original build | v2 → v4.4 | Theta-focused report from ReportLab + Monte Carlo (~16 sections) |
| Reconstruction | v4.4 rebuilt → v4.5 | Recover `build_report.py` after filesystem loss; layout/table polish |
| Greek expansion | v5.0 → v5.2 | Full volatility-trading manual (23 sections); sequential renumbering |
| Chain validation | v6.0 → v6.2 | Databento OPRA pilot; Appendix B; honest MC vs chain framing |

---

## Phase 1 — Original report (v2 → v4.4)

The report was assembled iteratively in Cursor using ReportLab (Python), with charts from matplotlib and pricing from Black–Scholes / Merton jump-diffusion. External review cycles drove structure and tone:

| Step | Highlights |
|------|------------|
| v2 → v3 | Regime analysis, transaction costs, trade rules, literature grounding |
| v3 → v3.5 | Production charts, distribution-level risk, sensitivity grids, scenarios |
| v3.5 → v4.0 | Section restructuring; Section 7 empirical signals standalone; clickable TOC |
| v4.0 → v4.2 | Greek framework (P&amp;L decomposition, path dependency, unified interpretation) |
| v4.2 → v4.3 | Causal language pass (mechanical “driven by” vs descriptive) |
| v4.3 → v4.4 | Layout/pagination (orphans, spacing) |

By **v4.4** the document had **16 sections + Appendix + References** (~49 pages): analytical theta/Greek content, Monte Carlo regime and scenario work, Section 7 surface signals from `signal_summary.json`, and operational rules in Section 13.

**Checkpoint artifact:** [`archive/old_pdfs/Theta_Decay_Dynamics_v4.4.pdf`](../archive/old_pdfs/Theta_Decay_Dynamics_v4.4.pdf)

**Deep detail:** [`Theta_Report_Handoff.md`](Theta_Report_Handoff.md) — section-by-section inventory, simulation parameters, citations, review scores, and remaining-work list as of v4.4.

---

## Phase 2 — Filesystem loss and reconstruction (May 2026)

The main PDF assembly script (`build_report.py`, ~1,500 lines) was built through many incremental edits and **was not saved as a single file** before a workspace reset. Recoverable assets remained:

- v4.4 PDF (reference text)
- `options_math.py`, `generate_all_charts.py`, chart PNGs
- Handoff, feedback, and context markdown
- `signal_summary.json` (Section 7)

**Reconstruction approach:**

1. Extract v4.4 PDF text page-by-page (`archive/scratch/` tools — local only)
2. Use the handoff spec as blueprint
3. Rebuild ReportLab assembly (styles, `BookmarkedDocTemplate`, tables, figures)
4. Validate against original outline and chart inventory

First successful rebuild: **`Theta_Decay_Dynamics_v4.4_rebuilt.pdf`** (local intermediate; not in git).

---

## Phase 3 — v4.5 layout and table polish

[`Theta_Report_Feedback.md`](Theta_Report_Feedback.md) drove a surgical pass on table bleedover, orphan headers, and TOC page numbers (two-pass build for dotted leaders).

| Change | Outcome |
|--------|---------|
| Section openings bound to first figure/table | No orphaned “5. Multi-Leg Strategies” headers |
| Global table font/wrap tuning | Shorter cells in §2.1, §6, §7, §8, §10, §13 |
| Decision matrix heatmap | Adaptive text contrast on dark cells → triggered v5.0 |

**Artifact:** [`archive/old_pdfs/Theta_Decay_Dynamics_v4.5.pdf`](../archive/old_pdfs/Theta_Decay_Dynamics_v4.5.pdf)

---

## Phase 4 — v5.0 expansion (theta report → Greek manual)

The handoff “long-term” blueprint called for second-order Greeks, variance framework, hedging, surface dynamics, model risk, and execution microstructure. **v5.0** added sections **17–23** (before later renumbering):

| New block | Topics |
|-----------|--------|
| 17–18 | Second-order Greeks; realized vs implied variance |
| 19–20 | Dynamic Greek evolution; hedging framework |
| 21–23 | Surface stickiness; BS/Merton/Kou/Heston model risk; execution microstructure |

Supporting work: new functions in `options_math.py`, additional charts (`fig_v5_greeks`, surface, model risk, execution), expanded references.

**Artifact:** [`archive/old_pdfs/Theta_Decay_Dynamics_v5.0.pdf`](../archive/old_pdfs/Theta_Decay_Dynamics_v5.0.pdf)

---

## Phase 5 — v5.1–v5.2 restructure and production polish

Reading order was reorganized so **foundations (1–12) → Greek system (13–19) → operations (20) → stress (21) → reference (22) → synthesis (23)**. Section numbers were renumbered sequentially (no more 1–12 then 17–23 then 13–16 in the TOC).

| Version | Work |
|---------|------|
| **v5.1** | Reorder + renumber; Section 20 = decision rules; §14 → “Master Reference” |
| **v5.2** | `P&L` rendering fix; stale cross-refs; figure bleedover; `audit_report.py` |

**Artifacts:** [`v5.1`](../archive/old_pdfs/Theta_Decay_Dynamics_v5.1.pdf), [`v5.2`](../archive/old_pdfs/Theta_Decay_Dynamics_v5.2.pdf)

At v5.2 the **simulated** report was treated as complete; empirical chain validation was explicitly deferred.

---

## Phase 6 — v6.x chain validation (Databento)

**Goal:** Test Section 20 management rules (45 DTE entry, 50% profit take, 21 DTE floor) on **real SPY OPRA chains**, without turning Section 7 into a trading strategy.

| Version | Change |
|---------|--------|
| **v6.0** | Appendix B scaffold; Databento pipeline spec; pilot framing |
| **v6.1** | Evidence Map; bootstrap CIs; honest “MC vs pilot” language in §12/§21 |
| **v6.2** | n = 32 weekly entries (8 OPRA months pulled); dynamic pilot counts in PDF |

**Pipeline:** [`scripts/README.md`](../scripts/README.md), [`Databento_v6_Spec.md`](Databento_v6_Spec.md)

**Pilot result (v6.2, local `data/v6/v6_summary.json`):**

- 32 entries, 64 trades (managed/hold pairs), Mar 2020 – Mar 2023 sample
- Median net P&amp;L: hold ~$94, managed ~$95; identical 5th %ile (~−$76)
- Paired managed−hold median **−$0.50** (95% CI includes zero) → **inconclusive**
- Section 21 MC claim that “management cuts tail losses” **not replicated** in pilot

**Artifacts:** [`v6.0`](../archive/old_pdfs/Theta_Decay_Dynamics_v6.0.pdf), [`v6.1`](../archive/old_pdfs/Theta_Decay_Dynamics_v6.1.pdf), current [`v6.2`](../report/output/Theta_Decay_Dynamics_v6.2.pdf)

---

## Pre-repo legacy bundle (May 2025)

Before the current `scripts/` pipeline, early experiments lived in a separate folder archived as:

**[`archive/legacy/Theta_Decay_Report_legacy.7z`](../archive/legacy/Theta_Decay_Report_legacy.7z)** (~18 MB)

Contents (extract locally with 7-Zip):

| Path in archive | Description |
|-----------------|-------------|
| `databento_pull.py`, `build_surface_dataset.py` | First Databento/surface scripts |
| `initial_run/` | Daily SPY options CSVs (Mar 2021, Apr–Jun 2022 samples) |
| `second_round_bigger_time_window/`, `splitting/` | Follow-on data experiments |

This predates OPRA parquet pulls and the v6 backtest engine; it documents **first contact** with chain data, not the current validation stack.

---

## Milestone PDF index

All milestone PDFs under [`archive/old_pdfs/`](../archive/old_pdfs/) unless noted.

| PDF | Pages (approx.) | Role |
|-----|-----------------|------|
| v4.4 | 49 | Last pre-loss “canonical” simulated report |
| v4.5 | 36 | Layout/table polish complete |
| v5.0 | 50 | Greek expansion added |
| v5.1 | 51 | Reordered narrative flow |
| v5.2 | 50 | Production polish; last MC-only release |
| v6.0 | — | Appendix B + pipeline introduced |
| v6.1 | — | Evidence Map + bootstrap framing |
| **v6.2** | — | **Current** — pilot n = 32 |

Intermediate builds (`*_draft`, `*_build`, `*_layout`, `*_rebuilt`) are kept locally only — see [`archive/README.md`](../archive/README.md).

---

## Where to read more

| Question | Document |
|----------|----------|
| What does each v4.4 section contain? | [`Theta_Report_Handoff.md`](Theta_Report_Handoff.md) |
| What layout bugs drove v4.5? | [`Theta_Report_Feedback.md`](Theta_Report_Feedback.md) |
| Section 7 scope constraints | [`Theta_Report_Context.md`](Theta_Report_Context.md) |
| OPRA schemas, costs, acceptance criteria | [`Databento_v6_Spec.md`](Databento_v6_Spec.md) |
| How to rebuild the PDF | [`report/README.md`](../report/README.md) |
| How to run the validation pipeline | [`scripts/README.md`](../scripts/README.md) |

---

## Still open (as of v6.2)

- ≥150 weekly entries in a contiguous 12-month block for statistical power
- Cross-month position carry; replace selected MC figures with chain-derived panels
- Section 7 signals remain **interpretation-only** — not chain-validated
- Public license TBD

These appear in the report’s **Future Work** section and in [`Databento_v6_Spec.md`](Databento_v6_Spec.md).
