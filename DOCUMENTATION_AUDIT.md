# Documentation Audit

Scope: root `POS` docs requested by the user: `README.md`, `production_alignment.md`, `Database_admin/DB_administration.md`, `Database_admin/setup_fresh_database.py`, and the contents of root `Documentation/`. `Exploration/` was skipped.

Date reviewed: 2026-07-04.

## Executive Summary

- Root `README.md` is the most current broad entry point, but it contains mojibake/encoding artifacts, stale structure examples, duplicate logout text, placeholder license/contact text, and broken links to docs that actually live under `Project/Documentation/`.
- `production_alignment.md` is useful as a deployment/path-change phase log. It is not general user documentation and should either be kept as a release/deployment record or folded into a shorter deployment note.
- `Database_admin/DB_administration.md` is useful and aligns closely with the current admin scripts. Keep it, with minor wording updates around configuration names.
- `Database_admin/setup_fresh_database.py` is not documentation; it is the executable database bootstrap script documented by `DB_administration.md`. Keep it as source code.
- Root `Documentation/` has many exact duplicates. Most early planning docs describe Tkinter/ttkbootstrap, old schemas, or planned hardware features and are stale compared with the active PyQt5 application.
- Root `Documentation/UI/` duplicates UI docs already present directly under `Documentation/`.
- The active, detailed feature docs appear to live in `Project/Documentation/`, but that folder was outside the explicit requested list. The root README currently links to those files using the wrong base path.

## Duplicate Groups

Exact duplicate files found by SHA-256 hash:

| Duplicate Set | Recommendation |
| --- | --- |
| `Documentation/Business Requirements Document.md` and `Documentation/Business Requirements V.1.md` | Keep one canonical BRD or archive both as historical planning. Delete the duplicate. |
| `Documentation/Development Documentation (Outline).md` and `Documentation/Development outline V.1.md` | Keep at most one if historical. Otherwise remove; it is only an outline and no longer matches the current structure. |
| `Documentation/System Documentation.md` and `Documentation/System Documentation V.1.md` | Keep one only if rewritten. Current content is stale against the active schema and workflows. |
| `Documentation/User Documentation - POS System.md` and `Documentation/User Documentation POS V.1.md` | Keep one only after updating. Current content describes broad planned features, not verified current operator workflow. |
| `Documentation/POS_Technical_Overview.md` and `Documentation/Windows environment setup overview.md` | Delete or archive one; both are the same stale Tkinter/Python 3.13 overview. |
| `Documentation/UI_Design_POS.md` and `Documentation/UI/UI Design POS V.1.md` | Keep one only as historical prototype notes. Active app is PyQt5, not Tkinter/ttkbootstrap. |
| `Documentation/UI HTML protype explained.md` and `Documentation/UI/UI HTML protype explained.md` | Keep one only as historical prototype notes. Also fix typo `protype` to `prototype` if retained. |
| `Documentation/UI GUI tool evaluation.pdf` and `Documentation/UI/UI GUI tool evaluation.pdf` | Keep one copy if useful as historical design research. |

Note: several filenames contain punctuation/encoding issues in terminal output, especially the en dash in `User Documentation - POS System.md` and non-ASCII symbols inside older docs.

## File Log

