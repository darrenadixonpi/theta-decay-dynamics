#!/usr/bin/env python3
"""Build Theta Decay Dynamics PDF (v6.1)."""
from __future__ import annotations

import io
import json
import re
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import CondPageBreak, Flowable
from PIL import Image as PILImage

REPORT_DIR = Path(__file__).resolve().parent
REPO_ROOT = REPORT_DIR.parent
CHARTS = REPORT_DIR / "charts"
OUT_PDF = REPORT_DIR / "output" / "Theta_Decay_Dynamics_v6.2.pdf"
SIGNALS = json.loads((REPORT_DIR / "signal_summary.json").read_text(encoding="utf-8"))
V6_SUMMARY_PATH = REPO_ROOT / "data" / "v6" / "v6_summary.json"


def load_v6_summary() -> dict | None:
    if V6_SUMMARY_PATH.is_file():
        return json.loads(V6_SUMMARY_PATH.read_text(encoding="utf-8"))
    return None


def _usd(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"${x:,.0f}"


def _pct100(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{100 * x:.1f}%"


def _sharpe(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{x:.1f}"


def _pilot_n() -> int:
    v6 = load_v6_summary()
    return int(v6["n_entries"]) if v6 and v6.get("n_entries") else 0


def _ci_band(ci: dict | None) -> str:
    if not ci or ci.get("lo") is None or ci.get("hi") is None:
        return ""
    return f" (95% CI: {_usd(ci['lo'])} to {_usd(ci['hi'])})"

# Style constants
HEADER_BG = colors.HexColor("#1E293B")
ROW_BG = colors.HexColor("#F8FAFC")
ROW_ALT = colors.HexColor("#F1F5F9")
GRID_CLR = colors.HexColor("#E2E8F0")
BLUE = colors.HexColor("#2563EB")
DARK = colors.HexColor("#1F2937")
MID = colors.HexColor("#6B7280")
PAGE_W, PAGE_H = letter
MARGIN_LR = 0.85 * inch
MARGIN_TB = 0.75 * inch
CONTENT_W = PAGE_W - 2 * MARGIN_LR
PAGE_CONTENT_H = PAGE_H - 2 * MARGIN_TB
BLOCK_SAFETY = 0.18 * inch  # pad height estimates so KeepTogether blocks don't split
DEFAULT_FIG_WIDTH = 0.62
DEFAULT_FIG_MAX_H = 0.26  # ~2.5 in — standard single-panel charts

# Manual overrides only when aspect-ratio tiers are insufficient.
CHART_LAYOUT_OVERRIDES: dict[str, tuple[float, float]] = {
    "fig_surface_sticky": (1.0, 0.24),
}

_aspect_cache: dict[str, float] = {}


def _chart_aspect(name: str) -> float:
    if name not in _aspect_cache:
        path = CHARTS / f"{name}.png"
        with PILImage.open(path) as im:
            _aspect_cache[name] = im.width / im.height
    return _aspect_cache[name]


def _chart_layout(name: str) -> tuple[float, float]:
    """Size charts from PNG aspect ratio — wide multi-panel figures need more width."""
    if name in CHART_LAYOUT_OVERRIDES:
        return CHART_LAYOUT_OVERRIDES[name]
    ar = _chart_aspect(name)
    if ar >= 2.4:
        # 3-across small multiples — use full content width so panels stay legible
        return (1.0, 0.32)
    if ar >= 1.7:
        # 2-across comparisons (skew, merton, sens grid, IV shock)
        return (0.84, 0.32)
    if ar >= 1.32:
        # Moderately wide (2×2 grids, sweep, boxplots, risk equity)
        return (0.72, 0.30)
    if ar < 0.95:
        # Tall stacked panels (trade lifecycle)
        return (0.56, 0.36)
    return (DEFAULT_FIG_WIDTH, DEFAULT_FIG_MAX_H)


def _img_dims(name: str, width_frac: float, max_height_frac: float) -> tuple[float, float]:
    path = CHARTS / f"{name}.png"
    with PILImage.open(path) as im:
        w_px, h_px = im.size
    width = CONTENT_W * width_frac
    height = width * (h_px / w_px)
    max_h = PAGE_CONTENT_H * max_height_frac
    if height > max_h:
        height = max_h
        width = height * (w_px / h_px)
    return width, height


class BookmarkFlowable(Flowable):
    """Paragraph wrapper that registers PDF outline bookmarks."""

    def __init__(self, para: Paragraph, key: str, title: str, level: int = 0):
        super().__init__()
        self.para = para
        self.key = key
        self.title = title
        self.level = level
        self.width = CONTENT_W
        self.height = 0

    def wrap(self, availW, availH):
        w, h = self.para.wrap(availW, availH)
        self.width, self.height = w, h
        return w, h

    def draw(self):
        canv = self.canv
        canv.bookmarkPage(self.key)
        canv.addOutlineEntry(self.title, self.key, level=self.level, closed=False)
        self.para.drawOn(canv, 0, 0)


class BookmarkedDocTemplate(SimpleDocTemplate):
    """Tracks bookmark page numbers for a two-pass table of contents."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_map: dict[str, int] = {}

    def afterFlowable(self, flowable):
        if isinstance(flowable, BookmarkFlowable):
            self.page_map[flowable.key] = self.page


def build_styles():
    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=DARK,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=MID,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "Section": ParagraphStyle(
            "Section",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=DARK,
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "Subsection": ParagraphStyle(
            "Subsection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=DARK,
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "SubsectionBlock": ParagraphStyle(
            "SubsectionBlock",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=DARK,
            spaceBefore=0,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=DARK,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "BodyCenter": ParagraphStyle(
            "BodyCenter",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=MID,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "Caption": ParagraphStyle(
            "Caption",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=MID,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "Formula": ParagraphStyle(
            "Formula",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=DARK,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=DARK,
            leftIndent=14,
            bulletIndent=4,
            spaceAfter=3,
        ),
        "TOC": ParagraphStyle(
            "TOC",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=DARK,
            spaceAfter=0,
        ),
        "TOCEntry": ParagraphStyle(
            "TOCEntry",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=DARK,
            tabStops=[(CONTENT_W, TA_RIGHT, ".")],
        ),
        "Ref": ParagraphStyle(
            "Ref",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=DARK,
            spaceAfter=4,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=DARK,
            wordWrap="LTR",
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white,
            wordWrap="LTR",
        ),
        "TableFoot": ParagraphStyle(
            "TableFoot",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=MID,
        ),
    }
    return styles


ST = build_styles()

# HTML entities → Unicode / reportlab markup (Helvetica supports Greek).
_MATH_ENTITIES = {
    "&sigma;": "σ", "&theta;": "θ", "&Delta;": "Δ", "&Gamma;": "Γ",
    "&lambda;": "λ", "&mu;": "μ", "&phi;": "φ", "&rho;": "ρ", "&alpha;": "α",
    "&part;": "∂", "&middot;": "·", "&ndash;": "–", "&mdash;": "—",
    "&asymp;": "≈", "&radic;": "√", "&frac12;": "½", "&minus;": "−",
    "&le;": "≤", "&ge;": "≥", "&times;": "×", "&rarr;": "→", "&prop;": "∝",
    "&bull;": "•", "&rsquo;": "’", "&ldquo;": "“", "&rdquo;": "”",
    "&sup2;": "<super>2</super>", "&sup3;": "<super>3</super>",
}


def normalize_markup(text: str) -> str:
    """Convert HTML entities to reportlab-safe Unicode / markup tags."""
    t = str(text)
    for ent, repl in _MATH_ENTITIES.items():
        t = t.replace(ent, repl)
    # Keep &amp; for ReportLab (P&amp;L, &lt;, etc.); stripping it breaks P&L rendering.
    return t


def P(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(normalize_markup(text), ST[style])


def section(
    story,
    key: str,
    title: str,
    level: int = 0,
    lead: str | None = None,
    opening: tuple[list, float] | None = None,
    new_page: bool = True,
):
    """Section heading; each main section starts on a fresh page by default."""
    if new_page:
        story.append(PageBreak())
    plain = normalize_markup(title)
    para = P(f'<a name="{key}"/>{title}', "Section")
    bookmark = BookmarkFlowable(para, key, plain, level)
    block: list = [bookmark]
    if lead:
        block.append(P(lead))
    opening_needed = 0.0
    if opening is not None:
        opening_flowables, opening_needed = opening
        block.extend(opening_flowables)

    needed = 0.55 * inch
    if lead:
        needed += max(0.35 * inch, (len(lead) / 90) * 0.13 * inch)
    needed += opening_needed

    append_unbreakable(story, block, needed)


def subsection(story, title: str, opening: tuple[list, float] | None = None):
    """Subsection heading; optional opening content (table, figure, lead text) stays on same page."""
    block: list = [P(title, "Subsection")]
    needed = 0.42 * inch
    if opening is not None:
        opening_flowables, opening_needed = opening
        block.extend(opening_flowables)
        needed += opening_needed
    append_unbreakable(story, block, needed)


def subsection_lead(story, title: str, *paragraphs: str):
    """Keep subsection heading with its opening paragraph(s)."""
    block: list = [P(title, "Subsection")]
    for text in paragraphs:
        block.append(P(text))
    append_unbreakable(story, block, _estimate_para_block_height(len(paragraphs) + 1))


def _img_height(name: str, width_frac: float, max_height_frac: float) -> float:
    return _img_dims(name, width_frac, max_height_frac)[1]


def _estimate_para_block_height(n_paras: int, chars: int = 0) -> float:
    return (0.28 + 0.14 * n_paras + (chars / 90) * 0.12) * inch


def ensure_space(story, needed: float):
    """Page-break early if less than `needed` points remain (avoids widowed headings)."""
    story.append(CondPageBreak(needed))


def append_unbreakable(story, block: list, needed: float):
    """Keep a block on one page; break early using a padded height estimate."""
    needed = min(needed + BLOCK_SAFETY, PAGE_CONTENT_H - 0.12 * inch)
    ensure_space(story, needed)
    story.append(KeepTogether(block))


def _fig_flowables(
    name: str,
    caption_text: str,
    width_frac: float | None = None,
    title: str | None = None,
    max_height_frac: float | None = None,
    lead: str | None = None,
) -> tuple[list, float]:
    w_frac, h_frac = _chart_layout(name)
    if width_frac is not None:
        w_frac = width_frac
    if max_height_frac is not None:
        h_frac = max_height_frac

    img_h = _img_height(name, w_frac, h_frac)
    needed = img_h + 0.45 * inch
    if title:
        needed += 0.30 * inch
    if lead:
        needed += max(0.35 * inch, (len(lead) / 90) * 0.13 * inch)

    block: list = []
    if title:
        block.append(P(title, "SubsectionBlock"))
    if lead:
        block.append(P(lead))
    width, height = _img_dims(name, w_frac, h_frac)
    image = Image(str(CHARTS / f"{name}.png"), width=width, height=height)
    img_table = Table([[image]], colWidths=[CONTENT_W])
    img_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    block.extend(
        [
            Spacer(1, 3),
            img_table,
            P(f"<i>{caption_text}</i>", "Caption"),
            Spacer(1, 3),
        ]
    )
    return block, needed


def fig_block(
    story,
    name: str,
    caption_text: str,
    width_frac: float | None = None,
    title: str | None = None,
    max_height_frac: float | None = None,
    lead: str | None = None,
):
    """Atomic figure unit: optional heading + lead + image + caption stay on one page."""
    block, needed = _fig_flowables(name, caption_text, width_frac, title, max_height_frac, lead)
    append_unbreakable(story, block, needed)


def caption(story, text: str):
    story.append(P(f"<i>{text}</i>", "Caption"))


def source(story, text: str):
    label = text if text.startswith("[") else f"[{text}"
    if not label.endswith("]"):
        label = label + "]"
    story.append(P(label, "Caption"))


def formula_box(story, lines: list[str]):
    data = [[P(f"<b>{line}</b>", "Formula")] for line in lines]
    t = Table(data, colWidths=[CONTENT_W * 0.92])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.75, GRID_CLR),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(Spacer(1, 4))
    story.append(t)
    story.append(Spacer(1, 6))


def bullets(story, items: list[str]):
    for item in items:
        story.append(P(f"• {item}", "Bullet"))


def cell(text, header: bool = False, align: str = "LEFT"):
    style = "TableHeader" if header else "TableCell"
    para = Paragraph(normalize_markup(str(text)), ST[style])
    return para


def _table_flowables(
    headers: list[str],
    rows: list[list],
    col_widths: list[float] | None = None,
    footnote: str | None = None,
    heading: str | None = None,
) -> tuple[list, float]:
    block: list = []
    if heading:
        block.extend([P(heading, "SubsectionBlock"), Spacer(1, 3)])
    data = [[cell(h, header=True) for h in headers]]
    for row in rows:
        data.append([cell(str(c)) for c in row])
    if col_widths is None:
        n = len(headers)
        widths = [CONTENT_W / n] * n
    else:
        widths = [w * CONTENT_W for w in col_widths]
    t = Table(data, colWidths=widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID_CLR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(data)):
        bg = ROW_BG if i % 2 else ROW_ALT
        cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    t.setStyle(TableStyle(cmds))
    block.append(t)
    if footnote:
        block.extend([Spacer(1, 2), P(f"<i>{footnote}</i>", "TableFoot")])
    est = (0.22 + len(rows) * 0.19 + (0.2 if footnote else 0) + (0.25 if heading else 0)) * inch
    return block, est


def add_table(
    story,
    headers: list[str],
    rows: list[list],
    col_widths: list[float] | None = None,
    footnote: str | None = None,
    repeat_rows: int = 1,
    heading: str | None = None,
):
    block, est = _table_flowables(headers, rows, col_widths, footnote, heading)
    if len(rows) <= 8 or heading:
        append_unbreakable(story, block, est)
    else:
        if heading:
            ensure_space(story, est)
        for item in block:
            story.append(item)


def img(
    name: str,
    width_frac: float | None = None,
    max_height_frac: float | None = None,
) -> Image:
    path = CHARTS / f"{name}.png"
    if not path.exists():
        raise FileNotFoundError(path)
    w_frac, h_frac = _chart_layout(name)
    if width_frac is not None:
        w_frac = width_frac
    if max_height_frac is not None:
        h_frac = max_height_frac
    width, height = _img_dims(name, w_frac, h_frac)
    return Image(str(path), width=width, height=height)


def pct(x: float, digits: int = 2) -> str:
    sign = "+" if x > 0 else ""
    return f"{sign}{100 * x:.{digits}f}%"


def hit_rate(x: float) -> str:
    return f"{100 * x:.1f}%"


def add_title_page(story):
    story.append(Spacer(1, 1.4 * inch))
    story.append(P("Theta Decay Dynamics", "Title"))
    story.append(P("Moneyness, Volatility &amp; Strategy-Level Analysis", "Subtitle"))
    story.append(P("With a Merton Jump-Diffusion Extension for Event-Driven Underlyings", "Subtitle"))
    story.append(Spacer(1, 0.2 * inch))
    story.append(P("v6.2 &mdash; May 2026", "Subtitle"))
    story.append(Spacer(1, 0.35 * inch))
    story.append(
        P(
            "Mechanistic analysis &middot; Monte Carlo stress tests &middot; Pilot chain feasibility<br/>"
            "Regime framework &middot; Transaction costs &middot; Second-order Greeks<br/>"
            "Hedging &amp; surface dynamics &middot; Model risk &middot; Execution microstructure",
            "BodyCenter",
        )
    )
    story.append(PageBreak())


TOC_ENTRIES = [
    ("sec1", "1. Introduction"),
    ("sec2", "2. Mathematical Framework"),
    ("sec3", "3. Black-Scholes Theta"),
    ("sec4", "4. Single-Leg Strategies"),
    ("sec5", "5. Multi-Leg Strategies"),
    ("sec6", "6. Volatility Skew &amp; Term Structure"),
    ("sec7", "7. Preliminary Empirical Evidence"),
    ("sec8", "8. Regime Analysis"),
    ("sec9", "9. Transaction Costs"),
    ("sec10", "10. Risk Metrics &amp; Tail Analysis"),
    ("sec11", "11. Merton Jump-Diffusion Extension"),
    ("sec12", "12. Rule Sensitivity &amp; Benchmarks (Simulated)"),
    ("sec13", "13. Second-Order Greeks"),
    ("sec14", "14. Realized vs Implied Variance"),
    ("sec15", "15. Dynamic Greek Evolution"),
    ("sec16", "16. Hedging Framework"),
    ("sec17", "17. Volatility Surface Dynamics"),
    ("sec18", "18. Model Risk"),
    ("sec19", "19. Execution Microstructure"),
    ("sec20", "20. Decision Framework &amp; Trade Rules"),
    ("sec21", "21. Monte Carlo Scenario Analysis"),
    ("sec22", "22. Master Reference: Key Relationships"),
    ("sec23", "23. Unified Interpretation"),
    ("secA", "Appendix A: Methodology"),
    ("secB", "Appendix B: Historical Validation (Pilot)"),
    ("secFW", "Future Work"),
    ("secR", "References"),
]


def add_toc(story, page_map: dict[str, int] | None = None):
    story.append(P("Contents", "Section"))
    story.append(Spacer(1, 8))
    rows = []
    for key, label in TOC_ENTRIES:
        if page_map and key in page_map:
            # Literal tab char — ReportLab ignores <tab/> markup; tabStops add dot leaders.
            text = f'<link href="#{key}" color="#2563EB">{label}</link>\t{page_map[key]}'
        else:
            text = f'<link href="#{key}" color="#2563EB">{label}</link>'
        rows.append([Paragraph(normalize_markup(text), ST["TOCEntry"])])
    toc_table = Table(rows, colWidths=[CONTENT_W])
    toc_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(toc_table)
    story.append(PageBreak())


def build_section_1(story):
    section(story, "sec1", "1. Introduction", new_page=False)
    subsection(story, "Thesis")
    story.append(
        P(
            "The conventional wisdom that theta &ldquo;accelerates into expiry&rdquo; holds only for ATM options. "
            "For OTM options, theta peaks at an intermediate point and then declines, with direct implications for "
            "roll timing, exit rules, and P&amp;L projection."
        )
    )
    subsection(story, "Economic Foundation")
    story.append(
        P(
            "The variance risk premium (VRP)&mdash;the persistent gap between implied and realized volatility&mdash;"
            "provides the economic rationale for premium selling (Carr &amp; Wu, 2009; Bollerslev et al., 2009). "
            "Dew-Becker (2023) presents evidence that VRP alpha has declined as more capital enters short-vol strategies. "
            "This report optimizes how to harvest theta, not whether the premium exists."
        )
    )
    subsection(story, "Audience")
    story.append(
        P(
            "Systematic premium sellers seeking to optimize entry/exit timing and portfolio construction. "
            "Assumes familiarity with options Greeks and Black-Scholes mechanics. Not investment advice."
        )
    )
    subsection(story, "Sourcing Convention")
    story.append(
        P(
            "Every threshold is labeled: [Derived] = analytically proven from pricing model; "
            "[Calibrated] = grounded in cited empirical data; [Convention] = practitioner standard with limited formal evidence."
        )
    )
    subsection(story, "Validation Scope")
    story.append(
        P(
            "Analytic and Monte Carlo results (Sections 2&ndash;21) establish mechanism and stress behavior under "
            "model assumptions. A <b>pilot</b> historical validation on real SPY options chains (Appendix B) applies "
            "Section 20 rules to Databento OPRA marks&mdash;directional only at the current sample size. "
            "Monte Carlo remains the primary framework for Sections 12 and 21 until a full multi-year chain backtest "
            "is completed (Future Work)."
        )
    )
    subsection(story, "Evidence Map")
    story.append(
        P(
            "Use this table to separate <b>what is proven</b> from <b>what is illustrated</b>. "
            "Confidence labels match Section 22."
        )
    )
    add_table(
        story,
        ["Claim", "Primary evidence", "Confidence"],
        [
            ["T* peak theta timing (OTM vs ATM)", "BS derivation, Sections 3&ndash;4", "Robust"],
            ["Gamma&ndash;theta duality &amp; path dependence", "BS + MC paths, Sections 3, 10", "Robust / Tentative"],
            ["VRP motivates premium selling", "Cited literature, Section 1", "Tentative (declining)"],
            ["Surface signals predict 5d SPY returns", "Section 7 (n=3 activations)", "Not inferential"],
            ["45 DTE / 50% profit / 21 DTE rules", "MC sensitivity §12 + practitioner §20", "Model-contingent"],
            ["Management cuts tail loss in crisis", "Monte Carlo §21 only", "Model-contingent; not in pilot"],
            ["Section 20 rules on real SPY chains", f"Appendix B (n={_pilot_n()} entries)", "Pilot / directional"],
            ["Sticky surface amplifies crisis vega loss", "Qualitative + §17 charts", "Tentative"],
            ["OTM spread drag dominates far strikes", "§9, §19", "Tentative"],
        ],
        col_widths=[0.34, 0.40, 0.26],
        footnote="Monte Carlo = constant-vol paths with embedded VRP unless noted. Pilot = Databento OPRA EOD marks.",
    )


def build_section_2(story):
    section(story, "sec2", "2. Mathematical Framework")
    subsection(story, "2.1 Notation")
    story.append(
        P(
            "The following symbols are used throughout this report. All quantities are deterministic unless otherwise "
            "noted. Time is in years unless converted explicitly; &sigma; is annualized."
        )
    )
    add_table(story,
            ["Symbol", "Definition", "Units"],
            [
                ["S, S<sub>t</sub>", "Spot price at t", "$/share"],
                ["K", "Strike", "Currency"],
                ["T", "Time to expiry", "Years"],
                ["r", "Risk-free rate", "Ann. decimal"],
                ["&sigma;", "Implied vol (BS)", "Ann. decimal"],
                ["&sigma;<sub>d</sub>", "Diffusion vol (Merton)", "Ann. decimal"],
                ["&theta;(S,K,T,&sigma;,r)", "Theta &part;V/&part;T", "$/yr (÷365 daily)"],
                ["&Gamma;(S,K,T,&sigma;,r)", "Gamma &part;&sup2;V/&part;S&sup2;", "1/$"],
                ["&Delta;(S,K,T,&sigma;,r)", "Delta &part;V/&part;S", "Unitless"],
                ["V", "Option value", "Currency"],
                ["T*", "Time of max &theta; (OTM)", "Years"],
                ["&phi;(&middot;)", "Standard normal PDF", "—"],
                ["N(&middot;)", "Standard normal CDF", "—"],
                ["d1, d2", "BS intermediates (Sec 3.1)", "—"],
                ["&lambda;", "Jump intensity (Merton)", "Events/yr"],
                ["&mu;<sub>j</sub>", "Mean log-jump size", "Unitless"],
                ["&sigma;<sub>j</sub>", "Log-jump vol", "Unitless"],
            ],
            col_widths=[0.13, 0.52, 0.35],
    )
    subsection(story, "2.2 Underlying Price Dynamics")
    story.append(P("<b>Diffusion model (Black-Scholes).</b> The underlying follows geometric Brownian motion under the risk-neutral measure Q:"))
    formula_box(story, ["dS<sub>t</sub> = r &middot; S<sub>t</sub> &middot; dt + &sigma; &middot; S<sub>t</sub> &middot; dW<sub>t</sub>"])
    bullets(story, [
        "W<sub>t</sub> is a standard Brownian motion under Q",
        "Solution: S<sub>t</sub> = S<sub>0</sub> &middot; exp[(r &ndash; &frac12;&sigma;&sup2;)t + &sigma;W<sub>t</sub>]",
    ])
    story.append(P("<b>Jump-diffusion model (Merton, 1976).</b> For event-exposed underlyings:"))
    formula_box(story, ["dS<sub>t</sub> / S<sub>t</sub> = (r &ndash; &lambda;E[J]) dt + &sigma;<sub>d</sub> &middot; dW<sub>t</sub> + J &middot; dN<sub>t</sub>"])
    bullets(story, [
        "N<sub>t</sub> is a Poisson process with intensity &lambda; (jumps/year)",
        "ln(1 + J) ~ Normal(&mu;<sub>j</sub>, &sigma;<sub>j</sub>&sup2;)",
        "E[J] = exp(&mu;<sub>j</sub> + &frac12;&sigma;<sub>j</sub>&sup2;) &ndash; 1  (drift compensation)",
    ])
    subsection(story, "2.3 Key Definitions")
    story.append(P("<b>P&amp;L.</b> For a short option position entered at time 0 and closed at time t &le; T:"))
    formula_box(story, ["PnL(t) = V(S<sub>0</sub>, K, T, &sigma;, r) &ndash; V(S<sub>t</sub>, K, T&ndash;t, &sigma;, r)"])
    story.append(P("For hold-to-expiry: PnL = Premium &ndash; max(K &ndash; S<sub>t</sub>, 0) [put]"))
    story.append(
        P(
            "<b>Expectation and probability.</b> E[X] denotes expectation under the simulation measure. "
            "P(X &le; x) denotes the cumulative distribution. CVaR at level &alpha; = E[X | X &le; q<sub>&alpha;</sub>] "
            "where q<sub>&alpha;</sub> is the &alpha;-quantile."
        )
    )
    story.append(
        P(
            "<b>Loss clustering.</b> Given a binary loss sequence X<sub>t</sub> = 1{PnL<sub>t</sub> &lt; 0}, a loss cluster is a "
            "maximal run of consecutive 1s. Cluster length L<sub>k</sub> is the length of the k-th cluster."
        )
    )
    story.append(
        P(
            "<b>T* approximation regime.</b> The expression T* &asymp; ln&sup2;(S/K) / &sigma;&sup2; is derived by setting "
            "&part;&theta;/&part;T = 0 under the BS model with r = 0. For the OTM, short-dated focus of this report "
            "(T &lt; 0.25 years, r &le; 8%), the error is below 5% of the exact peak DTE."
        )
    )
    source(story, "Derived] Approximation bounds verified numerically across r = 0&ndash;8%, T = 0&ndash;0.5y")
    add_table(story,
            ["Assumption", "Specification", "Impact if Violated"],
            [
                ["Returns distribution", "Log-normal (BS) or log-normal + Poisson jumps (Merton)", "Heavier tails than modeled; tail metrics are optimistic"],
                ["Independence", "Returns are i.i.d. across time steps within each path", "Autocorrelation would increase clustering beyond reported levels"],
                ["Constant IV", "Implied vol fixed during trade; no stochastic vol", "IV path dependency adds P&amp;L variance not captured"],
                ["Stationarity", "Parameters constant within each regime block", "Regime transitions mid-trade are not modeled"],
                ["No friction dynamics", "Spreads and liquidity constant; no margin calls", "Stress-period widening creates additional losses not captured"],
            ],
            col_widths=[0.22, 0.38, 0.40],
            footnote="These assumptions collectively create an optimistic bias in simulated results relative to live trading.",
            heading="2.4 Simulation Assumptions",
    )


def build_section_3(story):
    section(story, "sec3", "3. Black-Scholes Theta")
    story.append(
        P(
            "BS theta decomposes into a volatility/gamma term (always negative, maximal near ATM) and a carry term "
            "(partially offsetting for puts, reinforcing for calls). Theta is a function of five variables: "
            "&theta; = &theta;(S, K, T, &sigma;, r). For short sellers, daily income = &ndash;&theta;/365."
        )
    )
    subsection(story, "3.1 The OTM Theta Peak")
    story.append(
        P(
            "For OTM options, the accelerating 1/&radic;T and decelerating Gaussian collapse of &phi;(d1) compete. Their crossover yields:"
        )
    )
    formula_box(
        story,
        [
            "T*  &asymp;  ln&sup2;(S/K) / &sigma;&sup2;",
            "Doubling distance from ATM  &rarr;  peak shifts 4&times; earlier",
            "Doubling IV  &rarr;  peak shifts 4&times; later",
            "At ATM (S = K):  T* = 0, peaks at expiry",
        ],
    )
    source(story, "Derived] Analytically from BS PDE; confirmed by Emery, Guo &amp; Su (2008)")
    story.append(
        P(
            "The gamma-theta duality (&theta; = &ndash;&frac12;&middot;&sigma;&sup2;&middot;S&sup2;&middot;&Gamma; + r&middot;(V &ndash; S&middot;&Delta;)) "
            "means the theta peak coincides with the gamma peak at any moneyness."
        )
    )
    subsection(story, "3.2 P&amp;L Decomposition &amp; Greek Interaction")
    story.append(
        P(
            "Theta does not operate in isolation. The instantaneous change in option value is the sum of contributions from all Greeks:"
        )
    )
    formula_box(story, ["dV  &asymp;  &Delta;&middot;dS  +  &frac12;&Gamma;&middot;dS&sup2;  +  Vega&middot;d&sigma;  +  &theta;&middot;dt  +  &rho;&middot;dr"])
    add_table(story,
            ["Term", "Greek", "Meaning", "Impact on Short Premium"],
            [
                ["&Delta;&middot;dS", "Delta", "Directional exposure to underlying movement", "Loss if spot moves against position"],
                ["&frac12;&Gamma;&middot;dS&sup2;", "Gamma", "Convexity: sensitivity of delta to spot moves", "Always negative for short options; amplifies losses"],
                ["Vega&middot;d&sigma;", "Vega", "Exposure to changes in implied volatility", "Short premium is short vega; IV spikes cause losses discontinuously"],
                ["&theta;&middot;dt", "Theta", "Time decay; this report&rsquo;s primary focus", "Positive for short premium; only Greek that reliably favors the seller"],
                ["&rho;&middot;dr", "Rho", "Interest rate sensitivity", "Small for short-dated; material &gt; 90 DTE"],
            ],
            col_widths=[0.12, 0.10, 0.34, 0.44],
    )
    story.append(P("Short premium strategies are structurally:"))
    bullets(
        story,
        [
            "Short gamma (convexity works against you)",
            "Short vega (IV expansion causes losses)",
            "Long theta (time decay is your income)",
            "Long variance risk premium (IV &gt; realized vol on average)",
        ],
    )
    formula_box(
        story,
        [
            "Short premium = short gamma + short vega + long theta + long VRP",
            "Vega asymmetry: theta accrues gradually; vega materializes discontinuously",
        ],
    )
    story.append(
        P(
            "Realized P&amp;L is the cumulative result of interacting Greeks, not isolated theta decay. A position can "
            "collect positive theta daily yet lose money overall if gamma or vega losses exceed theta income. The "
            "variance risk premium (Section 1) compensates sellers for bearing this structural short-gamma, short-vega "
            "exposure. When realized volatility exceeds implied volatility, the gamma term (&frac12;&Gamma;&middot;dS&sup2;) "
            "dominates theta, producing net losses regardless of time decay collected."
        )
    )
    source(story, "Derived] Standard stochastic Taylor expansion of option value")
    fig_block(
        story,
        "fig_sens_grid",
        "Figure A: T* peak timing across IV levels (left) and rate sensitivity of total theta (right).",
        title="3.3 Parameter Sensitivity",
    )
    story.append(
        P(
            "T* is sensitive to IV but not to interest rates for short-dated options. Conclusions in this report are robust "
            "to rate variation within the 1&ndash;8% range tested."
        )
    )
    source(story, "Derived] Analytical from T* formula; rate sensitivity computed across r = 1&ndash;8%")
    subsection(story, "3.4 Gamma Scaling and Expiry Risk")
    story.append(
        P(
            "Near ATM, gamma scales approximately as &Gamma; &prop; 1/&radic;T. This explains why the T* framework matters and "
            "why the 21 DTE exit rule exists&mdash;it removes positions before gamma becomes the dominant P&amp;L driver."
        )
    )
    source(story, "Derived] Gamma scaling from BS formula; &Gamma; = &phi;(d1) / (S&sigma;&radic;T)")
    fig_block(
        story,
        "fig_path_dep",
        "Figure I: Path dependency demonstration. Both paths start at $100 and end at $98.80. "
        "Path A (realized vol 4%) produces smooth theta accumulation. Path B (realized vol 47%) produces violent daily P&amp;L swings.",
        title="3.5 Path Dependency of Theta Realization",
        lead="Theta is not realized deterministically&mdash;it is filtered through gamma-driven path dependence. Two price paths "
        "with identical starting and ending points can produce materially different P&amp;L experiences.",
    )
    story.append(
        P(
            "Theta projections are invalid without path assumptions. Static theta calculations assume the underlying does not move; "
            "realized P&amp;L is determined by the interaction of theta with the gamma-driven path. In low realized-vol paths, "
            "theta dominates and accumulates smoothly. In high realized-vol paths, gamma losses can exceed theta income even when "
            "the underlying finishes in a favorable position. This is the mechanism behind the variance risk premium."
        )
    )
    subsection(story, "3.6 Model Limitations")
    story.append(
        P(
            "European BS for analytical clarity. American early-exercise has limited impact on OTM. Flat-vol assumption ignores skew; "
            "per-leg IVs can be layered on. Transaction costs: Section 9. Path dependency: Monte Carlo in Sections 8 and 12."
        )
    )


def build_section_4(story):
    section(
        story,
        "sec4",
        "4. Single-Leg Strategies",
        lead="OTM short puts and calls exhibit intermediate theta peaks (T*) rather than pure expiry acceleration.",
        opening=_fig_flowables(
            "fig01_put_moneyness",
            "Figure 1: Short put theta vs DTE by moneyness. &sigma; = 80%, K = $100.",
            title="4.1 Short Put &mdash; Moneyness Effect",
        ),
    )
    story.append(
        P(
            "ATM: theta accelerates because gamma concentrates at the strike. S/K=1.05: peak &asymp; DTE 10. "
            "S/K=1.20: peaks near DTE 30. S/K=1.40: peaks &asymp; DTE 60. ITM (S/K=0.90): plateaus, can turn negative. "
            "Takeaway: OTM short puts do not accelerate into expiry."
        )
    )
    add_table(story,
            ["Put &Delta;", "Approx S/K", "T* Peak DTE", "Decay Profile", "Relative Tail Risk"],
            [
                ["&minus;50", "1.00 (ATM)", "0 (at expiry)", "Accelerating", "Highest"],
                ["&minus;30", "1.07", "&asymp;8 DTE", "Mild hump", "High"],
                ["&minus;20", "1.12", "&asymp;18 DTE", "Moderate hump", "Moderate"],
                ["&minus;15", "1.17", "&asymp;30 DTE", "Front-loaded", "Moderate-Low"],
                ["&minus;10", "1.25", "&asymp;55 DTE", "Strongly front-loaded", "Low"],
                ["&minus;5", "1.40", "&asymp;120 DTE", "Very early peak", "Very Low"],
            ],
            col_widths=[0.12, 0.16, 0.16, 0.24, 0.32],
            footnote="[Derived] Computed from BS at &sigma; = 30%, 45 DTE, r = 5%. Approximate; varies with IV and time.",
            heading="Delta-to-Moneyness Mapping",
    )
    fig_block(story, "fig02_put_iv", "Figure 2: IV effect on OTM short put. S/K = 1.30.", title="4.1.2 IV Effect")
    story.append(
        P(
            "Low IV: early peak with low magnitude. High IV widens the distribution, making the option behave like near-ATM&mdash;"
            "peak shifts near expiry with approximately 10&times; magnitude."
        )
    )
    fig_block(
        story,
        "fig03_put_iv_shock",
        "Figure 3: IV shock (60% &rarr; 120%). Left: OTM. Right: ATM.",
        title="4.1.3 IV Shock Asymmetry",
    )
    story.append(
        P(
            "OTM: peak theta increases 3&ndash;4&times;, shifts 20&ndash;40 days later. ATM: magnitude only. "
            "Selling OTM premium ahead of events is most theta-efficient because the IV shock increases extrinsic value."
        )
    )
    fig_block(story, "fig04_put_surface", "Figure 4: 3D short put theta surface. &sigma; = 80%.", title="4.1.4 Theta Surface &amp; Peak Timing")
    fig_block(story, "fig05_peak_timing", "Figure 5: Peak theta DTE vs moneyness and volatility.")
    fig_block(
        story,
        "fig06_call_moneyness",
        "Figure 6: Short call theta vs DTE by moneyness. &sigma; = 80%.",
        title="4.2 Short Call",
        lead="Identical peak structure to puts. Carry term reinforces the volatility term, producing slightly higher daily theta "
        "vs puts at the same distance from ATM. T* applies with inverted moneyness (OTM call: S/K &lt; 1).",
    )


def build_section_5(story):
    section(
        story,
        "sec5",
        "5. Multi-Leg Strategies",
        lead="Composite theta = algebraic sum of each leg. OTM legs experience peak-shift; ATM legs see magnitude scaling only.",
        opening=_fig_flowables(
            "fig07_straddle",
            "Figure 7: Short straddle theta by underlying position. &sigma; = 80%.",
            title="5.1 Short Straddle",
        ),
    )
    story.append(P("ATM: pure acceleration. Displacement introduces hump pattern. Theta scales linearly with &sigma;."))
    fig_block(story, "fig08_strangle", "Figure 8: Short strangle theta by wing width. &sigma; = 80%.", title="5.2 Short Strangle")
    story.append(
        P(
            "Wider wings = earlier peak, lower magnitude. Both legs are OTM, so both experience the T* peak-shift."
        )
    )
    fig_block(story, "fig09_credit_spread", "Figure 9: Bull put spread net theta by width. S = $105, &sigma; = 80%.", title="5.3 Credit Spread")
    story.append(
        P(
            "Long leg's theta peaks earlier because it is further OTM. Net theta can increase in the final days as the short leg's "
            "gamma accelerates while the long leg's does not."
        )
    )
    fig_block(story, "fig10_iron_condor", "Figure 10: Iron condor net theta by configuration. &sigma; = 80%.", title="5.4 Iron Condor")
    story.append(P("Wider: flatter, earlier plateau. Four-leg smoothing dampens IV shock. 45 DTE wide condor earns 60&ndash;70% of total theta in the first 20 days."))
    add_table(story,
            ["Strategy", "Peak Shape", "IV Sensitivity", "Front-Loading", "Best For"],
            [
                ["Straddle", "ATM acceleration", "Moderate (linear)", "Low (back-loaded)", "Neutral, high IV"],
                ["Strangle", "Humped mid-period", "High (structural)", "High", "Range-bound"],
                ["Credit Spread", "Net acceleration", "Asymmetric", "Variable by width", "Directional bias"],
                ["Iron Condor", "Plateau", "Dampened", "Moderate&ndash;High", "Defined-risk neutral"],
            ],
            col_widths=[0.18, 0.22, 0.20, 0.18, 0.22],
    )
    story.append(P("Strategy selection is fundamentally a choice of Greek exposure profile:"))
    add_table(story,
            ["Strategy", "&theta; (Theta)", "&Gamma; (Gamma)", "Vega", "Tail Risk", "P&amp;L Driver"],
            [
                ["CSP (naked)", "+", "&minus;&minus;", "&minus;", "High (unlimited downside)", "VRP + theta vs gamma + vega losses"],
                ["Short Strangle", "++", "&minus;&minus;&minus;", "&minus;&minus;", "High (two-sided)", "Maximum theta but maximum Greek exposure"],
                ["Credit Spread", "+", "Limited (capped by long leg)", "&minus;", "Capped (width of spread)", "Defined risk trades theta for protection"],
                ["Iron Condor", "+", "Moderate (four-leg dampening)", "Moderate", "Controlled (both sides capped)", "Balanced Greek profile; best theta-per-risk"],
            ],
            col_widths=[0.14, 0.10, 0.22, 0.10, 0.20, 0.24],
            footnote="[Derived] Greek signs follow directly from option pricing theory. Strategy selection should match the trader's view on which Greeks will dominate the regime (see Section 8).",
    )
    fig_block(story, "fig11_portfolio", "Figure 11: Portfolio theta aggregation (BS-only), 4 positions over 45 DTE.", title="5.5 Portfolio Aggregation")
    add_table(story,
            ["Position", "Total", "1st Half", "2nd Half", "Profile"],
            [
                ["ATM CSP (IV=35%)", "$206", "$66 (32%)", "$140 (68%)", "Back-loaded"],
                ["OTM Strangle (IV=90%)", "$1,013", "$560 (55%)", "$453 (45%)", "Front-loaded"],
                ["Credit Spread (IV=110%)", "$413", "$81 (20%)", "$331 (80%)", "Back-loaded"],
                ["Far OTM CSP (IV=55%)", "$34", "$28 (82%)", "$6 (18%)", "Strongly front-loaded"],
            ],
            col_widths=[0.30, 0.14, 0.18, 0.18, 0.20],
    )
    story.append(P("Opposing profiles partially offset at portfolio level, producing more uniform income."))


def build_section_6(story):
    skew_fig, skew_need = _fig_flowables(
        "fig_skew",
        "Figure B: Theta under flat vs skewed IV. Left: OTM put. Right: strangle.",
        title="6.1 How Skew Changes Theta Profiles",
    )
    intro = P(
        "These impact P&amp;L through vega and vanna, and can materially alter theta profiles."
    )
    section(
        story,
        "sec6",
        "6. Volatility Skew &amp; Term Structure",
        lead="Equity options exhibit volatility skew and term structure that alter per-leg theta and roll economics.",
        opening=([intro, *skew_fig], skew_need + 0.35 * inch),
    )
    story.append(
        P(
            "OTM puts: Under typical equity skew, the flat-vol model tends to underestimate OTM put theta by 20&ndash;40%. "
            "The T* peak also shifts later. Strangles: put-skew makes the put leg contribute disproportionately more theta."
        )
    )
    subsection(story, "6.2 Term Structure Effects")
    story.append(
        P(
            "A steep term structure means rolling from near-term to longer-dated expiry involves selling higher IV. "
            "An inverted term structure penalizes rolls. The T* formula applies per-expiry."
        )
    )
    subsection(story, "6.3 Practical Implications", opening=_table_flowables(
            ["Flat-Vol Assumption", "Skew Reality", "Impact"],
            [
                ["OTM put θ low", "Skew +20–40% θ", "Favor OTM puts"],
                ["Symmetric strangle", "Put leg dominates θ", "Manage put leg"],
                ["Uniform T*", "T* later (OTM puts)", "Per-leg IV exits"],
                ["IV-neutral rolls", "Term structure matters", "Roll steep; skip inversion"],
            ],
            col_widths=[0.26, 0.32, 0.42],
            footnote="[Calibrated] Skew magnitudes typical for equity indexes. Motivates Section 7.",
    ))


def build_section_7(story):
    section(story, "sec7", "7. Preliminary Empirical Evidence")
    story.append(
        P(
            "This section presents preliminary empirical analysis of whether volatility surface features contain predictive "
            "information about forward equity returns. The analysis is illustrative, not definitive: SPY daily data, "
            "March 2021 through March 2023, 76 weekly observations. This section does not constitute a trading signal."
        )
    )
    sig = SIGNALS
    ss = sig["sample_size"]
    sf = sig["signal_frequency"]
    ind = sig["individual_signals"]
    subsection(story, "7.1 Signal Behavior and Forward Returns", opening=_table_flowables(
            ["Signal", "Freq.", "Active", "Inactive", "Note"],
            [
                ["Vol Spike", f"{100*sf['vol_spike']:.1f}%", str(ss["vol_spike_true"]), str(ss["vol_spike_false"]), "Rare (n=3)"],
                ["Skew Spike", f"{100*sf['skew_spike']:.1f}%", str(ss["skew_spike_true"]), str(ss["skew_spike_false"]), "Rare; 0% hit (n=3)"],
                ["Term Inversion", f"{100*sf['term_inversion']:.1f}%", str(ss["term_inversion_true"]), str(ss["term_inversion_false"]), "84% active; regime tag"],
            ],
            col_widths=[0.16, 0.10, 0.10, 0.10, 0.54],
            footnote="Total sample: 76 observations. Vol/skew spike: 3 activations each.",
            heading="Signal Frequency and Sample Sizes",
    ))
    add_table(story,
            ["Signal", "Cond.", "n", "5d Ret", "Hit %", "Read"],
            [
                ["Vol Spike", "On", "3", pct(ind["vol_spike"]["fwd_return_5d"]["true"]), hit_rate(ind["vol_spike"]["hit_rate_5d"]["true"]), "Mean revert (n=3)"],
                ["Vol Spike", "Off", "73", pct(ind["vol_spike"]["fwd_return_5d"]["false"]), hit_rate(ind["vol_spike"]["hit_rate_5d"]["false"]), "Baseline"],
                ["Skew Spike", "On", "3", pct(ind["skew_spike"]["fwd_return_5d"]["true"]), hit_rate(ind["skew_spike"]["hit_rate_5d"]["true"]), "Negative (n=3)"],
                ["Skew Spike", "Off", "73", pct(ind["skew_spike"]["fwd_return_5d"]["false"]), hit_rate(ind["skew_spike"]["hit_rate_5d"]["false"]), "Neutral"],
                ["Term Inv.", "On", "64", pct(ind["term_inversion"]["fwd_return_5d"]["true"]), hit_rate(ind["term_inversion"]["hit_rate_5d"]["true"]), "Weak − (n=64)"],
                ["Term Inv.", "Off", "12", pct(ind["term_inversion"]["fwd_return_5d"]["false"]), hit_rate(ind["term_inversion"]["hit_rate_5d"]["false"]), "Slight + (n=12)"],
            ],
            col_widths=[0.12, 0.08, 0.08, 0.10, 0.10, 0.52],
            footnote="SPY daily, Mar 2021–Mar 2023. n=3 signals not statistically significant.",
            heading="Individual Signal Results (5-Day Forward Returns)",
    )
    subsection(story, "7.2 Signal Interactions")
    it = sig["interaction_table"]
    story.append(
        P(
            "When isolated from skew spikes, vol spikes are associated with 5-day forward returns of +1.75% (n = 3). "
            "When skew spikes occur without vol spikes, forward returns are &minus;2.08% (n = 3)."
        )
    )
    add_table(story,
            ["Skew", "Vol", "n", "5d Ret", "Read"],
            [
                ["No", "No", "70", pct(it["skew_false_vol_false"]), "Baseline"],
                ["No", "Yes", "3", pct(it["skew_false_vol_true"]), "Vol mean revert"],
                ["Yes", "No", "3", pct(it["skew_true_vol_false"]), "Skew risk"],
            ],
            col_widths=[0.08, 0.08, 0.08, 0.14, 0.62],
    )
    subsection(story, "7.3 Regime Context")
    rt = sig["regime_table"]
    add_table(story,
            ["Regime", "5d Ret", "Read"],
            [
                ["Low vol, no crash", pct(rt["low_vol_no_crash"]), "Calm drift +"],
                ["Low vol, crash signal", pct(rt["low_vol_crash"]), "Calm-vol warning"],
                ["High vol, crash signal", pct(rt["high_vol_crash"]), "Signal absorbed"],
            ],
            col_widths=[0.30, 0.14, 0.56],
            footnote="Regimes by ATM vol vs trailing median. Crash signal = skew + term structure.",
    )
    subsection(story, "7.4 Implications and Limitations")
    story.append(
        P(
            "The directional patterns are economically interpretable, but statistical limitations are severe&mdash;vol spike and "
            "skew spike signals each activated on only 3 of 76 observations. These results provide directional hypotheses for "
            "further investigation and should not be used to inform position decisions in their current form. "
            "They are <b>not</b> validated by the SPY options-chain pilot in Appendix B, which tests Section 20 "
            "management rules rather than surface signal predictability."
        )
    )
    source(story, "Calibrated] SPY daily data, Mar 2021 &ndash; Mar 2023. Small sample; results are directional, not definitive.")


def build_section_8(story):
    section(
        story,
        "sec8",
        "8. Regime Analysis",
        lead="VIX-based regime bins anchor simulated theta paths and Greek dominance patterns.",
        opening=_table_flowables(
            ["Regime", "VIX", "&sigma;", "Drift", "Jumps", "Example"],
            [
                ["Low Volatility", "&lt; 15", "15%", "+2%", "None", "2017, mid-2024"],
                ["Normal", "15&ndash;20", "20%", "+4%", "None", "2019, early 2024"],
                ["Elevated", "20&ndash;30", "35%", "&minus;2%", "None", "Late 2022"],
                ["Crisis / Jump", "&gt; 30", "50%", "&minus;10%", "&lambda; = 3", "Mar 2020"],
            ],
            col_widths=[0.18, 0.10, 0.10, 0.10, 0.12, 0.20],
            footnote="[Calibrated] VIX &gt; 30 corresponds approximately to the upper 5th percentile of daily VIX readings since 1990.",
        ),
    )
    fig_block(
        story,
        "fig_regime",
        "Figure 12: OTM short put (S/K = 1.11) theta across four regimes. Shading: 25th&ndash;75th percentile bands. 1,500 paths each.",
    )
    story.append(
        P(
            "Low vol: theta-dominated regime. Normal: clear front-loaded pattern driven by the T* peak-shift. "
            "Elevated: higher magnitude, wider dispersion. Crisis: gamma + vega dominated regime where both convexity losses "
            "and IV expansion overwhelm theta income."
        )
    )
    add_table(story,
            ["Regime", "Greek", "P&amp;L Driver", "Implication"],
            [
                ["Low Vol (VIX &lt; 15)", "Theta", "Decay dominates", "θ works; mgmt adds friction"],
                ["Normal (15–20)", "θ + Γ", "Balanced θ/Γ", "50% profit / 21 DTE"],
                ["Rising Vol (20–30)", "Vega", "IV expansion", "Size down; defined risk"],
                ["Near Expiry (&lt; 10 DTE)", "Gamma", "Convexity", "High risk; T* exit"],
                ["Crisis (VIX &gt; 30)", "Γ + Vega", "Convexity + IV", "Min exposure; defined risk"],
            ],
            col_widths=[0.17, 0.12, 0.26, 0.45],
            footnote="[Calibrated] Theta dominates P&amp;L only in low-to-normal vol regimes.",
            heading="Regime-Based Greek Dominance",
    )
    story.append(
        P(
            "<b>Key insight:</b> Theta-centric strategies implicitly assume theta will be the dominant Greek. "
            "This assumption holds in low-to-normal volatility regimes but breaks down when vega or gamma dominance emerges."
        )
    )


def build_section_9(story):
    section(
        story,
        "sec9",
        "9. Transaction Costs",
        opening=_table_flowables(
            ["Tier", "Eff. Half-Spread", "Commission", "Round-Trip ($3 Premium)", "Drag"],
            [
                ["Retail", "3.0%", "$0.65 / ct", "$2.10", "7.0%"],
                ["Active Retail", "2.0%", "$0.50 / ct", "$1.60", "5.3%"],
                ["Institutional", "1.0%", "$0.10 / ct", "$0.80", "2.7%"],
            ],
            col_widths=[0.18, 0.18, 0.18, 0.24, 0.12],
            footnote="[Calibrated] Muravyev &amp; Pearson (2020): avg approximately 2.2% eff. spread.",
        ),
    )
    fig_block(story, "fig_costs", "Figure 13: Net theta after transaction costs (S = $105, K = $100, &sigma; = 80%).")
    story.append(
        P(
            "Costs matter most for narrow spreads with thin premium, frequent rolls, and low-IV OTM positions. "
            "Retail round-trip of approximately 7% on a $3 premium is material for strategies targeting 50% profit."
        )
    )


def build_section_10(story):
    section(
        story,
        "sec10",
        "10. Risk Metrics &amp; Tail Analysis",
        lead="Distribution-level metrics compare tail risk, clustering, and recovery across structure types.",
        opening=_fig_flowables(
            "fig_risk",
            "Figure 14: Theta&ndash;risk frontier by moneyness. Each dot = one S/K level. 45 DTE, &sigma; = 30%, 5,000 paths.",
        ),
    )
    story.append(
        P(
            "ATM collects the most theta but faces approximately 3&ndash;4&times; higher tail risk than S/K = 1.20. "
            "The theta-per-unit-of-tail-risk ratio favors slightly OTM positions (S/K approximately 1.05&ndash;1.10) over pure ATM."
        )
    )
    fig_block(
        story,
        "fig_risk_equity",
        "Figure E: Equity curves (left) and drawdown paths (right). Solid = hold-to-expiry, dashed = managed.",
        title="10.1 Distribution-Level Risk Metrics",
        lead="Single-trade averages obscure loss distribution shape. This section compares max drawdown, loss clustering, "
        "CVaR, and recovery time across CSP, strangle, and credit spread (200 trades each, IV = 25%, RV = 18%).",
    )
    add_table(story,
            ["Strategy", "Max DD", "5th %", "CVaR", "Loss %", "Skew"],
            [
                ["CSP hold", "34.2%", "−5.1%", "−8.9%", "18%", "−3.0"],
                ["CSP mngd", "10.0%", "−2.2%", "−4.1%", "25%", "−3.0"],
                ["Strangle hold", "9.5%", "−2.6%", "−4.9%", "12%", "−3.7"],
                ["Strangle mngd", "8.5%", "−1.7%", "−2.9%", "20%", "−3.3"],
                ["Spread hold", "100%*", "−82%", "−82%", "20%", "−2.0"],
                ["Spread mngd", "100%*", "−40%", "−54%", "30%", "−2.0"],
            ],
            col_widths=[0.15, 0.13, 0.13, 0.13, 0.12, 0.11],
            footnote="*Spread max loss = 100% of margin. mngd = managed. Model-contingent.",
            heading="Core Risk Metrics",
    )
    add_table(story,
            ["Strategy", "Max Consec.", "Max Recovery"],
            [
                ["CSP hold", "3", "10"],
                ["CSP mngd", "3", "34"],
                ["Strangle hold", "2", "14"],
                ["Strangle mngd", "3", "34"],
                ["Spread hold", "2", "50"],
                ["Spread mngd", "5", "165"],
            ],
            col_widths=[0.38, 0.31, 0.31],
            footnote="Max Recovery = trades to recover from worst drawdown.",
            heading="Recovery &amp; Clustering Metrics",
    )
    fig_block(story, "fig_risk_clustering", "Figure F: Loss clustering by structure (small multiples).")
    fig_block(story, "fig_risk_boxplots", "Figure G: P&amp;L distribution box plots by structure. All strategies show negative skew.")
    add_table(story,
            ["Regime", "Structure", "Avg Cluster", "Max Cluster", "5th %ile", "CVaR 5%"],
            [
                ["Low Vol", "CSP", "1.0", "1", "&minus;1.4%", "&minus;2.4%"],
                ["Low Vol", "Strangle", "1.1", "2", "&minus;1.9%", "&minus;2.9%"],
                ["Low Vol", "Spread", "1.1", "2", "&minus;41%", "&minus;73%"],
                ["Normal", "CSP", "1.1", "2", "&minus;4.6%", "&minus;9.0%"],
                ["Normal", "Strangle", "1.2", "2", "&minus;2.7%", "&minus;4.3%"],
                ["Normal", "Spread", "1.4", "3", "&minus;82%", "&minus;82%"],
                ["Elevated", "CSP", "1.3", "3", "&minus;14%", "&minus;16%"],
                ["Elevated", "Strangle", "1.3", "4", "&minus;11%", "&minus;17%"],
                ["Elevated", "Spread", "1.5", "3", "&minus;70%", "&minus;70%"],
            ],
            col_widths=[0.14, 0.14, 0.14, 0.14, 0.16, 0.16],
            footnote="150 trades per cell. Loss clustering increases with vol regime across all structures.",
            heading="Regime-Conditioned Risk",
    )
    story.append(
        P(
            "<b>Key observations:</b> (1) Strangles show the best risk-adjusted profile: lowest max drawdown as percentage of margin "
            "(9.5% hold, 8.5% managed) with the lowest loss rate (12% hold). (2) Credit spreads have binary loss profiles&mdash;"
            "losses tend to be near 100% of margin when they occur. Management increases loss frequency (30% vs 20%) by triggering "
            "exits on mark-to-market noise. (3) CSP managed cuts max drawdown from 34% to 10% but extends max recovery time. "
            "(4) All structures show more clustering in elevated vol regimes. (5) Negative skew is universal (&minus;2.0 to &minus;3.7), "
            "confirming left-tail risk is structural in short premium."
        )
    )
    story.append(
        P(
            "<b>Sizing implication:</b> Given that the worst-case single-trade loss for a CSP is its full strike value, and the 5th "
            "percentile loss under normal vol is approximately 5% of margin, a position size of 2&ndash;3% of portfolio per CSP limits "
            "the 5th percentile portfolio impact to 0.1&ndash;0.15%. For credit spreads, sizing should be proportionally smaller per unit "
            "of notional&mdash;typically 1&ndash;2% of portfolio per spread. Strangles fall between the two."
        )
    )
    subsection(story, "10.2 Portfolio Stress Scenarios", opening=_table_flowables(
            ["Scenario", "Description", "Impact", "Mitigation"],
            [
                ["−5% gap", "Open −5% vs prior close", "15–25% margin loss", "2× margin; use spreads"],
                ["Vol spike", "VIX 2×; spreads 3–5×", "MTM −10–20%", "Stagger expiries; GTC exits"],
                ["Corr. convergence", "All names move together", "Diversification fails", "Cap net Δ; hedge"],
            ],
            col_widths=[0.14, 0.28, 0.26, 0.32],
            footnote="[Convention] Approximate portfolio-level impacts.",
    ))


def build_section_11(story):
    section(story, "sec11", "11. Merton Jump-Diffusion Extension")
    story.append(
        P(
            "Merton (1976) augments GBM with Poisson jumps. The option price becomes a weighted sum of BS prices "
            "across jump scenarios, with theta gaining a jump-risk premium component."
        )
    )
    fig_block(
        story,
        "fig_merton",
        "Figure 15: Merton vs BS theta. Left: ATM (nearly identical). Right: OTM (Merton higher, later peak).",
    )
    story.append(
        P(
            "When to use: When the underlying has a known discrete event priced via elevated IV relative to realized vol. "
            "Kou (2002) provides a better fit for asymmetric jumps."
        )
    )
    source(story, "Convention] No formal cutoff; Ramezani &amp; Zeng (2007) found both Merton and Kou outperform BS.")


def build_section_12(story):
    section(story, "sec12", "12. Rule Sensitivity &amp; Benchmarks (Simulated)")
    story.append(
        P(
            "Trade rules in premium-selling are often conventions without formal optimization. "
            "This section is <b>rule sensitivity analysis</b> under Monte Carlo with an embedded VRP "
            "(IV = 25%, realized vol = 18%)&mdash;not an historical validation. "
            "Figures 16&ndash;18 are simulation-based. A pilot real-chain benchmark for Section 20 rules "
            "appears in Appendix B; it does not replace the DTE sweep or normalized benchmark figures below."
        )
    )
    fig_block(
        story,
        "fig_sweep",
        "Figure 16: Sharpe and win rate across DTE entries and profit targets. 400 paths/cell, OTM put S/K = 1.05.",
        title="12.1 DTE &times; Profit Target Sweep",
    )
    story.append(
        P(
            "The 45 DTE entry is competitive but not uniquely optimal&mdash;the 40&ndash;55 DTE range tends to produce similar Sharpe ratios. "
            "Takeaway: The 45 DTE / 50% profit rule is a reasonable default, not a proven optimum."
        )
    )
    fig_block(
        story,
        "fig_dte_ci",
        "Figure C: Sharpe ratio by entry DTE with 80% bootstrap confidence interval.",
        title="12.2 DTE Selection with Confidence Intervals",
    )
    story.append(
        P(
            "The Sharpe curve shows a broad plateau from approximately 35&ndash;60 DTE. Below 30 DTE, risk-adjusted returns "
            "tend to deteriorate as gamma dominates."
        )
    )
    source(story, "Calibrated] MC simulation; competitive zone sensitive to VRP magnitude")
    fig_block(
        story,
        "fig_sensitivity",
        "Figure 17: How total theta and front-loading change with IV, moneyness, and costs.",
        title="12.3 Sensitivity Analysis",
    )
    story.append(P("Total theta is roughly linear in IV but nonlinear in moneyness. Front-loading increases with both."))
    fig_block(
        story,
        "fig_bench_norm",
        "Figure 18: Equal-margin benchmark. $5,000 margin budget, IV = 25%, RV = 18%, 500 cycles.",
        title="12.4 Normalized Benchmark Comparison",
    )
    add_table(story,
            ["Strategy", "Sharpe", "Win %", "ROI/Trade", "Notes"],
            [
                ["ATM CSP (K = 100)", "0.50", "70%", "1.55%", "Moderate SR; highest absolute theta"],
                ["OTM CSP (K = 95)", "0.59", "84%", "1.02%", "Best Sharpe for naked"],
                ["OTM CSP managed", "0.19", "78%", "0.23%", "Management reduces per-trade ROI"],
                ["Credit Spread 95/90", "0.30", "73%", "1.91%", "Best capital efficiency"],
            ],
            col_widths=[0.24, 0.12, 0.12, 0.14, 0.38],
            footnote="[Convention] Simulation under constant vol with VRP. Results are sensitive to VRP magnitude.",
    )
    story.append(
        P(
            "Sections 13&ndash;19 extend this analysis into second-order Greeks, variance decomposition, hedging, "
            "surface dynamics, model risk, and execution&mdash;the machinery underlying the decision rules in Section 20."
        )
    )


def build_section_20(story):
    tbl_20_1, est_20_1 = _table_flowables(
        ["Rule", "Logic", "Source", "Fails When"],
        [
            ["DTE at Entry", "40–55 DTE", "[Convention] MC plateau", "Earnings window; inverted term"],
            ["IV Filter", "IV Rank &gt; 50%", "[Calibrated] VRP capture", "IV ↑ from tail, not VRP"],
            ["Regime Check", "Cut size VIX &gt; 30", "[Convention] regime MC", "Mean-reverting vol spike"],
        ],
        col_widths=[0.14, 0.20, 0.28, 0.38],
    )
    section(
        story,
        "sec20",
        "20. Decision Framework &amp; Trade Rules",
        lead="Sections 1&ndash;12 establish pricing, strategies, and simulated rule sensitivity. Sections 13&ndash;19 develop the full "
        "Greek interaction system. This section translates that machinery into operational rules for <b>unhedged</b> "
        "short premium positions.",
        opening=([P("20.1 Entry Rules", "Subsection"), *tbl_20_1], 0.42 * inch + est_20_1),
    )
    story.append(
        P(
            "These rules are the unhedged baseline. Second-order triggers (Section 13), dynamic Greek monitoring "
            "(Section 15), and hedging overlays (Section 16) can modify exit logic; surface and execution constraints "
            "(Sections 13&ndash;19) bound net edge after costs."
        )
    )
    subsection(story, "20.2 Exit Rules", opening=_table_flowables(
            ["Rule", "Logic", "Source", "Fails When"],
            [
                ["Profit Target", "50% max (or 25%)", "[Convention] tastylive", "Stable VRP; hold wins"],
                ["DTE Floor", "Close/roll at 21 DTE", "[Convention] γ zone", "Low-IV grind; θ remains"],
                ["Peak-Aware", "DTE &lt; T* → close", "[Derived] T* formula", "Spot moved; stale T*"],
                ["Post-Event", "Close 1–2d post catalyst", "[Calibrated] IV crush", "IV stays elevated"],
            ],
            col_widths=[0.14, 0.22, 0.26, 0.38],
    ))
    story.append(
        P(
            "These rules were encoded in a chain backtest engine (Appendix B) and applied to historical SPY put "
            "marks from Databento OPRA data. Pilot results are directional; Monte Carlo in Sections 12 and 21 "
            "remains the primary stress framework until sample size increases."
        )
    )
    subsection(
        story,
        "20.3 Decision Matrix",
        opening=_fig_flowables(
            "fig_matrix",
            "Figure 19: Peak theta DTE by moneyness &times; IV.",
            lead="Green = peaks near expiry (hold). Red = peaks early (close early).",
        ),
    )
    subsection(story, "20.4 Position Sizing", opening=_table_flowables(
            ["Regime", "Max Size", "Rationale"],
            [
                ["Low Vol (VIX &lt; 15)", "3&ndash;5%", "Premium thin; need more positions"],
                ["Normal (15&ndash;20)", "2&ndash;3%", "Standard allocation"],
                ["Elevated (20&ndash;30)", "1&ndash;2%", "Higher tail risk; wider outcomes"],
                ["Crisis (&gt; 30)", "0.5&ndash;1%", "Jump risk dominates; size down"],
            ],
            col_widths=[0.28, 0.16, 0.56],
            footnote="[Convention] Starting points; optimize per portfolio.",
    ))
    add_table(story,
            ["Component", "Trigger", "Signal", "Action"],
            [
                ["45 DTE entry", "Thin VRP", "IV Rank &lt; 20%", "Wait / reduce size"],
                ["OTM CSP", "Downtrend → breach", "Spot &lt; 20d MA; Δ → −50", "Spreads; tighten stop"],
                ["Short strangle", "Vol ↑; leg ITM", "VIX ↑; strike breach", "Roll tested leg; 2× stop"],
                ["50% profit", "Trend favors hold", "Spot trending", "75% target or hold"],
                ["21 DTE floor", "Low-IV grind", "IV &lt; 15%; OTM", "Hold if γ low"],
                ["T* exit", "Spot moved", "S/K shifted", "Recompute T*"],
                ["VIX sizing", "Dispersion break", "Low VIX; high ρ", "Size on name IV"],
                ["Credit spread", "Max loss zone", "Through long strike", "Accept loss; no adds"],
            ],
            col_widths=[0.13, 0.20, 0.24, 0.43],
            footnote="Not exhaustive. Correlation convergence + vol spike = worst compound failure.",
            heading="20.5 Failure Mode Reference",
    )
    subsection_lead(
        story,
        "20.6 Trade Lifecycle Example",
        "The following walkthrough traces a single simulated OTM short put from entry through exit (seed = 11), "
        "illustrating how the decision rules interact with the price path.",
    )
    fig_block(
        story,
        "fig_lifecycle",
        "Figure H: Trade lifecycle. Panel 1: spot price path. Panel 2: open P&amp;L with triggers. Panel 3: daily theta collected.",
    )
    add_table(story,
            ["Day", "Event", "Spot", "P&amp;L", "Decision"],
            [
                ["0", "Entry", "$100.00", "$0", "Sell 95P @ $1.65; $165 prem"],
                ["2–5", "Drift up", "$101–102", "+$40–60", "θ accrues; hold"],
                ["8–16", "Decline", "$93–97", "−$50 to −$222", "Day 16: spot &lt; K; max −$222"],
                ["Days 17–23", "Recovery", "$96–99", "−$120 to +$50", "P&amp;L turns positive"],
                ["24", "21 DTE exit", "$99.21", "+$70", "Close +$70 (42% of max)"],
                ["25–45", "Not held", "$97–101", "N/A", "Forgone θ ≈ $95"],
            ],
            col_widths=[0.08, 0.14, 0.12, 0.14, 0.52],
    )
    story.append(
        P(
            "<b>Key observations from this path:</b> (1) The position went underwater by $222 on day 16 when spot dropped below the "
            "strike. The management rules did not trigger an exit because neither the profit target nor the DTE floor was reached. "
            "(2) The 21 DTE floor triggered the exit on day 24 with a modest $70 profit. (3) The T* peak for this position was at "
            "DTE 12&mdash;the position was closed well before peak theta, forgoing approximately $95 of additional decay. "
            "(4) This trade illustrates the fundamental tension in premium selling: management rules sacrifice per-trade upside to limit "
            "exposure to gamma-driven path losses."
        )
    )


def build_section_22(story):
    section(
        story,
        "sec22",
        "22. Master Reference: Key Relationships",
        lead="Consolidated index of findings across Sections 1&ndash;23. "
        "<b>Robust</b> = analytically derived; <b>Tentative</b> = simulation-supported; "
        "<b>Model-contingent</b> = depends on model or convention choices.",
        opening=_table_flowables(
            ["#", "Finding", "Source", "Confidence", "Summary"],
            [
                ["1", "T* peak timing", "[Derived]", "Robust", "T* &asymp; ln&sup2;(S/K)/&sigma;&sup2;. ATM at expiry; OTM earlier."],
                ["2", "Moneyness effect", "[Derived]", "Robust", "ATM&rarr;OTM shifts peak earlier. Quadratic."],
                ["3", "IV effect", "[Derived]", "Robust", "Higher IV delays OTM peak, increases magnitude."],
                ["4", "IV shock asymmetry", "[Derived]", "Robust", "OTM: structural shift. ATM: magnitude only."],
                ["5", "Gamma-theta duality", "[Derived]", "Robust", "Theta tracks gamma at all moneyness."],
                ["6", "Multi-leg composition", "[Derived]", "Robust", "Composite theta = sum of legs."],
                ["7", "Skew impact", "[Calibrated]", "Tentative", "OTM put theta 20&ndash;40% higher under typical skew."],
            ],
            col_widths=[0.05, 0.18, 0.12, 0.14, 0.51],
        ),
    )
    add_table(story,
            ["#", "Finding", "Source", "Confidence", "Summary"],
            [
                ["8", "VRP foundation", "[Calibrated]", "Tentative", "Premium compensated but declining."],
                ["9", "Transaction costs", "[Calibrated]", "Tentative", "Approximately 2.2% half-spread; regime-dependent."],
                ["10", "DTE optimum", "[Convention]", "Model-contingent", "40&ndash;55 DTE MC plateau; not historical optimum."],
                ["11", "50% profit close", "[Convention]", "Model-contingent", "Hold may outperform in stable vol (§21 MC); pilot inconclusive."],
                ["12", "Regime thresholds", "[Convention]", "Model-contingent", "VIX bins are heuristic, not statistical."],
                ["13", "Merton advantage", "[Calibrated]", "Tentative", "Higher OTM theta vs BS; Kou better for asymmetry."],
                ["14", "Second-order Greeks", "[Derived]", "Robust", "Vomma/vanna/charm/speed peak at intermediate DTE (Sec. 13)."],
                ["15", "Variance identity", "[Derived]", "Robust", "P&amp;L<sub>&gamma;</sub> &prop; &sigma;&sup2;<sub>real</sub> &minus; &sigma;&sup2;<sub>impl</sub> (Sec. 14)."],
                ["16", "Hedging tradeoff", "[Calibrated]", "Tentative", "Delta hedge removes direction; gamma/vega remain (Sec. 16)."],
                ["17", "Surface dynamics", "[Calibrated]", "Tentative", "Sticky delta amplifies vega loss on spot drops (Sec. 17)."],
                ["18", "Model risk", "[Calibrated]", "Model-contingent", "Merton/stoch-vol shift T* and peak θ (Sec. 18)."],
                ["19", "Execution drag", "[Calibrated]", "Tentative", "OTM spreads wider; stress multiplies costs (Sec. 19)."],
                ["20", "Section 20 rules (pilot)", "[Calibrated]", "Pilot only", f"SPY chain n={_pilot_n()}; wide CIs; MC tail benefit not replicated."],
            ],
            col_widths=[0.05, 0.18, 0.12, 0.14, 0.51],
    )
    add_table(story,
            ["Position", "Moneyness", "1st Half", "2nd Half", "Profile"],
            [
                ["ATM CSP", "S/K = 1.00", "&asymp;32%", "&asymp;68%", "Back-loaded"],
                ["Near OTM", "S/K = 1.10", "&asymp;45%", "&asymp;55%", "Balanced"],
                ["OTM Strangle", "&plusmn;20%", "&asymp;55%", "&asymp;45%", "Front-loaded"],
                ["Far OTM", "S/K = 1.30", "&asymp;75%", "&asymp;25%", "Strongly front-loaded"],
            ],
            col_widths=[0.20, 0.20, 0.16, 0.16, 0.28],
            heading="Quick Reference: Integrated Theta (45-day hold)",
    )


def build_section_21(story):
    section(
        story,
        "sec21",
        "21. Monte Carlo Scenario Analysis",
        lead="Stress-tests the Section 20 management rules across four calibrated regimes. Crisis scenarios "
        "understate tail risk relative to sticky-delta surface dynamics (Section 17) and stress-period execution "
        "(Section 19).",
    )
    story.append(
        P(
            "Monte Carlo parameters approximate historical market regimes. These are <b>simulations</b>&mdash;"
            "not historical backtests&mdash;with parameters chosen to reflect each regime's characteristics. "
            f"A complementary <b>pilot</b> historical test on real SPY chains (Appendix B, n = {_pilot_n()} weekly entries) "
            "partially addresses the validation gap but is not yet sufficient to replace Figure D or the scenario table below. "
            "All scenarios model <b>unhedged</b> hold vs managed strategies; hedged overlays (Section 16) are a natural extension."
        )
    )
    add_table(story,
            ["Scenario", "IV Used", "Realized &sigma;", "Drift", "Jump &lambda;", "Rationale"],
            [
                ["2017 Low-Vol Grind", "12%", "10%", "+3%", "0", "Persistent low vol; steady drift"],
                ["Feb 2018 Volmageddon", "15%", "35%", "&minus;5%", "5.0", "Sudden vol spike; extreme jump"],
                ["Mar 2020 Crash", "20%", "60%", "&minus;15%", "8.0", "Pandemic shock; massive gap"],
                ["2022 Bear Grind", "28%", "25%", "&minus;4%", "0.5", "Elevated vol; grinding decline"],
            ],
            col_widths=[0.20, 0.12, 0.14, 0.10, 0.12, 0.32],
            footnote="[Convention] Parameters are approximate regime characterizations, not fitted to specific historical windows.",
    )
    fig_block(
        story,
        "fig_cases",
        "Figure D: Cumulative P&amp;L distributions (CDF) for hold-to-expiry vs managed strategies across simulated regimes.",
    )
    add_table(story,
            ["Regime", "Strategy", "Median", "5th %ile", "P(Loss)"],
            [
                ["Low Vol", "Hold", "0.2%", "0.0%", "5%"],
                ["Low Vol", "Managed", "0.1%", "&minus;0.5%", "13%"],
                ["Volmageddon", "Hold", "0.4%", "&minus;38.8%", "48%"],
                ["Volmageddon", "Managed", "0.2%", "&minus;21.2%", "18%"],
                ["Crash", "Hold", "&minus;5.4%", "&minus;62.3%", "54%"],
                ["Crash", "Managed", "0.5%", "&minus;34.2%", "24%"],
                ["Bear Grind", "Hold", "1.7%", "&minus;9.8%", "28%"],
                ["Bear Grind", "Managed", "0.9%", "&minus;6.0%", "27%"],
            ],
            col_widths=[0.18, 0.16, 0.16, 0.16, 0.16],
            footnote="All values as % of margin deployed. Model-contingent; see Appendix B for pilot chain cross-check.",
            heading="Scenario Comparison Summary",
    )
    add_table(story,
            ["Scenario", "Greek", "Mechanism", "Mgmt"],
            [
                ["Low-Vol Grind", "Theta", "Smooth θ; low γ/vega", "Adds friction"],
                ["Volmageddon", "Vega + Γ", "IV ↑ + spot move", "Exit cuts compound loss"],
                ["Crash", "Γ + Vega", "Gap + IV spike", "5th %ile ~−50%"],
                ["Bear Grind", "Δ + θ", "Slow drift; θ vs Δ", "Limited effect"],
            ],
            col_widths=[0.15, 0.13, 0.40, 0.32],
            footnote="[Derived] Attribution from dV expansion (Section 3.2). Approximate dominance.",
            heading="Greek Attribution of Scenario Outcomes",
    )
    story.append(
        P(
            "<b>Key findings (Monte Carlo only):</b> In low-vol environments, management adds friction without material "
            "risk reduction (P(Loss) increases from 5% to 13% due to mid-trade exits on noise). In volmageddon and "
            "crash scenarios, managed strategies tend to cut 5th percentile losses by approximately half. The bear grind "
            "shows minimal difference. "
            f"<b>Appendix B does not confirm the tail benefit:</b> with n = {_pilot_n()} paired entries, managed and hold share the "
            "same 5th percentile (&asymp; &minus;$56/contract), and Mar 2020 crisis cells show no managed advantage on "
            "median P&amp;L. Treat §21 as a stress narrative under fixed model assumptions until a larger chain sample "
            "is available (Future Work)."
        )
    )


def build_section_23(story):
    section(
        story,
        "sec23",
        "23. Unified Interpretation",
        lead="Final synthesis. The report progresses from theta mechanics (Sections 1&ndash;6) through evidence and "
        "risk (7&ndash;12), into the full Greek system (13&ndash;19), and concludes with operational rules (20), "
        "stress validation (21), and the master reference (22).",
    )
    story.append(
        P(
            "Theta decay is the entry point, not the whole story. Every finding in this report is a facet of a single "
            "governing equation&mdash;the stochastic Taylor expansion of option value&mdash;evaluated across moneyness, "
            "time, volatility regimes, and execution reality."
        )
    )
    formula_box(
        story,
        [
            "dV  &asymp;  &Delta;&middot;dS  +  &frac12;&Gamma;&middot;dS&sup2;  +  Vega&middot;d&sigma;  +  &theta;&middot;dt  +  cross terms (Vanna, Vomma, Charm)",
            "Short premium = long &theta; + short &Gamma; + short Vega &minus; VRP harvest &minus; costs &minus; tail events",
        ],
    )
    subsection(story, "23.1 Layered Framework", opening=_table_flowables(
            ["Layer", "Sections", "Question Answered"],
            [
                ["Mechanics", "1&ndash;6", "When and how does theta accrue?"],
                ["Evidence &amp; risk", "7&ndash;12", "Does the premium exist? What does tail risk look like?"],
                ["Greek system", "13&ndash;19", "How do Greeks interact, evolve, hedge, reprice, and execute?"],
                ["Operations", "20", "What rules translate theory into trades?"],
                ["Validation (MC)", "21", "Do rules survive stress regimes under simulation?"],
                ["Validation (pilot)", "App. B", "Do Section 20 rules behave plausibly on real chains?"],
                ["Reference", "22", "What is robust vs model-contingent?"],
            ],
            col_widths=[0.14, 0.16, 0.70],
    ))
    subsection(story, "23.2 Regime-Specific Guidance")
    bullets(
        story,
        [
            "<b>Low-vol grind (Sec. 8, 21):</b> Theta dominates; T* and exit rules optimize carry. Management adds friction; execution costs (Sec. 19) matter most.",
            "<b>Normal regime:</b> Theta and gamma balance. Section 20 rules (45 DTE, 50% profit, 21 DTE floor) appropriately limit gamma into expiry.",
            "<b>Elevated vol:</b> Vega and vanna rise (Sec. 13, 15). Size down (Sec. 20.4); monitor dynamic Greeks, not just entry snapshot.",
            "<b>Crisis:</b> Vega, vomma, and sticky-delta repricing (Sec. 17) overwhelm theta. Management rules earn their value; flat-vol BS scenarios understate losses.",
        ],
    )
    subsection(story, "23.3 Hedging vs Management")
    story.append(
        P(
            "Section 20 rules manage risk by <b>exiting</b> positions before Greek exposures become unstable. "
            "Section 16 manages risk by <b>overlaying</b> hedges that neutralize selected exposures. These are "
            "complementary, not interchangeable: delta hedging removes direction but leaves gamma and vega; "
            "exit rules cap all exposures but forgo remaining theta. The variance identity (Section 14) explains "
            "when each approach dominates&mdash;calm paths favor unhedged carry; volatile paths favor hedged gamma scalping."
        )
    )
    source(story, "Convention] Framework synthesis; quantitative hedging comparison in Section 16")
    formula_box(
        story,
        [
            "Theta is the carry component&mdash;the predictable income that motivates premium selling.",
            "Gamma is path risk. Vega is regime risk. Second-order Greeks are the acceleration of those risks.",
            "Surface dynamics, model choice, and execution determine whether theoretical edge survives contact with markets.",
            "Strategy selection, management rules, position sizing, and hedging overlays are all mechanisms for controlling the balance between these forces.",
        ],
    )


def build_section_13(story):
    section(
        story,
        "sec13",
        "13. Second-Order Greeks",
        lead="Beginning the applied Greek-system block (Sections 13&ndash;19). First-order Greeks describe "
        "instantaneous sensitivity; second-order Greeks describe how those sensitivities change.",
    )
    story.append(
        P(
            "The convexity and cross-effects that dominate during vol shocks, spot gaps, and the final weeks "
            "before expiry. For short premium positions, they explain why losses can accelerate nonlinearly even when "
            "first-order exposures appear manageable."
        )
    )
    add_table(
        story,
        ["Greek", "Definition", "Primary Role", "Short Premium Impact"],
        [
            ["Vomma", "d&sup2;V/d&sigma;&sup2;", "Convexity of value in IV", "IV spikes hurt more when vomma is large (short vega becomes more short)"],
            ["Vanna", "d&sup2;V/dS d&sigma;", "Delta response to vol; vega response to spot", "Spot moves re-rate delta during vol events; hedges drift"],
            ["Charm", "d&Delta;/dt", "Delta decay over time", "Unhedged delta creeps toward expiry; roll timing affects residual exposure"],
            ["Speed", "d&Gamma;/dS", "Gamma response to spot", "Near ATM, small spot moves rapidly change gamma (pin risk)"],
        ],
        col_widths=[0.10, 0.16, 0.30, 0.44],
    )
    source(story, "Derived] Standard Black-Scholes partial derivatives")
    fig_block(
        story,
        "fig_v5_greeks",
        "Figure 20: Second-order Greek profiles vs DTE for a representative OTM short put (S/K = 1.15, &sigma; = 80%). "
        "Vomma and vanna peak at intermediate DTE; charm and speed intensify into expiry.",
        title="13.1 Second-Order Profiles",
        lead="All four Greeks are material for the OTM short puts analyzed in Sections 4 and 20. Their DTE profiles "
        "explain why management rules (50% profit, 21 DTE exit) remove positions before second-order effects dominate.",
    )
    subsection(story, "13.2 Vomma and Volatility Convexity")
    story.append(
        P(
            "Vomma measures how vega itself changes with implied volatility. Short options with large negative vomma "
            "suffer accelerating losses during IV expansion: each vol point hurts more than the last. This is the "
            "mechanism behind the vega asymmetry noted in Section 3.2&mdash;theta accrues linearly in time, but vega "
            "losses compound through vomma during regime shifts."
        )
    )
    formula_box(
        story,
        [
            "Vomma = Vega &middot; d1 &middot; d2 / &sigma;",
            "Short premium: negative vega &times; positive vomma (OTM) &rarr; convex loss in IV",
        ],
    )
    subsection(story, "13.3 Vanna and Cross-Greek Interaction")
    story.append(
        P(
            "Vanna links spot and volatility. When IV rises as spot falls (typical equity skew), vanna amplifies "
            "delta losses on short puts: the position becomes more short delta precisely when the underlying is "
            "weakening. This cross-effect is absent from static Greek snapshots and motivates regime-aware sizing "
            "(Section 20.4)."
        )
    )
    subsection(story, "13.4 Charm, Speed, and Expiry Dynamics")
    story.append(
        P(
            "Charm (delta decay) drives the drift of unhedged delta toward its expiry limit. Speed governs how quickly "
            "gamma changes with spot&mdash;maximal near ATM into expiry, producing pin risk and the gamma scaling "
            "behavior in Section 3.4. Together, charm and speed explain why the 21 DTE exit removes positions before "
            "delta and gamma become unstable."
        )
    )
    formula_box(
        story,
        [
            "Near expiry: Speed &uarr; &rarr; small spot moves &rarr; large &Delta;&Gamma; changes",
            "Management implication: second-order Greeks peak where first-order theta is already declining (post-T*)",
        ],
    )


def build_section_14(story):
    section(story, "sec14", "14. Realized vs Implied Variance")
    story.append(
        P(
            "The variance risk premium (Section 1) is not only a difference in vol levels&mdash;it is a difference in "
            "the variance that gets integrated along the price path. Gamma P&amp;L is the mechanism that converts "
            "realized path variance into dollars, making the VRP tangible at the position level."
        )
    )
    subsection(story, "14.1 The Gamma–Variance Identity")
    story.append(
        P(
            "Summing the gamma term from the P&amp;L decomposition (Section 3.2) over a holding period yields the "
            "realized-vs-implied variance relationship:"
        )
    )
    formula_box(
        story,
        [
            "P&amp;L<sub>&gamma;</sub>  &asymp;  &frac12; &Gamma; S&sup2; &sum; ( &sigma;&sup2;<sub>realized</sub> &minus; &sigma;&sup2;<sub>implied</sub> ) &Delta;t",
            "Short premium wins when realized variance &lt; implied variance (path stays calm)",
            "Short premium loses when realized variance &gt; implied variance (path is volatile)",
        ],
    )
    source(story, "Derived] Discrete sum of &frac12;&Gamma;&middot;dS&sup2; with dS = S&sigma;&radic;&Delta;t&middot;Z")
    fig_block(
        story,
        "fig_var_premium",
        "Figure 21: Median gamma P&amp;L over 30 days for an ATM short put (&sigma;<sub>implied</sub> = 25%). "
        "Bars left of implied vol are favorable; bars right are unfavorable. Theta income is excluded to isolate the variance channel.",
        title="14.2 Simulation Evidence",
        lead="Monte Carlo paths at fixed implied vol isolate gamma P&amp;L by realized vol level. The crossover at "
        "implied vol confirms the structural identity: premium selling is a bet on realized variance falling short of "
        "implied variance.",
    )
    subsection(story, "14.3 Interaction with Theta and Vega")
    story.append(
        P(
            "Total P&amp;L is the sum of theta carry, gamma-variance realization, and vega re-pricing. In calm regimes "
            "(Section 8), theta exceeds gamma drag and the VRP is harvested. In crisis regimes, vega and gamma "
            "overwhelm theta regardless of entry timing. The T* framework optimizes theta capture; this framework "
            "optimizes understanding of when theta income is sufficient to compensate for variance risk."
        )
    )
    add_table(
        story,
        ["Component", "Favors Seller When", "Dominates In"],
        [
            ["&theta;&middot;dt", "Time passes; spot stable", "Low-vol, post-T* carry phases"],
            ["&frac12;&Gamma;&middot;dS&sup2;", "Realized vol &lt; implied vol", "Calm paths; low RV environments"],
            ["Vega&middot;d&sigma;", "IV contracts", "Vol mean-reversion after spikes"],
            ["Vomma / Vanna", "N/A (always convex/cross risk)", "Vol shocks with spot gaps (Section 13)"],
        ],
        col_widths=[0.18, 0.38, 0.44],
    )
    formula_box(
        story,
        [
            "Net edge  &asymp;  VRP (variance)  +  theta (time)  &minus;  transaction costs  &minus;  tail events",
            "Section 7 signals describe regime shifts where the variance term turns against sellers&mdash;not a standalone strategy.",
        ],
    )


def build_section_15(story):
    section(story, "sec15", "15. Dynamic Greek Evolution")
    story.append(
        P(
            "Greeks are not constants&mdash;they evolve with calendar time, spot moves, and vol repricing. A position "
            "entered with a static Greek snapshot can cross risk thresholds without any rule violation if spot or IV "
            "shift. This section maps how first-order exposures drift, connecting the T* framework (Section 3) to "
            "second-order effects (Section 13) and management rules (Section 20)."
        )
    )
    fig_block(
        story,
        "fig_greek_evolution",
        "Figure 22: Position Greeks vs DTE at three spot levels (S/K = 1.10, 1.00, 0.95). A spot decline toward "
        "the strike shifts the gamma and theta peaks earlier and amplifies delta drift via charm.",
        title="15.1 The Greek Clock",
        lead="At entry (S/K = 1.10), theta peaks at an intermediate DTE consistent with the decision matrix (Section 20.3). "
        "If spot falls to 0.95, the profile resembles a nearer-to-the-money position: gamma rises, theta peak moves "
        "earlier, and vega sensitivity increases.",
    )
    subsection(story, "15.2 Evolution Drivers")
    add_table(
        story,
        ["Driver", "Primary Effect", "Secondary Effect", "Management Link"],
        [
            ["Calendar time (&part;/&part;t)", "Theta accrual; charm drift", "Gamma &uarr; into expiry", "21 DTE floor (Sec. 20.2)"],
            ["Spot move (&part;/&part;S)", "Delta &amp; gamma repricing", "Vanna cross (Sec. 13.3)", "Recompute T*; peak-aware exit"],
            ["Vol move (&part;/&part;&sigma;)", "Vega MTM; vomma convexity", "Skew-dependent vanna", "Regime sizing (Sec. 20.4)"],
        ],
        col_widths=[0.18, 0.26, 0.26, 0.30],
    )
    subsection(story, "15.3 Static vs Dynamic Risk Assessment")
    story.append(
        P(
            "Entry-time Greeks answer &ldquo;what is my exposure today?&rdquo; Dynamic evolution answers &ldquo;what path "
            "could take me into gamma- or vega-dominated territory before my exit rule fires?&rdquo; The trade lifecycle "
            "example (Section 20.6) shows this gap: spot dropped below strike on day 16, but neither the profit target "
            "nor the DTE floor triggered an exit. A dynamic assessment would flag rising gamma and vanna as the spot "
            "approached the strike, even while theta remained positive."
        )
    )
    formula_box(
        story,
        [
            "Risk state  &ne;  entry Greeks",
            "Monitor: &Gamma;(t), charm drift, vanna under spot&ndash;vol joint moves",
            "Section 20 rules remain the operational baseline; this section explains when they lag the Greek surface",
        ],
    )


def build_section_16(story):
    section(story, "sec16", "16. Hedging Framework")
    story.append(
        P(
            "Hedging transforms the P&amp;L decomposition (Section 3.2) by neutralizing selected Greek exposures. "
            "It is an alternative to exit-based management (Section 20): rather than closing to reduce gamma, the "
            "position is overlaid with hedge instruments that absorb specific risks. Each hedge removes one exposure "
            "while leaving others intact."
        )
    )
    add_table(
        story,
        ["Hedge", "Neutralizes", "Leaves Exposed", "Typical Cost"],
        [
            ["Delta hedge (stock/futures)", "&Delta;&middot;dS", "Gamma, vega, theta", "Rebalance frequency; borrow/fees"],
            ["Gamma scalping", "Directional drift of &Delta;", "Vega, net gamma sign", "Bid-ask on hedge trades"],
            ["Vega hedge (calendar/diagonal)", "Vega&middot;d&sigma;", "Theta, term structure", "Calendar spread premium"],
            ["Tail hedge (OTM options)", "Left-tail gap risk", "Carry drag; theta bleed", "Option premium paid"],
        ],
        col_widths=[0.22, 0.18, 0.28, 0.32],
    )
    source(story, "Convention] Standard market practice; costs calibrated qualitatively")
    fig_block(
        story,
        "fig_hedging",
        "Figure 23: Single volatile path (RV &asymp; 38%). Unhedged short put P&amp;L swings with direction. "
        "Daily delta rebalancing removes directional component, isolating theta&ndash;gamma dynamics. "
        "Transaction costs excluded for clarity.",
        title="16.1 Delta Hedging in Practice",
        lead="On the simulated path, the unhedged position loses when spot falls toward the strike despite collecting theta. "
        "The delta-hedged overlay converts the same path into a smoother P&amp;L stream dominated by gamma-variance "
        "realization (Section 14) rather than directional delta.",
    )
    subsection(story, "16.2 Gamma Scalping")
    story.append(
        P(
            "Gamma scalping is the active management of a delta-hedged option book. Each rebalance trade captures "
            "&frac12;&Gamma;&middot;dS&sup2; from the hedge while paying bid-ask spread. The strategy profits when "
            "realized variance exceeds the implied variance embedded in the option price&mdash;the same condition that "
            "hurts unhedged short premium (Section 14). For short premium sellers who delta hedge, gamma scalping "
            "partially offsets gamma drag on volatile paths but cannot eliminate vega risk during IV spikes."
        )
    )
    formula_box(
        story,
        [
            "Gamma scalper P&amp;L  &asymp;  &frac12;&Gamma; S&sup2; (&sigma;&sup2;<sub>realized</sub> &minus; &sigma;&sup2;<sub>implied</sub>) &minus; hedge costs",
            "Short unhedged seller: same gamma term, plus full delta and vega exposure",
        ],
    )
    subsection(story, "16.3 Vega and Tail Overlays")
    story.append(
        P(
            "Vega hedging uses offsetting option positions (typically calendars or diagonals) to reduce sensitivity to "
            "parallel IV shifts. It does not hedge skew shocks or spot-vol correlation (vanna). Tail hedges (long OTM "
            "puts, put spreads) cap gap risk at the cost of persistent theta bleed. In crisis regimes (Section 8, "
            "In crisis regimes (Section 8, Section 21), vega and tail overlays tend to earn their cost; in low-vol grinds they drag returns."
        )
    )
    subsection(story, "16.4 Relationship to Section 20 Rules")
    story.append(
        P(
            "The Section 20 decision framework assumes unhedged management. With hedging overlays, several rules change character:"
        )
    )
    add_table(
        story,
        ["Sec. 20 Rule", "Unhedged Role", "With Hedge Overlay"],
        [
            ["50% profit target", "Lock theta; cut gamma tail", "Less critical if delta-neutral; vega may dominate exit"],
            ["21 DTE floor", "Exit before gamma spike", "Hedged books may hold; monitor speed/charm instead"],
            ["Peak-aware (T*)", "Close before theta declines", "Still relevant for carry optimization"],
            ["Regime sizing", "Cap tail exposure", "Hedge budget replaces part of size reduction"],
        ],
        col_widths=[0.18, 0.38, 0.44],
    )
    story.append(
        P(
            "<b>Recommendation:</b> Treat Section 20 as the unhedged baseline. Sections 15&ndash;16 provide the Greek "
            "machinery to design hedge-aware variants. Section 22 indexes which findings survive model and execution stress."
        )
    )


def build_section_17(story):
    section(story, "sec17", "17. Volatility Surface Dynamics")
    story.append(
        P(
            "Section 6 introduced skew and term structure as static features. In live markets, the surface also "
            "<b>moves</b> when spot changes&mdash;and the movement convention (sticky strike vs sticky delta) determines "
            "how vega and vanna reprice a position. This is the bridge between the skew tables in Section 6 and the "
            "vanna analysis in Section 13."
        )
    )
    subsection(
        story,
        "17.1 Sticky Strike vs Sticky Delta",
        opening=(
            [
                P(
                    "<b>Sticky strike:</b> implied volatility at each strike K remains fixed when spot moves. "
                    "<b>Sticky delta:</b> implied volatility at each delta level remains fixed; as spot moves, the surface "
                    "shifts so that the IV associated with a given moneyness/delta follows the spot. Equity index markets "
                    "typically behave closer to sticky delta in the short term, especially during selloffs."
                )
            ],
            0.55 * inch,
        ),
    )
    fig_flows, fig_h = _fig_flowables(
        "fig_surface_sticky",
        "Figure 24: Skew surface at two spot levels (left) and short 95P P&amp;L after a $110&rarr;$100 drop (right). "
        "Sticky delta amplifies MTM loss vs sticky strike.",
        lead="For short puts, sticky delta is the adverse convention: spot declines raise the relevant IV just as the "
        "position becomes more sensitive to further declines (vanna cross, Section 13.3). Flat-vol BS models miss this "
        "joint spot&ndash;vol movement entirely.",
    )
    tbl_flows, tbl_h = _table_flowables(
        ["Convention", "When Spot Falls", "IV at Short Put Strike", "Impact on Short Premium"],
        [
            ["Sticky strike", "Strike IV unchanged", "Fixed", "Vega loss from level only"],
            ["Sticky delta", "Surface shifts with spot", "Rises as put &rarr; ATM", "Vega + vanna compound loss"],
            ["Flat BS (this report default)", "IV constant everywhere", "Fixed", "Underestimates crisis MTM"],
        ],
        col_widths=[0.18, 0.22, 0.22, 0.38],
    )
    subsection(
        story,
        "17.2 Surface Repricing and Short Premium",
        opening=(fig_flows + tbl_flows, fig_h + tbl_h),
    )
    subsection(story, "17.3 Local Vol vs Stochastic Vol")
    story.append(
        P(
            "<b>Local volatility</b> models (Dupire 1994) fit the current surface exactly and imply sticky strike "
            "dynamics in the short run. <b>Stochastic volatility</b> models (Heston 1993) generate smile through "
            "vol-of-vol and spot&ndash;vol correlation (&rho; &lt; 0 for equity), producing sticky-delta-like behavior "
            "and richer tail dynamics. Neither is used for pricing in this report; both inform model risk (Section 18)."
        )
    )
    formula_box(
        story,
        [
            "Sticky delta + &rho; &lt; 0  &rarr;  spot&darr; implies IV&uparrow; at fixed strike",
            "Implication: crisis vega losses exceed flat-vol BS projections (Section 21 scenarios)",
        ],
    )


def build_section_18(story):
    section(story, "sec18", "18. Model Risk")
    story.append(
        P(
            "Every result in this report is conditional on the pricing model. Black-Scholes provides analytical clarity; "
            "Merton adds jump risk; stochastic-vol models add smile dynamics and spot&ndash;vol correlation. Model risk "
            "is the sensitivity of conclusions&mdash;especially T*, peak theta, and scenario losses&mdash;to these choices."
        )
    )
    fig_block(
        story,
        "fig_model_risk",
        "Figure 25: Left: daily theta vs DTE for BS, Merton, and stoch-vol-adjusted pricing. Right: peak theta magnitude. "
        "Merton raises OTM theta via jump premium; stoch-vol adjustment raises theta further via skew.",
        title="18.1 Model Comparison: Theta Profiles",
        lead="The T* framework (Section 3.1) is robust within BS but its quantitative predictions shift under alternative "
        "models. Rankings (OTM &gt; ATM theta per unit risk) tend to survive; magnitudes and peak timing do not.",
    )
    add_table(
        story,
        ["Model", "Strengths", "Weaknesses", "Use When"],
        [
            ["Black-Scholes", "Analytical T*; fast MC", "Flat vol; no jumps; no smile dynamics", "Baseline; OTM &gt; 30 DTE"],
            ["Merton jumps", "Event risk; fat tails", "Symmetric jumps; no smile", "Earnings; gap risk (Sec. 11)"],
            ["Kou double-exp", "Asymmetric jumps", "More params; harder to calibrate", "Equity tails; better fit than Merton"],
            ["Heston stoch vol", "Smile; &rho;; vol clustering", "No closed-form; calibration heavy", "Surface dynamics; crisis repricing"],
        ],
        col_widths=[0.14, 0.24, 0.28, 0.34],
    )
    source(story, "Calibrated] Ramezani &amp; Zeng (2007); Kou (2002) for jump models")
    subsection(story, "18.2 What Transfers Across Models")
    bullets(
        story,
        [
            "<b>Robust:</b> OTM theta peaks before expiry; gamma&ndash;theta duality; short premium = short gamma + short vega.",
            "<b>Model-contingent:</b> T* in calendar days; peak theta magnitude; skew-adjusted OTM advantage (20&ndash;40%).",
            "<b>Model-sensitive:</b> Crisis scenario 5th percentile (Section 21); vega loss during spot&ndash;vol joint moves.",
        ],
    )
    subsection(story, "18.3 Model Selection Guide", opening=_table_flowables(
            ["Question", "Recommended Model", "Report Section"],
            [
                ["When does OTM theta peak?", "BS (analytical T*)", "3.1, 20.3"],
                ["How much theta under skew?", "Per-leg IV (skew-adjusted BS)", "6.1"],
                ["Earnings / gap risk?", "Merton or Kou", "11"],
                ["Spot drop + IV spike together?", "Stoch vol / sticky delta", "17, 21"],
                ["Net edge after costs?", "BS MC + cost overlay", "9, 12"],
            ],
            col_widths=[0.30, 0.34, 0.36],
    ))


def build_section_19(story):
    section(story, "sec19", "19. Execution Microstructure")
    story.append(
        P(
            "Theoretical theta and Greek analysis assume frictionless execution at mid-market. Real trading introduces "
            "bid&ndash;ask spreads, partial fills, leg risk on multi-leg structures, and early assignment on American "
            "options. Section 9 quantified average costs; this section addresses how execution quality varies with "
            "moneyness, stress, and structure complexity."
        )
    )
    fig_block(
        story,
        "fig_execution",
        "Figure 26: Left: effective half-spread by moneyness (Muravyev &amp; Pearson 2020 calibration). "
        "Right: spread widening multiplier vs VIX (Cao et al. 2024 pattern). OTM and crisis conditions degrade execution.",
        title="19.1 Bid-Ask Dynamics",
        lead="Far OTM options&mdash;often favored for Sharpe ratio (Section 12.4)&mdash;carry the widest spreads. "
        "During stress, spreads widen nonlinearly, eroding the advantage of management rules that require frequent exits.",
    )
    add_table(
        story,
        ["Execution Factor", "Mechanism", "Impact on Theta Harvesting", "Mitigation"],
        [
            ["Wide OTM spreads", "Thin premium; market maker inventory risk", "7%+ round-trip on cheap options", "Trade liquid names; use spreads"],
            ["Stress widening", "MMs pull quotes in vol spikes", "Exit rules fire at worst fills", "GTC limits; avoid market orders"],
            ["Partial fills", "Multi-leg asymmetry", "Unintended Greek exposure", "All-or-none; legging risk limits"],
            ["Early assignment", "American calls on dividends", "Sudden delta/gamma jump", "Close before ex-div; monitor deep ITM"],
            ["Capacity", "Size vs OI / ADV", "Slippage scales nonlinearly", "Cap per strike; diversify expiries"],
        ],
        col_widths=[0.16, 0.26, 0.30, 0.28],
    )
    source(story, "Calibrated] Muravyev &amp; Pearson (2020); Cao et al. (2024)")
    subsection(story, "19.2 Interaction with Sections 9 and 20")
    story.append(
        P(
            "Section 9 showed that retail round-trip costs of approximately 7% on a $3 premium consume a meaningful "
            "fraction of a 50% profit target. Execution microstructure amplifies this for OTM positions and during "
            "the crisis regimes where Section 20 exit rules are most valuable. A complete net-edge calculation requires "
            "both the average cost table (Section 9) and the moneyness/stress adjustments shown here."
        )
    )
    formula_box(
        story,
        [
            "Net edge  &asymp;  theta + VRP  &minus;  &frac12;spread &times; turnover  &minus;  slippage(VIX, moneyness)",
            "Turnover rises with active management (50% target, 21 DTE floor) and with hedging (Section 16)",
        ],
    )
    subsection(story, "19.3 Capacity and Liquidity")
    story.append(
        P(
            "Capacity constraints are not modeled quantitatively in this report. Qualitatively: SPX/SPY options at "
            "standard strikes and 30&ndash;60 DTE support institutional size; single-name OTM options at &gt; 1.20 "
            "moneyness may not. Rolling concentrated positions near expiry competes with market maker gamma hedging "
            "flows, widening spreads precisely when Section 3.4 gamma scaling peaks."
        )
    )


def build_appendix(story):
    section(story, "secA", "Appendix A: Methodology")
    subsection(story, "A.1 Pricing Model")
    story.append(
        P(
            "All options are priced using Black-Scholes (1973) for European options. The Merton (1976) jump-diffusion "
            "extension is used for event-exposed positions only (Section 11). Surface dynamics (Section 17) and "
            "stochastic-vol models (Section 18) are discussed for interpretation but not used in simulations."
        )
    )
    subsection(story, "A.2 Monte Carlo Process")
    story.append(
        P(
            "Price paths follow geometric Brownian motion with dt = 1/252. Jump-diffusion scenarios add Poisson-distributed jumps. "
            "All simulations use numpy's Mersenne Twister PRNG with fixed seeds."
        )
    )
    subsection(story, "A.3 Path Counts and Convergence", opening=_table_flowables(
            ["Analysis", "Paths", "Bootstrap", "Rationale"],
            [
                ["Regime analysis", "1,500/regime", "None", "Sufficient for median + IQR"],
                ["Parameter sweep", "400/cell", "None", "Grid has 28 cells; total 11,200"],
                ["DTE curves", "300/DTE", "100/point", "CI width approximately &plusmn;0.15 SR"],
                ["Benchmarks", "500/strategy", "None", "Directional ranking stable"],
                ["Case studies", "500/scenario", "None", "Distribution shape reliable"],
            ],
            col_widths=[0.24, 0.18, 0.18, 0.40],
    ))
    subsection(
        story,
        "A.4 Fee and Cost Assumptions",
        opening=(
            [
                P(
                    "Transaction costs use the Muravyev &amp; Pearson (2020) effective half-spread framework. "
                    "Three tiers: retail (3%, $0.65/contract), active retail (2%, $0.50), institutional (1%, $0.10)."
                )
            ],
            0.45 * inch,
        ),
    )
    subsection(story, "A.5 Variance Risk Premium")
    story.append(
        P(
            "Default VRP is IV = 25%, RV = 18%, representing a 7-percentage-point premium. "
            "Results are sensitive to VRP magnitude."
        )
    )
    subsection(story, "A.6 Limitations")
    story.append(
        P(
            "Simulations assume constant implied volatility (unless noted in Section 17), no bid-ask widening during stress "
            "(Section 19 quantifies but does not embed), no margin calls, no dividend events, and no early assignment. "
            "Hedging (Section 16) and stoch-vol dynamics (Section 18) are illustrative. These limitations collectively "
            "create an optimistic bias in unhedged, BS-based results. Historical pilot limitations are listed in Appendix B."
        )
    )


def build_appendix_b(story):
    v6 = load_v6_summary()
    section(
        story,
        "secB",
        "Appendix B: Historical Validation (Pilot)",
        lead="Pilot backtest of Section 20 rules on real SPY put chains from Databento OPRA.PILLAR. "
        "<b>Directional only</b>&mdash;not a substitute for the Monte Carlo validation in Sections 12 and 21.",
    )
    story.append(
        P(
            "This appendix documents what could be validated with available data as of v6.1. It does not upgrade "
            "simulation-supported findings to empirical certainty. Section 7 surface signals are out of scope."
        )
    )
    story.append(
        P(
            "<b>Pre-specification note:</b> Section 20 rules were fixed before the pilot run; parameters match "
            "B.2 below and the engine in <i>scripts/backtest_managed_put.py</i>. No in-sample tuning was performed."
        )
    )
    subsection(story, "B.1 Data and Scope")
    add_table(
        story,
        ["Item", "Detail"],
        [
            ["Dataset", "Databento OPRA.PILLAR, parent symbol SPY.OPT"],
            ["Schemas", "definition, statistics, cbbo-1m (EOD NBBO marks)"],
            ["Months", "Mar 2020; Jan/Mar/Jun/Aug/Oct 2022; Jan/Mar 2023 (8 non-contiguous blocks)"],
            ["Sessions", "84 trading days across four non-contiguous blocks"],
            ["Underlying / VIX", "SPY close (Yahoo); VIXCLS (FRED) for regime tags"],
            ["Cost", "~$50 historical platform fees (four monthly pulls)"],
        ],
        col_widths=[0.22, 0.78],
    )
    subsection(story, "B.2 Backtest Specification")
    add_table(
        story,
        ["Parameter", "Value", "Report ref."],
        [
            ["Structure", "Short SPY put", "Section 20"],
            ["Entry", "Weekly (Fridays); 40&ndash;50 DTE target", "Section 20.1"],
            ["Moneyness", "S/K &isin; [1.05, 1.15]", "Section 12.4 / spec"],
            ["Profit exit", "50% of entry premium", "Section 20.2"],
            ["Time exit", "DTE &le; 21", "Section 20.2"],
            ["Benchmark", "Hold to last mark in sample", "Section 21"],
            ["Costs", "Half-spread at entry/exit + $0.65/leg commission", "Section 9"],
        ],
        col_widths=[0.22, 0.38, 0.40],
    )
    if v6:
        dr = v6["date_range"]
        bs = v6["by_strategy"]
        hold = bs["hold"]
        mgd = bs["managed"]
        subsection(story, "B.3 Results Summary")
        med_h = hold.get("median_pnl_net_ci", {})
        med_m = mgd.get("median_pnl_net_ci", {})
        p05_h = hold.get("p05_pnl_net_ci", {})
        p05_m = mgd.get("p05_pnl_net_ci", {})
        story.append(
            P(
                f"<b>{v6['n_entries']} weekly entries</b> ({v6['n_trades']} trade rows including managed/hold pairs), "
                f"{dr['start']} through {dr['end']}. With n = {v6['n_entries']}, bootstrap 95% confidence intervals are wide; "
                "Sharpe ratios are unstable. Phase 1 acceptance target remains &ge;150 entries (Future Work)."
            )
        )
        add_table(
            story,
            ["Strategy", "n", "Median net P&amp;L", "5th %ile", "95th %ile", "Win %"],
            [
                [
                    "Hold",
                    str(hold["count"]),
                    _usd(hold["median_pnl_net"]) + _ci_band(med_h),
                    _usd(hold["p05_pnl_net"]) + _ci_band(p05_h),
                    _usd(hold["p95_pnl_net"]),
                    _pct100(hold["win_rate"]),
                ],
                [
                    "Managed",
                    str(mgd["count"]),
                    _usd(mgd["median_pnl_net"]) + _ci_band(med_m),
                    _usd(mgd["p05_pnl_net"]) + _ci_band(p05_m),
                    _usd(mgd["p95_pnl_net"]),
                    _pct100(mgd["win_rate"]),
                ],
            ],
            col_widths=[0.14, 0.06, 0.28, 0.22, 0.14, 0.10],
            footnote="95% CIs from 10,000 bootstrap resamples of trade-level P&amp;L. Pilot sample; not inferential.",
        )
        diff = v6.get("managed_minus_hold", {})
        if diff:
            dci = diff.get("median_diff_ci", {})
            story.append(
                P(
                    f"<b>Managed &minus; hold (paired):</b> median {_usd(diff.get('median_diff'))} per contract"
                    f"{_ci_band(dci)} across {diff.get('count', 0)} entry weeks. "
                    "A positive median favors management on this sample; overlapping CIs with zero imply no significant edge."
                )
            )
        regime_rows = []
        for regime, block in v6.get("by_regime", {}).items():
            h = block.get("hold", {})
            m = block.get("managed", {})
            regime_rows.append(
                [
                    regime.title(),
                    str(block.get("count", 0) // 2),
                    _usd(m.get("median_pnl_net")),
                    _usd(h.get("median_pnl_net")),
                    _usd(m.get("p05_pnl_net")),
                    _usd(h.get("p05_pnl_net")),
                ]
            )
        add_table(
            story,
            ["Regime (VIX bin)", "n", "Managed median", "Hold median", "Managed 5th %ile", "Hold 5th %ile"],
            regime_rows,
            col_widths=[0.16, 0.06, 0.18, 0.18, 0.18, 0.18],
            footnote="Regime tags from Section 8 VIX bins. Crisis = Mar 2020 week; small cell counts.",
            heading="Regime Breakdown (Pilot)",
        )
        if (CHARTS / "fig_v6_pilot.png").is_file():
            fig_block(
                story,
                "fig_v6_pilot",
                "Figure E: Median net P&amp;L by VIX regime &mdash; pilot SPY chain backtest (managed vs hold).",
            )
        subsection(story, "B.4 Pilot vs Monte Carlo (Section 21)")
        story.append(
            P(
                "<b>Agreement (directional):</b> Elevated/normal months can show positive median P&amp;L for short OTM puts "
                "after spread-aware costs. "
                "<b>Divergence (important):</b> Section 21 MC claims managed strategies cut crisis 5th-percentile losses "
                "by roughly half; the pilot does <b>not</b> replicate this&mdash;managed and hold share the same 5th %ile "
                f"on n = {v6['n_entries']}, and Mar 2020 crisis cells show higher median P&amp;L for hold than managed. "
                "Do not treat §21 tail-benefit claims as empirically supported until sample size and cross-month carry improve."
            )
        )
    else:
        subsection(story, "B.3 Results Summary")
        story.append(P("No v6 summary found. Run the Databento pipeline and rebuild the report."))
    subsection(story, "B.5 Limitations")
    bullets(
        story,
        [
            f"<b>Sample size:</b> {v6['n_entries']} entries vs &ge;150 Phase 1 target; confidence intervals are wide.",
            "<b>Non-contiguous months:</b> Open positions close on month-end marks (<i>last_mark</i>) rather than true exits.",
            "<b>American exercise:</b> SPY puts are American; engine uses European EOD marks.",
            "<b>IV rank filter:</b> Section 20 IV Rank &gt; 50% rule not applied (no historical IV rank series in pilot).",
            "<b>Sticky surface:</b> EOD marks miss intraday spot&ndash;vol joint moves (Section 17).",
            "<b>Survivorship:</b> Point-in-time definitions used, but liquidity filters may exclude delisted illiquid strikes.",
        ],
    )
    source(story, "Calibrated] Databento OPRA.PILLAR pulls; pipeline in project scripts/; spec in Databento_v6_Spec.md")


def build_future_work(story):
    section(
        story,
        "secFW",
        "Future Work",
        lead="Items required to move from pilot chain validation to publication-grade empirical results.",
    )
    add_table(
        story,
        ["Priority", "Work item", "Unlocks"],
        [
            [
                "P0",
                "Expand OPRA pulls to &ge;150 weekly entries (contiguous block preferred, e.g. 2022 full year)",
                "Phase 1 acceptance; replace Figure D with real CDFs",
            ],
            [
                "P0",
                "Cross-month position carry (fix month-end last_mark exits)",
                "Realistic managed vs hold comparison",
            ],
            [
                "P1",
                "Replace Section 12.1 DTE sweep with chain-based sweep",
                "Empirical DTE &times; profit target surface",
            ],
            [
                "P1",
                "Historical IV rank series for Section 20 IV filter",
                "Full rule-set fidelity",
            ],
            [
                "P2",
                "SPX/SPXW chain comparison",
                "Index-settled vs ETF-settled validation",
            ],
            [
                "P2",
                "Hedged backtest variant (Section 16 overlays)",
                "Management vs hedging tradeoff on real paths",
            ],
            [
                "P3",
                "Section 7 signal test on historical surfaces",
                "Separate signal validation from management rules",
            ],
            [
                "P3",
                "Out-of-sample split (train &le; 2021, test &ge; 2022)",
                "Overfit control for rule parameters",
            ],
        ],
        col_widths=[0.08, 0.52, 0.40],
        footnote="Cost estimate: ~$12/month per schema bundle (cbbo-1m + definition + statistics) for SPY.OPT parent pull.",
    )
    story.append(
        P(
            "Until P0 items are complete, Monte Carlo results in Sections 12 and 21 remain the primary quantitative "
            "framework. Appendix B should be read as a feasibility check, not confirmation of simulated magnitudes."
        )
    )


def build_references(story):
    section(story, "secR", "References")
    refs = [
        "Black, F. &amp; Scholes, M. (1973). The pricing of options and corporate liabilities. <i>J. Political Economy</i>, 81(3), 637&ndash;654.",
        "Bollerslev, T., Tauchen, G. &amp; Zhou, H. (2009). Expected stock returns and variance risk premia. <i>Rev. Financial Studies</i>, 22(11), 4463&ndash;4492.",
        "Cao, J., Jacobs, K. &amp; Ke, S. (2024). Derivative spreads: Evidence from SPX options. Working paper.",
        "Carr, P. &amp; Wu, L. (2009). Variance risk premiums. <i>Rev. Financial Studies</i>, 22(3), 1311&ndash;1341.",
        "CME Group. Option Greeks: Theta. CME Education Series.",
        "Dew-Becker, I. (2023). The decline of the variance risk premium. Working paper, Northwestern.",
        "Dupire, B. (1994). Pricing with a smile. <i>Risk Magazine</i>, 7(1), 18&ndash;20.",
        "Emery, D.R., Guo, W. &amp; Su, T. (2008). A closer look at Black&ndash;Scholes option thetas. <i>J. Econ. &amp; Finance</i>, 32(1), 59&ndash;74.",
        "Gatheral, J. (2006). <i>The Volatility Surface: A Practitioner&rsquo;s Guide</i>. Wiley.",
        "Heston, S.L. (1993). A closed-form solution for options with stochastic volatility. <i>Rev. Financial Studies</i>, 6(2), 327&ndash;343.",
        "Kou, S.G. (2002). A jump-diffusion model for option pricing. <i>Management Science</i>, 48(8), 1086&ndash;1101.",
        "Merton, R.C. (1976). Option pricing when underlying stock returns are discontinuous. <i>J. Financial Economics</i>, 3(1&ndash;2), 125&ndash;144.",
        "Muravyev, D. &amp; Pearson, N.D. (2020). Options trading costs are lower than you think. <i>Rev. Financial Studies</i>, 33(11), 4973&ndash;5014.",
        "Ramezani, C.A. &amp; Zeng, Y. (2007). Maximum likelihood estimation of the double exponential jump-diffusion. <i>Annals of Finance</i>, 3(4), 487&ndash;507.",
        "tastylive Research Team. 45 DTE and trade management studies. Various publications, tastylive.com.",
    ]
    for ref in refs:
        story.append(P(ref, "Ref"))


_ORPHAN_HEADING = re.compile(
    r"^("
    r"\d+\.\d+\s+\S|"  # 13.3 Decision Matrix
    r"\d+\.\s+[A-Z]|"  # 1. Introduction (section at page bottom — rare)
    r"[A-Z]\.\d+\s+\S|"  # A.3 Path Counts
    r"Appendix\s+[A-Z]:|"
    r"Evidence Map|"
    r"Future Work|"
    r"Historical Validation|"  # Appendix A:
    r"Scenario Comparison Summary|"
    r"Greek Attribution of Scenario Outcomes|"
    r"Quick Reference:|"
    r"Core Risk Metrics|"
    r"Recovery & Clustering Metrics|"
    r"Regime-Conditioned Risk|"
    r"Regime-Based Greek Dominance|"
    r"Signal Frequency and Sample Sizes|"
    r"Individual Signal Results"
    r")"
)


def scan_orphaned_headers(pdf_path: Path) -> list[tuple[int, str]]:
    """Flag pages whose last text line looks like a heading stranded from its body."""
    from pypdf import PdfReader

    orphans: list[tuple[int, str]] = []
    reader = PdfReader(str(pdf_path))
    skip_pages = {1, 2}  # title + TOC
    for idx, page in enumerate(reader.pages, start=1):
        if idx in skip_pages:
            continue
        lines = [ln.strip() for ln in (page.extract_text() or "").splitlines() if ln.strip()]
        if not lines:
            continue
        last = lines[-1]
        if _ORPHAN_HEADING.match(last):
            # Heading at the top of a page with content below is fine.
            if last == lines[0] and len(lines) > 1:
                continue
            orphans.append((idx, last))
    return orphans


def build_story(page_map: dict[str, int] | None = None):
    story = []
    add_title_page(story)
    add_toc(story, page_map)
    build_section_1(story)
    build_section_2(story)
    build_section_3(story)
    build_section_4(story)
    build_section_5(story)
    build_section_6(story)
    build_section_7(story)
    build_section_8(story)
    build_section_9(story)
    build_section_10(story)
    build_section_11(story)
    build_section_12(story)
    build_section_13(story)
    build_section_14(story)
    build_section_15(story)
    build_section_16(story)
    build_section_17(story)
    build_section_18(story)
    build_section_19(story)
    build_section_20(story)
    build_section_21(story)
    build_section_22(story)
    build_section_23(story)
    build_appendix(story)
    build_appendix_b(story)
    build_future_work(story)
    build_references(story)
    return story


def main():
    if not CHARTS.exists():
        raise SystemExit(f"Missing chart directory: {CHARTS}. Run generate_all_charts.py first.")
    doc_kwargs = dict(
        pagesize=letter,
        leftMargin=MARGIN_LR,
        rightMargin=MARGIN_LR,
        topMargin=MARGIN_TB,
        bottomMargin=MARGIN_TB,
        title="Theta Decay Dynamics",
        author="Theta Decay Dynamics Report",
    )

    # Pass 1: collect section page numbers for the table of contents.
    probe = io.BytesIO()
    probe_doc = BookmarkedDocTemplate(probe, **doc_kwargs)
    probe_doc.build(build_story())
    page_map = probe_doc.page_map

    # Pass 2: render TOC with dot leaders and page numbers.
    doc = BookmarkedDocTemplate(str(OUT_PDF), **doc_kwargs)
    doc.build(build_story(page_map))
    orphans = scan_orphaned_headers(OUT_PDF)
    if orphans:
        print("WARNING: possible orphaned headers detected:")
        for page_num, label in orphans:
            print(f"  page {page_num}: {label}")
    else:
        print("Orphan header scan: OK (0 issues)")
    print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
