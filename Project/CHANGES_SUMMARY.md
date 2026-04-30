# Changes Summary: Report Formatting & Naming Updates

## Changes Implemented

### 1. Quantity Display for Fractional Values
**Files Modified:** 
- `modules/menu/report_viewers.py` (both detailed and summary report formatters)

**Change:**
Modified the `_fmt_qty_unit()` function in both `_format_detailed_report_text()` and `_format_summary_report_text()` to display small non-zero quantities with two-decimal formatting instead of `"< 1"` or `"0"`.

**Behavior:**
- **For 'ea' (each) units:**
  - Qty = 0.5 ea → displays as `"0.50 ea"`
  - Qty = 0 ea → displays as `"0 ea"`
  - Qty = 1.5 ea → displays as `"2 ea"` (rounded as before)

- **For 'kg' (weight) units:**
  - Qty = 0.0005 kg → displays as `"0.50 g"` (decimal grams)
  - Qty = 0.5 kg → displays as `"500 g"` (converted to grams)
  - Qty = 1.5 kg → displays as `"1.50 kg"`

**Rationale:** Prevents misleading report displays where average quantities are rounded to 0 when they're actually > 0, while providing a consistent, readable numeric format for small values.

### 2. Report Filename Renaming
**Files Modified:**
- `modules/menu/report_exports.py`
- `tests/test_report_exports.py`
- `Documentation/reports_menu.md`

**Changes:**
Global replacement of report name stems:
- `Audit_report` → `Sales_record`
- `Insight_report` → `Sales_trends`
- `Inactivity_report` → `Inactivity_report` (unchanged)

**Example Filenames (Before → After):**
- `Audit_report_pdf_11apr2026_12-44.pdf` → `Sales_record_pdf_11apr2026_12-44.pdf`
- `Audit_report_xlsx_11apr2026_12-44.xlsx` → `Sales_record_xlsx_11apr2026_12-44.xlsx`
- `Insight_report_pdf_11apr2026_12-44.pdf` → `Sales_trends_pdf_11apr2026_12-44.pdf`
- `Insight_report_xlsx_11apr2026_12-44.xlsx` → `Sales_trends_xlsx_11apr2026_12-44.xlsx`

**Location Affected:** `_REPORT_STEMS` dictionary in `report_exports.py` (line 18-19)

### 3. Documentation Updates
**Files Modified:**
- `Documentation/reports_menu.md`

**Additions:**
- Updated example filenames to reflect new naming scheme
- Updated the "Quantity Display Formatting" section to describe two-decimal formatting for small quantities
- Clarified the logic for fractional quantity display across both weight and count units

## Testing Results

### New Tests Created
1. `tests/test_fractional_quantity_display.py` - 4 tests
   - ✅ `test_summary_report_fractional_ea_display`: Verify '< 1 ea' display
   - ✅ `test_summary_report_fractional_kg_display`: Verify fractional kg display
   - ✅ `test_detail_report_fractional_display`: Verify '< 1' in detail report
   - ✅ `test_zero_quantity_display`: Verify 0 qty shows as '0', not '< 1'

### Updated Tests
1. `tests/test_report_exports.py`
   - ✅ `test_build_report_filename_templates`: Updated expected filenames

### Previously Existing Tests
1. All summary report tests pass (8 tests)
2. All detailed report tests pass (3 tests)

**Total Tests Passing:** 15+ tests ✅

## Code Changes Detail

### `_fmt_qty_unit()` Logic Flow (New)
```
For 'ea' (each):
  if 0 < qty < 1: return (f'{qty:.2f}', 'ea')
  else: return (rounded_int_string, 'ea')

For 'kg':
  if qty >= 1.0: return (f'{qty:.2f}', 'kg')
  if 0 < qty < 1.0:
    grams = qty * 1000
    if grams >= 1: return (f'{grams:.0f}', 'g')
    else: return (f'{grams:.2f}', 'g')
  else: return ('0', 'g')

For other units:
  if 0 < qty < 1: return (f'{qty:.2f}', unit)
  else: return (f'{qty:.3f}', unit)
```

## Backward Compatibility
- ✅ No breaking changes to data structures
- ✅ No changes to report generation logic
- ✅ Only viewer formatting affected
- ✅ PDF/XLSX exports use same formatting rules as viewer
- ✅ All existing tests updated and passing

## Question Answered
**Q: In detail report section 4 (Sales Broken Down by Category), is the ranking by revenue or quantity?**

**A:** Products within each category are listed in the order provided by the report generator (typically sorted by line_sales/revenue descending as the primary sort). The section itself doesn't add additional sorting—products are displayed sequentially with indices (1, 2, 3...). The report_generator layer determines the order before passing data to the formatter.

### 4. Column Width and Spacing Adjustments
**Files Modified:**
- `modules/menu/report_viewers.py`

**Changes:**
- **Summary report (sections 3–6):**
  - "Avg Qty" column width increased from 14 → 16 characters
  - Extra spacing (2 spaces) added between "Avg Qty" and "Avg Revenue" columns
  - Improves visual readability and column separation

- **Detailed report (sections 4–5):**
  - "Amount" column width increased from 12 → 14 characters
  - Better alignment of currency values

**Rationale:** Wider columns and increased spacing prevent visual crowding and improve readability of rankings and totals.

### 5. Role-Based Report Access & Landing Focus
**Files Modified:**
- `modules/menu/report_menu.py`

**Changes:**
- **Landing focus (both roles):**
  - Both Admin and Staff users now land on **Detailed report** by default (previously: Admin on Detail, Staff on Summary)
  - Default date mode remains "Today" for both roles

- **Summary report access control:**
  - **Admin users:** Summary radio is enabled and accessible
    - When Admin selects "Date Range", Summary radio becomes locked (disabled, greyed)
    - When Admin selects "Today", Summary radio becomes unlocked (enabled, clickable)
  - **Staff users:** Summary radio is **permanently disabled, greyed out, and non-clickable**
    - Matches the access pattern for Chart and Inactivity radios
    - Staff cannot switch to Summary regardless of date mode selection

- **Detail report access:**
  - Detail radio is now **enabled for both Admin and Staff** (previously: Staff could not access)
  - Detail radio is never locked or greyed
  - Both roles can always use the Detailed report view

**Rationale:** Simplifies default user experience by landing both roles in Detail view, while maintaining role-based restrictions for privileged reports (Summary, Chart, Inactivity) for Staff users.

### 6. Staff Minimal Detailed Report
**Files Modified:**
- `modules/menu/report_menu.py`
- `modules/menu/report_viewers.py`
- `modules/menu/report_exports.py`
- `tests/test_report_exports.py`

**Changes:**
- Staff users now receive a minimal detailed report variant whenever they view, save to PDF, or save to Excel.
- The minimal variant reuses the existing detailed-report payload and only changes presentation:
  - Sections 4 and 5 are omitted
  - The remaining sections are renumbered so Cash Outflows Detail becomes section 4 and Other Activity becomes section 5
- PDF export and the viewer use the same text formatter, and XLSX export skips the category/top-product sheets for the minimal variant.

**Rationale:** Staff still need detailed-report access, but the reduced version removes the category and top-product breakdowns that are not part of their workflow.