| Path | Documents | Status | Cleanup Recommendation |
| --- | --- | --- | --- |
| `README.md` | Main project overview, setup, feature list, project structure, DB path, usage, scanner behavior, error handling, and doc index. | Partly current, partly stale. It correctly says PyQt5/SQLite and mentions current concepts like `PRODUCT_CACHE`, `.ui`, QSS, scanner routing, hold failure handling, and `logs/error.log`. Problems: broken links to `Documentation/*.md` that appear to exist under `Project/Documentation/`; stale `tools/format_assets.py` path; stale module examples like `salesTable.py` and `db.py`; right-side menu says buttons open placeholders though many are implemented; duplicate logout bullet; mojibake characters; placeholder license/contact. | Keep as canonical root entry point, but clean heavily. Fix links to `Project/Documentation/...` or move canonical feature docs to root `Documentation/`. Refresh project tree from actual files. Remove placeholder license/contact or fill them. Fix encoding artifacts. |
| `production_alignment.md` | Phase-by-phase deployment alignment log: target dev/client layouts, path rules, database contract, external logs, writable data, and verification counts. | Useful but specialized. Current enough to keep as a deployment/release engineering record. Last phase is marked pending review. | Keep, rename or move to `Documentation/deployment/production_alignment.md` if organizing. Update Phase 4 status when approved/committed. |
| `Database_admin/DB_administration.md` | Database admin folder structure, config, product CSV format, fresh setup, reset behavior, product validation rules, receipt counters, legacy scripts, post-setup checks. | Mostly current and useful. Matches `setup_fresh_database.py` flow and current admin folder structure. Minor issue: mentions `.env` keys like `DB_NAME`/`DB_PATH`, while code also exposes `ADMIN_DB_PATH` and `ADMIN_DB_FILENAME`. | Keep. Light update only: clarify env variable names, add exact run location, and link to production-safe product update process when that exists. |
| `Database_admin/setup_fresh_database.py` | Executable script, not prose documentation. Creates/resets DB, creates users/product/receipt/cash-outflow tables, imports validated product CSV, runs verification. | Current source code. Properly documented by `DB_administration.md`. | Keep as code. Do not move into docs. Consider adding a short module docstring warning that `--reset` is destructive to transaction history after backup/reset behavior. |
| `Documentation/Business Requirements Document.md` | Original business requirements for standalone store: objectives, scope, sales, payment, receipt printing, products/suppliers/transactions schema, reports, stock alerts. | Duplicate of `Business Requirements V.1.md`. Stale versus current implementation: old schema names (`ProductID`, `Transactions`, `TransactionDetails`), stock threshold requirements not reflected in current DB admin docs, hardware/scale features are planned or shelved. | Archive as historical requirements or rewrite into a current BRD. Delete duplicate. |
| `Documentation/Business Requirements V.1.md` | Same as above. | Exact duplicate. | Delete or archive; do not keep both. |
| `Documentation/Development Documentation (Outline).md` | High-level development documentation outline: environment, codebase structure, module docs, DB layer, hardware, logging, tests, deployment, security, future enhancements. | Duplicate of `Development outline V.1.md`. Stale/generic: says GUI toolkit is Tkinter or PyQt, folder structure does not match current repo, many sections are outline placeholders. | Delete or archive. Replace with links to active `Project/Documentation/` feature docs if needed. |
| `Documentation/Development outline V.1.md` | Same as above. | Exact duplicate. | Delete or archive; do not keep both. |
| `Documentation/git_ignore_pyc_and_pycache_cleanup.md` | Explains why to ignore `__pycache__/` and `*.pyc`, how to untrack safely, and what went wrong with a past PowerShell/Git command. | Useful as a one-off troubleshooting note, but not POS product documentation. It contains a long incident transcript and references a past mistake. | Move to `Documentation/dev-notes/` or archive. Keep only if this repo still needs the Git cleanup guidance. |
| `Documentation/manualEntrySpec.md` | Functional specification for Manual Entry button/dialog: inputs, validation, keyboard behavior, status messages, acceptance checklist. | Partly useful but likely superseded by `Project/Documentation/manual_entry.md` and current PyQt5 implementation. Mentions `assets/style.qss`, while current QSS appears under `Project/assets/qss/`. Checklist is still unchecked. | Compare with current manual entry implementation and `Project/Documentation/manual_entry.md`; merge any useful acceptance criteria, then remove or archive this spec. |
| `Documentation/POS_Technical_Overview.md` | Environment and architecture overview: Windows 11, Python 3.13, hardware, dependencies, Tkinter/ttkbootstrap UI, old database tables. | Duplicate of `Windows environment setup overview.md`. Stale: active source imports PyQt5 throughout; root README says PyQt5; database table names like `inventory` and `daily_transaction` do not match current `Product_list`, `receipts`, `receipt_items`, etc.; Python version conflicts with `Python Environment.md`. | Delete or rewrite entirely. If kept, mark as historical pre-PyQt prototype documentation. |
| `Documentation/Windows environment setup overview.md` | Same as `POS_Technical_Overview.md`. | Exact duplicate and stale. | Delete or archive; do not keep both. |
| `Documentation/Python Environment.md` | Narrative of Python interpreter confusion, choosing Python 3.12 for PyQt5, PATH notes, and best practices. | Useful as local environment history, but conflicts with `POS_Technical_Overview.md`/`Windows environment setup overview.md`, which say Python 3.13 is primary. It is personal-machine-specific rather than project-wide setup docs. | Keep only as local dev note or convert into a concise `Project/README.md` setup section. Prefer documenting supported Python range from `requirements.txt`/tested versions. |
| `Documentation/System Documentation.md` | Conceptual system architecture, database schema, workflows, hardware integration, reports, security, deployment. | Duplicate of `System Documentation V.1.md`. Stale: schema uses `Products`, `Suppliers`, `Transactions`, `TransactionDetails`; current app/admin docs use `Product_list`, `receipts`, `receipt_items`, `receipt_payments`, `cash_outflows`, `users`; describes stock updates and scale workflow not clearly implemented. | Rewrite if a system architecture doc is needed. Otherwise archive. Delete duplicate. |
| `Documentation/System Documentation V.1.md` | Same as above. | Exact duplicate. | Delete or archive; do not keep both. |
| `Documentation/User Documentation - POS System.md` | Operator/user guide: system requirements, startup, main screen, performing sale, stock management, reports, settings, troubleshooting, safety. | Duplicate of `User Documentation POS V.1.md`. Stale or over-broad: describes stock management/settings/reporting as user-facing capabilities without matching the current README's exact UI behavior; includes optional weighing machine. | Keep one only after updating against the live PyQt5 UI. Delete duplicate. |
| `Documentation/User Documentation POS V.1.md` | Same as above. | Exact duplicate. | Delete or archive; do not keep both. |
| `Documentation/UI_Design_POS.md` | UI design plan for Tkinter/ttkbootstrap implementation based on HTML/CSS prototype; panels, theme, sidebar, event notes, next steps. | Duplicate of `Documentation/UI/UI Design POS V.1.md`. Stale: active implementation is PyQt5 with `.ui` files and QSS. | Archive as prototype history or delete. Current UI docs should live near `Project/Documentation/` and reference PyQt5 widgets. |
| `Documentation/UI/UI Design POS V.1.md` | Same as above. | Exact duplicate. | Delete or archive; do not keep both. |
| `Documentation/UI HTML protype explained.md` | Explains the original HTML POS sales table/payment panel prototype and intended behavior. | Duplicate of `Documentation/UI/UI HTML protype explained.md`. Historical only. Filename typo: `protype`. Stale against current PyQt5 UI and implemented flows. | Keep one copy only if preserving prototype history; otherwise delete. |
| `Documentation/UI/UI HTML protype explained.md` | Same as above. | Exact duplicate. | Delete or archive; do not keep both. |
| `Documentation/UI GUI tool evaluation.pdf` | PDF evaluating GUI tools/themes. | Duplicate of `Documentation/UI/UI GUI tool evaluation.pdf`. Likely historical design research. | Keep one copy only if useful; otherwise archive/delete. |
| `Documentation/UI/UI GUI tool evaluation.pdf` | Same as above. | Exact duplicate. | Delete or archive; do not keep both. |

