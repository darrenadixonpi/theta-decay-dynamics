# Mathematical statistician passover (v6.2)

Assessment of *Theta Decay Dynamics* from a **mathematical statistics** perspective: notation, formal definitions, estimator transparency, and whether additional rigor is warranted.

---

## Executive summary

| Question | Answer |
|----------|--------|
| **Is more rigor needed?** | **Moderate additions only** — not a measure-theoretic rewrite. |
| **What was missing?** | Explicit ∂/ν/Π conventions, d₁/d₂ block, MC vs bootstrap estimators, §7 inferential status. |
| **What was fixed in v6.2 pass?** | §2 expanded; Appendix A.5 estimators; notation harmonized; §7 statistical disclaimer; **Appendix C derivations**. |
| **What remains deferred?** | Formal proofs, stochastic-vol PDE, hypothesis tests on pilot, multiple-comparison control on sweeps. |

The report is a **mechanistic + simulation** document. Appropriate rigor = clear notation, honest estimators, and explicit non-inferential labels — not full theorem–proof style.

---

## Rigor assessment by block

### Tier 1 — Adequate (no major additions)

| Block | Status |
|-------|--------|
| BS theta / T* peak | Correct standard results; Emery et al. citation; T* now written as (ln(S/K))²/σ² |
| P&amp;L decomposition | Itô-Taylor expansion; ∂V notation; ν = ∂V/∂σ defined |
| Second-order Greeks | ∂²V/∂σ², cross-partials aligned with §2 |
| Gamma–variance identity | Discrete Σ ½Γ S²(σ²_real − σ²_impl)Δt; MC illustration tagged |
| Merton series | Standard Poisson mixture of BS prices |

### Tier 2 — Improved in this pass

| Block | Change |
|-------|--------|
| **§2 Notation** | Added τ vs T, Π (seller P&amp;L), ν, CVaR, sign convention for short θ carry |
| **§2.2 Primitives** | Explicit d₁, d₂ and ∂V/∂· definitions |
| **§2.4–2.5** | MC sample mean; loss-cluster indicator formalized |
| **§7 Signals** | Explicit “hypothesis-generating”; n = 3 / unbalanced cells |
| **Appendix A.5** | Sharpe, bootstrap B, percentile CI method, no FDR on grid |

### Tier 3 — Deferred (high cost, low marginal value for audience)

| Item | Why defer |
|------|-----------|
| (Ω, ℱ, ℚ) measure space setup | Practitioner report; BS PDE assumed familiar |
| Full T* proof with r ≠ 0 | Numerical bound suffices; Emery reference |
| Heston / Dupire PDEs | Interpretive §17–18 only |
| Girsanov / risk-neutral derivation | Out of scope |
| Formal hypothesis tests on pilot | n = 32 insufficient; bootstrap CIs already reported |
| FDR on §12.1 heatmap | Exploratory sensitivity; label retained in A.5 |

---

## Notation checklist (LaTeX-aligned)

Conventions now documented in **§2.1–2.2**:

| LaTeX-style | Report usage |
|-------------|--------------|
| `S_t`, `K`, `T`, `\tau` | Spot, strike, time to expiry |
| `\sigma`, `r` | Annualized vol, rate (decimal) |
| `\partial V/\partial T`, `\theta` | Calendar theta |
| `\nu = \partial V/\partial\sigma` | Vega (tables may show ν·dσ) |
| `\Delta`, `\Gamma` | First-order Greeks |
| `\Pi = V_{\text{entry}} - V_{\text{exit}}` | Short P&amp;L |
| `d_1, d_2` | BS indices (formula box) |
| `T^* \approx (\ln(S/K))^2/\sigma^2` | OTM peak (r ≈ 0) |
| `X \sim \mathcal{N}(\mu_j, \sigma_j^2)` | Jump size (written ln(1+J) ∼ N(·)) |
| `\mathrm{CVaR}_\alpha`, `q_\alpha` | Tail risk |
| `(1/N)\sum_i f(X_i)` | MC expectation estimate |

**ReportLab note:** PDF uses Unicode Greek and `<super>` tags, not native LaTeX rendering. Notation is chosen to match what a LaTeX reader expects when transliterated.

---

## Estimator transparency

| Output | Defined in |
|--------|------------|
| MC path means / quantiles | §2.4; Appendix A.3 path counts |
| Sharpe (simulated) | Appendix A.5: √252 · μ/σ on stated period |
| 80% bootstrap CI (DTE curve) | A.5; B = 100 |
| 95% bootstrap CI (pilot) | Appendix B; B = 10,000 |
| Exploratory grid (§12.1) | A.5: no multiplicity correction |

---

## Recommendations if rigor is increased later

1. ~~**Appendix C (optional):** One-page T* derivation sketch under r = 0 with explicit ∂θ/∂T.~~ **Added (Appendix C.1–C.3).**
2. **Pilot phase 2:** Pre-register primary endpoint (paired median difference) before expanding n.
3. **§12.1:** Add false-discovery note in figure footnote (already in A.5 table).
4. **Do not add:** Full stochastic-calculus appendix unless the document is repositioned as a graduate text.

---

## Verdict

**Additional rigor incorporated:** targeted notation and estimator formalization — not a structural rewrite.

The mathematical portions are now **adequately legible** to a statistician reviewing notation and simulation methodology. Remaining gaps are **inferential power** (small n) and **exploratory MC grids**, which are correctly labeled as non-confirmatory rather than notation failures.
