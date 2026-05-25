# Report build pipeline

How to regenerate the PDF from source. Run all commands from the **repository root**.

## Prerequisites

```bash
pip install -r requirements.txt
```

## Steps

```bash
# 1. Charts → report/charts/*.png
python report/generate_all_charts.py

# 2. PDF → report/output/Theta_Decay_Dynamics_v6.2.pdf
python report/build_report.py

# 3. Audit (optional)
python report/audit_report.py
```

## Files

| Path | Role |
|------|------|
| `build_report.py` | Main PDF assembly (ReportLab) |
| `generate_all_charts.py` | Chart PNG generator |
| `options_math.py` | BS/Merton pricing, Greeks |
| `audit_report.py` | Page/glyph/text checks |
| `signal_summary.json` | Section 7 surface signal data |
| `charts/` | Generated figure assets |
| `output/` | Built PDF (only v6.2 tracked in git) |

## Appendix B (chain validation)

See [`docs/Databento_v6_Spec.md`](../docs/Databento_v6_Spec.md) and [`scripts/README.md`](../scripts/README.md).
