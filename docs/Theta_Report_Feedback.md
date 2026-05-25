# Theta Decay Dynamics v4.4 — Layout Debug Patch (Tables, Bleedover, Orphans)

## Objective

Fix **remaining high-friction layout defects**:

* Column/text bleedover
* Tables breaking across pages incorrectly
* Orphaned headers or partial tables
* Misaligned multi-column structures

This is a **surgical pass**, not a full redesign.

---

# 1. Column Bleedover (CRITICAL)

## 1.1 Root Cause

Bleedover is occurring due to:

* Unbounded column widths
* Long strings without wrap control
* Mixed content types (text + numbers) in same column
* PDF rendering engine not respecting soft wraps

---

## 1.2 Where It’s Happening (Confirmed Patterns)

### A. Section 2.1 Notation Table

* “Units / Domain” column wraps inconsistently
* Long expressions (e.g., derivatives) push into margins

### B. Section 7 Tables (Signal + Forward Returns)

* “Interpretation” column overflows
* Multi-line text compresses adjacent columns

### C. Section 10.1 Risk Metrics Table

* Dense numeric + text mix causing horizontal pressure
* “Max Recovery (trades)” column especially unstable

### D. Section 13.5 Failure Modes Table

* **Worst offender**
* Long “Failure Condition” + “Mitigation” text forces bleed

---

## 1.3 Required Fix (MANDATORY)

### Enforce Column Constraints

For ALL tables:

* Convert to fixed layout:

  * `table-layout: fixed` (HTML)
  * or explicit width percentages (LaTeX/Markdown engine)

### Apply Width Rules:

* Narrow columns (numbers): 10–12%
* Medium columns: 15–20%
* Text-heavy columns: 25–40%

---

## 1.4 Text Wrapping Fix

### Force wrapping:

* Enable:

  * `word-break: break-word`
  * `white-space: normal`

### For long math/expressions:

* Allow line breaking at:

  * commas
  * operators
  * parentheses

---

## 1.5 Content Refactor (IMPORTANT)

Where wrapping fails, **shorten content structurally**:

### Replace:

“Prolonged downtrend; spot grinds through strike”

### With:

“Downtrend → strike breach”

This is REQUIRED in:

* Section 7
* Section 10 tables
* Section 13.5 (major cleanup)

---

# 2. Orphaned Table Issue (CRITICAL)

## 2.1 Confirmed Problem

A table is being:

* Split across pages
* Header separated from body
* Or single rows pushed to next page

### Likely Locations:

* Section 10.1 (Risk Metrics)
* Section 13.5 (Failure Modes)
* Section 7 (Signal tables)

---

## 2.2 Required Fix

### HARD RULE:

> A table must NEVER break mid-structure without header repetition.

---

## 2.3 Implementation Options

### Option A (Preferred)

Enable:

* “Repeat header on each page”

### Option B

If table is too large:

* Split into logical chunks:

#### Example:

Instead of one table:

* “Failure Modes (Entry/Structure)”
* “Failure Modes (Management Rules)”

---

## 2.4 Prevent Orphan Headers

### Enforce:

* Minimum 3 rows must follow a header
* If not → push entire table to next page

---

## 2.5 Keep Tables Atomic

Apply:

* `page-break-inside: avoid`

To:

* All tables
* Table containers

---

# 3. Row Height & Vertical Compression

## Problem:

Rows are:

* Too tight in dense tables
* Too tall in sparse ones

---

## Fix:

### Standardize:

* Min row height: ~1.2–1.4 line height
* Add:

  * 4–6px vertical padding

---

## Special Case:

Section 10.1:

* Increase spacing for readability
* This is a **high-cognitive-load table**

---

# 4. Multi-Line Cell Instability

## Problem:

Cells with line breaks:

* Expand unpredictably
* Misalign adjacent rows

---

## Fix:

### Normalize:

* Avoid manual line breaks inside cells
* Let renderer wrap naturally

### If needed:

* Convert multi-line cells → bullet-style inline:

  * “Condition: … | Signal: … | Action: …”

---

# 5. Table-Specific Fix Instructions

## 5.1 Section 7 Tables

* Reduce text verbosity by ~30%
* Convert interpretation column → shorter phrases
* Consider moving notes below table

---

## 5.2 Section 10.1 (HIGH PRIORITY)

### Issues:

* Width pressure
* Readability collapse
* Potential orphaning

### Fix:

* Split into:

  1. “Core Risk Metrics”
  2. “Recovery & Clustering Metrics”

---

## 5.3 Section 13.5 (CRITICAL)

### Current State:

* Too wide
* Too verbose
* High bleed risk

### REQUIRED:

Convert from table → structured blocks OR compressed table:

#### Option A (Preferred):

Bullet blocks per component

#### Option B:

4-column compressed table:

* Component
* Failure Trigger
* Signal
* Action

---

# 6. Global Table Styling (Consistency Pass)

Apply to ALL tables:

* Header:

  * Bold
  * Slightly larger font
* Rows:

  * Uniform padding
* Alignment:

  * Numbers → right
  * Text → left
* Optional:

  * Light zebra striping

---

# 7. Final Validation Checklist (STRICT)

Before export:

* [ ] No horizontal scroll required anywhere
* [ ] No text touches page margins
* [ ] No table split without header repetition
* [ ] No single-row orphan on new page
* [ ] All columns aligned cleanly
* [ ] No overlapping text
* [ ] Tables readable at 100% zoom (no zoom required)

---

# 8. Execution Priority

## Phase 1 (Critical)

* Section 13.5 fix
* Section 10.1 split
* Apply table width constraints globally

## Phase 2

* Section 7 cleanup
* Wrapping + overflow fixes

## Phase 3

* Styling + spacing normalization

---

# Final Instruction

This pass is about eliminating:

> “subtle layout friction that signals non-professional output”

The document should feel:

* Structurally stable
* Visually controlled
* Free of rendering artifacts

If a table cannot be made clean:

> **Reduce it or restructure it. Do not force it to fit.**

---