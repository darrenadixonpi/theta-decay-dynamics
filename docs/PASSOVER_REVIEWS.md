# Report passover reviews (v6.2)

External-style reviews of *Theta Decay Dynamics v6.2* after TOC restructuring. These are editorial assessments, not formal peer review.

---

## Passover A — Academic statistician

**Reviewer stance:** Quantitative methods, inferential validity, reproducibility, and honest uncertainty quantification.

### Strengths

1. **Evidence Map (§1)** — Explicit claim → evidence → confidence labeling is best practice. Most practitioner documents never separate [Derived], [Calibrated], and [Convention]. This reduces over-interpretation.

2. **Section 7 discipline** — The report states n = 3 active observations for vol/skew spikes and refuses inferential language. That is statistically correct and rare in sell-side style work.

3. **Appendix B honesty** — Pilot results report bootstrap 95% CIs, paired managed−hold comparisons, and explicitly **fail to replicate** the Section 21 MC tail-benefit claim. Pre-specification of Section 20 rules before the pilot is noted. This is the right epistemic posture for n = 32.

4. **Simulation assumptions table (§2.4)** — Documents optimistic bias sources (constant IV, no margin, no spread widening in MC core). Appendix A states path counts and VRP embedding.

5. **Regime stratification** — VIX bins in §8 and pilot breakdown (Appendix B) are sensible; small cell counts are acknowledged.

### Concerns (ordered by severity)

| Issue | Location | Comment |
|-------|----------|---------|
| **Underpowered inference everywhere that matters** | §7, Appendix B | n = 3 signals; n = 32 chain entries. CIs include zero on key contrasts. Report correctly says "not inferential" but §12 MC Sharpe tables still read like rankings. |
| **Monte Carlo ≠ empirical validation** | §12, §21 | 300–1,500 paths with fixed IV/VRP are sensitivity illustrations, not estimates of live P&amp;L. The "(Simulated)" framing in body text is good; figure captions could repeat it more consistently. |
| **Multiple comparisons unchecked** | §12.1 sweep | DTE × profit-target grid implies many implicit tests. No FDR or holdout. Acceptable for exploratory sensitivity if labeled as such — currently borderline. |
| **Non-contiguous pilot sample** | Appendix B | Month-end forced exits (`last_mark`) inject noise unrelated to management rules. Confounds managed vs hold and tail quantiles. Well disclosed; still limits any causal reading. |
| **Sharpe on weekly entries** | Appendix B | Serial correlation across overlapping SPY exposure not modeled. Annualized Sharpe from 32 weeks is unstable (report notes this). |
| **American vs European** | Appendix B | SPY puts American; European EOD marks bias is directionally understood but not quantified. |
| **Missing IV Rank filter in pilot** | Appendix B | Section 20 entry rule partially not implemented. Backtest tests a subset of stated rules. |

### Statistical verdict

**As a mechanistic + stress-test document:** Strong structure, unusually honest about limits.

**As an empirical validation of trading rules:** **Not yet.** Appendix B is a feasibility pilot, not confirmation. The report's own framing (Evidence Map, Future Work, §21 divergence paragraph) matches this assessment.

### Recommendations

1. Keep MC figures but add a one-line "illustrative simulation" tag in every §12/§21 figure caption.
2. When pilot reaches n ≥ 150 contiguous weeks, pre-register primary endpoints: paired managed−hold median, 5th %ile difference, regime interaction (with minimum cell size rule).
3. Section 7: consider moving raw signal tables to an appendix so the main narrative cannot be skimmed as "predictive."

---

## Passover B — Professional options trader

**Reviewer stance:** Monday-morning utility for a short-premium book — entry/exit, risk, costs, regime behavior. Not looking for academic novelty; looking for **actionable filters and kill criteria**.

### What I would actually use

| Section | Utility | Notes |
|---------|---------|-------|
| **§3 T* peak / §20.3 Decision Matrix** | **High** | Directly informs "am I selling too early/late for this moneyness and IV?" Heatmap + T* formula = concrete DTE guidance. |
| **§20 Entry/Exit rules + §20.5 Failure modes** | **High** | 45/50/21 framework with explicit "Fails When" column is desk-ready. Failure mode table is the most tradable page in the doc. |
| **§8 Regime + §20.4 Sizing** | **High** | VIX bins → size caps is implementable TOM without a model build. |
| **§9 Costs + §19 Microstructure** | **Medium–High** | Muravyev spread tier + OTM widening reminder — use before sizing far OTM in stress. |
| **§1 Evidence Map** | **High (meta)** | Tells me what **not** to bet the farm on. Especially "management cuts tail" = MC only. |
| **§10 Risk metrics / boxplots** | **Medium** | Good for intuition on strangle vs CSP tail; numbers are simulated — use for shape, not levels. |
| **§13–18 Greek depth** | **Medium (selective)** | Vanna/vomma/charm sections useful during vol events; skim unless running a vol book. |
| **§7 Surface signals** | **Low (trading)** | Correctly labeled non-inferential. Would not signal-trade on n = 3. Fine as research direction. |
| **Appendix B** | **Medium (risk kill)** | "Pilot inconclusive" = **keep running current rules but don't claim edge from management.** 5th %ile identical managed/hold is the headline for a PM. |

### Trader pain points (friction in the doc)

1. **Length vs path** — 50 pages is fine for a manual, but the TOC was a flat 1–23 list with no story arc. **Grouped TOC (Parts I–VI)** fixes navigation: Foundations → Rules (§20) → Appendix B.

2. **§12 vs Appendix B tension** — MC says managed cuts ROI; pilot says no tail benefit. A trader needs the **Evidence Map** on page 3. Consider bold callout box in §20: *"Management: convention supported by MC; not confirmed on chain pilot."*

3. **Convention stacking** — tastylive 45/50/21 + IV Rank + T* + regime sizing = many rules. §20.5 failure table helps, but there's no single **priority stack** when rules conflict (e.g., 50% profit vs 21 DTE vs T*).

4. **Multi-leg vs single-leg** — §5 compares structures; §20 focuses on short put. A trader running iron condors needs explicit mapping ("these §20 rules apply to short put leg only").

5. **Execution gap** — §19 describes widening; pilot uses half-spread EOD. Real fills during Mar 2020 would be worse. Trader should mentally haircut crisis P&amp;L further than table shows.

### Utility verdict

**Worth keeping on the desk?** **Yes**, as a **theta/Greek reference + rule checklist**, not as proof that 50% management works.

**Highest-value reading path (≈45 min):** §1 Evidence Map → §3 (T*) → §8 → §9 → §20 → Appendix B → §22 reference table.

**Lowest-value for daily trading:** §2 full notation, §11 Merton unless trading event names, §7 unless doing vol-surface research.

### Recommendations

1. Add a one-page **"Desk Quick Reference"** (optional future): rule stack, regime size table, decision matrix thumbnail, Evidence Map condensed.
2. In §21, lead with pilot divergence before MC CDFs — traders read bottom-up from P&amp;L impact.
3. Keep Appendix B updated in PDF when n increases; that's the only section that will change a live process.

---

## Summary

| Lens | Overall | Main gap |
|------|---------|----------|
| Statistician | Strong methodology *disclosure*; weak inferential power | Need ≥150 contiguous entries; MC labeled exploratory throughout |
| Trader | High utility in §3, §8–9, §20; Greek block optional depth | Management edge unproven; need clearer rule priority when conflicts arise |

Both reviewers agree: **v6.2 is credible because it does not oversell the pilot.** The grouped TOC and reading-path line make the document easier to navigate for both audiences.