## Broken or Suspicious Links

In `README.md`, these links currently point to root `Documentation/`, but matching active files appear under `Project/Documentation/` instead:

- `Documentation/payment_processing.md`
- `Documentation/Payment_panel.md`
- `Documentation/cash_drawer.md`
- `Documentation/view_hold.md`
- `Documentation/product_menu.md`
- `Documentation/error_logging_and_fallback.md`
- `Documentation/dialog_utils.md`
- `Documentation/dialog_pipeline.md`
- `Documentation/scanner_input_infocus.md`
- `Documentation/db_operation.md`
- `Documentation/logout_and_titlebar.md`
- `Documentation/admin_settings.md`

Also suspicious:

- `Documentation/printer.md` is linked from `README.md`, but the discovered matching docs are `Project/Documentation/printer_drawer.md` and `Project/Documentation/qr_generator.md`; no root `Documentation/printer.md` was found in the requested scan.
- `README.md` references `tools/format_assets.py`, while the discovered file is `Project/dev_tools/maintenance/format_assets.py`.

## Suggested Cleanup Plan

1. Decide canonical doc locations:
   - Option A: keep root `Documentation/` for high-level docs and `Project/Documentation/` for implementation docs.
   - Option B: consolidate all Markdown docs under one `Documentation/` tree and update README links.
2. Delete exact duplicates first. This is low risk because hashes match.
3. Move historical prototype/planning docs into `Documentation/archive/` or remove them from active docs.
4. Refresh `README.md` after duplicate removal:
   - fix links,
   - regenerate project tree,
   - remove stale placeholders and duplicate text,
   - fix mojibake/encoding artifacts.
5. Keep and lightly update `Database_admin/DB_administration.md`.
6. Rewrite one current system overview from actual code/docs if needed, using PyQt5, `Project/config.py`, `Product_list`, receipt tables, hold receipts, cash outflows, logs, runtime data paths, and current deployment layout.
