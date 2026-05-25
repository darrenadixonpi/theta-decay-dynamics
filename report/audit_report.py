#!/usr/bin/env python3
"""Quick audit of build_report.py and generated PDF."""
from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

REPORT_DIR = Path(__file__).resolve().parent
BUILD = REPORT_DIR / "build_report.py"
CHARTS = REPORT_DIR / "charts"
PDF = REPORT_DIR / "output" / "Theta_Decay_Dynamics_v6.2.pdf"

issues: list[str] = []


def audit_charts():
    text = BUILD.read_text(encoding="utf-8")
    refs = set(re.findall(r'"(fig_[a-z0-9_]+)"', text))
    missing = [r for r in sorted(refs) if not (CHARTS / f"{r}.png").exists()]
    if missing:
        issues.append(f"Missing chart PNGs: {', '.join(missing)}")


def audit_stale_ranges():
    text = BUILD.read_text(encoding="utf-8")
    stale = [
        "Sections 17&ndash;23",
        "Sections 17–23",
        "Section 13 decision",
        'sec17", "17. Second-Order',
    ]
    for s in stale:
        if s in text:
            issues.append(f"Possible stale text: {s!r}")


def audit_pdf():
    if not PDF.exists():
        issues.append(f"PDF missing: {PDF}")
        return
    reader = PdfReader(str(PDF))
    full = "\n".join((p.extract_text() or "") for p in reader.pages)
    if "&amp;" in full or "&lt;" in full:
        issues.append("Raw HTML entities found in PDF text extraction")
    if "P&L;" in full:
        issues.append("Broken P&L entity (P&L;) in PDF")
    toc = reader.pages[1].extract_text() or ""
    nums = [int(m.group(1)) for m in re.finditer(r"^(\d+)\.", toc, re.M)]
    if nums and nums != list(range(1, max(nums) + 1)):
        issues.append(f"TOC section numbering not sequential: {nums}")


def main():
    audit_charts()
    audit_stale_ranges()
    audit_pdf()
    if issues:
        print("AUDIT ISSUES:")
        for i in issues:
            print(f"  - {i}")
    else:
        print("Pre-build audit: no issues in source checks")


if __name__ == "__main__":
    main()
