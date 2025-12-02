# Manual Entry Button — Functional Specification

## Goal
Add non-barcoded/non-DB products by letting the cashier enter Product name, Quantity, and Unit price via an on-screen keyboard, and then append the item to the sales table.

## Entry Point
- Trigger: Clicking the "Manual" button opens a modal dialog.
- Scope: Bypasses DB lookup entirely (ad-hoc items). The separate "barcode-not-found → Add Product" flow is out of scope here and can be handled later.

## Dialog Layout
- Left panel
  - Title: "Manual Product Entry"
  - Inputs:
    - Product name: Editable combo or line edit (editable combo preferred to reuse recent names)
    - Unit price: Decimal input
    - Quantity: Integer input
  - Actions: OK and Cancel buttons
- Right panel (on-screen keyboard)
  - Keys: digits 0–9, dot ".", QWERTY letters (A–Z), Space, Backspace, and a Tab/Enter key that advances focus cyclically

## Input Behavior & UX
- Product name
  - Required (non-empty)
  - Max length: 15 characters
- Quantity
  - Integer-only
  - No spin arrows visible
  - Default shown as 1
  - Allow typing "0" while editing (do not auto-correct), but block submission until > 0
- Unit price
  - Decimal allowed
  - Default shown as 0 (visually without decimals at default)
  - Dot key inserts a decimal point (only one)
- Focus & selection
  - On open: focus Product name and select all
  - On focus-in for any field: select all (typing replaces current value)
- Tab/Enter behavior
  - On-screen Enter (or a "Tab"-labeled key) advances focus cyclically
  - Cycle order: Product name → Unit price → Quantity → OK → Cancel → (wrap)
  - Do not advance if current field is invalid (keep focus; select all)

## Validation Rules
- When to validate: on OK press, and on Tab/Enter (on-screen or hardware)
- Rules
  - Product name: must be non-empty
  - Quantity: must be > 0
  - Unit price: must be > 0
- If invalid
  - Keep focus on the invalid field and select all text
  - Mark the field with a red border (dynamic property like error=true on the line editor)
  - Show a clear message in the status bar:
    - "Product name is required"
    - "Quantity must be > 0"
    - "Unit price must be > 0"
  - OK does not close the dialog until all fields are valid

## On-Screen Keyboard Behavior
- Keys never steal focus from the active editor (buttons set to NoFocus)
- Character routing
  - If a spin box is active, insert into its internal line edit:
    - Quantity: digits only
    - Unit price: digits plus a single dot
  - Product name: letters, digits, space allowed; backspace works normally
- Special keys
  - Backspace: delete character to the left
  - Space: insert space
  - Enter/Tab: validation-aware focus advance (block on invalid)

## Styling Hooks
- Error visual for invalid inputs
  - Apply via a dynamic property (e.g., `error=true`) on the line edit widgets
  - Style in QSS (red border and a light red background)
- Keep overall appearance consistent with `assets/style.qss`

## OK and Cancel Behavior
- OK
  - Validate all three fields
  - On success, add a row to the sales table with: Product name (as typed), Quantity, Unit price, and Total = Quantity × Unit price
  - Close the dialog
  - Show a brief confirmation in the status bar: "Added manual item: {name}"
- Cancel
  - Close the dialog without changes

## Status Bar Messages
- Optional on open: "Opening Manual Entry…"
- On validation failure: field-specific messages (as above)
- On success: "Added manual item: {name}"

## Non-Functional Considerations
- Console/log noise: keep quiet under normal use; optional single print on open during development guarded by `DEBUG` flag
- Manual items must not query the DB; treat them as ad-hoc entries

## Acceptance Criteria Checklist
- [ ] Manual button opens a modal dialog with inputs and on-screen keyboard
- [ ] Product name required and ≤ 15 chars
- [ ] Quantity accepts integers; 0 allowed during editing but blocked on OK until > 0
- [ ] Unit price accepts decimals; 0 blocked on OK
- [ ] Enter/Tab (on-screen and hardware) advances cyclically and blocks on invalid fields
- [ ] Invalid fields show red border; focus stays; status bar shows specific error
- [ ] OK adds a row to the sales table with correct totals; Cancel discards
- [ ] On-screen keys don’t steal focus; typing routes to the active field appropriately

## Optional Enhancements
- Add a QDoubleValidator to Unit price editor to block invalid characters from hardware keyboard
- Make the Tab cycle inputs-only (skip OK/Cancel) if desired; keep buttons reachable via mouse
- Persist a short history of recent manual product names in the editable combo
