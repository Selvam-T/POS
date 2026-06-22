# Payment Processing and Receipt Commit Logic

This document explains how the application finalizes a sale when the user
clicks the PAY button. The implementation guarantees atomicity (single
commit/rollback) and handles both new sales and held (UNPAID) receipts.

Overview
--------
- UI layer (`modules/payment/payment_panel.py`): validates inputs and emits the
  `payRequested` signal with a normalized payment payload (including `tender`
  for CASH). It does not write to the database.
- Application logic uses a cash-only drawer gate (`cash > 0`); tender/change do
  not affect drawer opening.
- Application layer (`main.py`): listens for `payRequested`, prepares payment
  data, applies a double-submit guard, and delegates DB finalization to
  `modules/db_operation/paid_sale_committer.py`.
- Service layer (`modules/db_operation/paid_sale_committer.py`): executes the multi-table
  DB commit inside one transaction using `modules/db_operation/db.transaction`.

Why the app layer performs DB commits
-------------------------------------
- Finalizing a sale touches multiple tables: `receipt_counters` (for the
  daily counter), `receipts` (header), `receipt_items`, and `receipt_payments`.
- To avoid partial commits (e.g., header inserted but items or payments fail),
  all writes must occur inside a single DB transaction. The application
  orchestrator (`main.py`) owns the sales table and receipt context and is the
  natural place to coordinate this atomic operation.
- The `transaction()` helper in `modules/db_operation/sqlite_runtime.py` uses
  `BEGIN IMMEDIATE` to acquire a write lock early and ensures `COMMIT` on
  success and `ROLLBACK` on exception.

High-level commit flow
----------------------
1. Sales-table readiness: `MainLoader` blocks PAY when the required Sales table
   failed initialization or a runtime rebuild. The originating failure is
   logged once and each blocked PAY attempt shows the shared StatusBar error.
2. Validation: `PaymentPanel` ensures payment totals and tender are valid and
   enables the PAY action only when rules are satisfied.
3. Build payload: `main.py` collects a snapshot of sale items and the
   selected payment split from the UI payload.
4. Double-submit guard: `main.py` checks `_payment_in_progress`. If a commit is
  already running, it shows "Payment is already processing..." and exits.
5. Open DB connection: obtain a single sqlite3 connection via `get_conn()`.
6. Begin transaction: `with transaction(conn):` (this runs `BEGIN IMMEDIATE`).
7. Within the transaction:
   - If this is a new sale (`active_receipt_id` is None):
     - Call `next_receipt_no(conn=conn)` to atomically increment the daily
       counter and obtain a receipt number.
     - Insert the receipt header row (status='PAID', `created_at` = `paid_at`).
     - Insert one `receipt_items` row per cart line (snapshot product name,
       unit, price, quantity, line_total).
   - If this is a held receipt (`active_receipt_id` points to an UNPAID
     receipt):
     - Update the existing receipt's status to 'PAID' and set `paid_at`.
     - Do not re-insert items (they were inserted when the sale was placed on
       hold).
   - Insert one or more `receipt_payments` rows representing each payment
     method used (CASH, NETS, PAYNOW, VOUCHER, ...). CASH rows store both
     `amount` (applied to the receipt total) and `tendered` (cash received);
     non-cash rows set `tendered = amount`.
8. Commit: if all statements succeed the transaction commits; otherwise
   an exception rolls back all changes and the calling UI layer is informed.
9. Finalize UI state: `_payment_in_progress` is cleared and pay-button state is
  recalculated in `finally` to avoid a stuck disabled button.

Important implementation details
--------------------------------
- `next_receipt_no` must be called with the same `conn` used by the
  transaction so the counter update participates in the same atomic boundary.
  The code checks `conn.in_transaction` and avoids nested `BEGIN` errors.
- The code is schema-tolerant: helper functions in `main.py` detect common
  column names (e.g. `receipt_no` vs `receipt_number`, `quantity` vs `qty`)
  to work with minor schema variants.

Snapshot model reminder:
- The `receipt_items` rows are a historical snapshot and are not retroactively modified when master `Product_list` rows change (for example when a product's `category` is updated or replaced). This design guarantees stable historical reporting. When master data changes, refresh `PRODUCT_CACHE()` for runtime lookups, but do not alter existing `receipt_items`.
- Hard-fail error handling: `main.py` routes commit exceptions through
  `modules/ui_utils/dialog_utils.report_exception(...)` so failures are both:
  - logged with traceback detail (for troubleshooting), and
  - shown as a concise message on the MainWindow status bar.
- On commit failure, the current sale is intentionally preserved (sales table is
  not cleared) so cashiers can retry payment or choose an explicit fallback.
- Payment DB failures are counted in `main.py`. After three failed commit
  attempts for the current sale, the PAY button enters a recovery lock:
  `payPayOpsBtn` is disabled, its text changes to `PAY err`, and the StatusBar
  persistently shows "Print receipt and clear salesTable to proceed" until the
  sales table is cleared.
- While the recovery lock is active, `printPayOpsBtn` is enabled even though the
  cart still has a total. It prints a temporary snapshot receipt using
  `modules/payment/recovery_receipt.py`. This receipt is labeled
  `TEMP-DB-FAIL` and is not inserted into any database table.
- Clearing the sales table while the recovery lock is active resets the retry
  count and restores the PAY button. If the payment panel has a cash allocation,
  the cash drawer is opened before payment fields are cleared. Ordinary clear
  cart actions do not use this drawer recovery path.

DB CRUD failure fallback (operations runbook)
---------------------------------------------
When payment commit fails, do **not** move to the next customer immediately.

Recommended cashier action order:
1. Retry PAY until the StatusBar shows the recovery instruction, up to three
   total failed attempts.
2. When PAY shows `PAY err`, print the temporary recovery receipt if needed.
3. Clear the sales table to reset the payment panel and continue.
4. Escalate persistent failures to supervisor/IT and use `logs/error.log`
   traceback entries for diagnosis.

Why this is required:
- Atomic transaction rollback means no partial receipt is saved on failure.
- Because the sale is still in the UI, clearing it blindly would risk revenue
  loss or mismatch between physical payment and DB records.
- The `TEMP-DB-FAIL` receipt is an operator recovery artifact only. It does not
  reserve a receipt number and does not persist `receipts`, `receipt_items`, or
  `receipt_payments` rows.

Testing recommendations
-----------------------
- Happy path: scan two items, open payment panel, allocate full cash, click
  PAY. Verify the following in the DB:
  - `receipt_counters` counter incremented for today's date
  - One row in `receipts` with status='PAID'
  - Two rows in `receipt_items` linked to that receipt
  - One or more rows in `receipt_payments` covering the grand total
  - CASH rows include `tendered` and `amount` (change due = `tendered - amount`)
- Held receipt path: create a hold (UNPAID), load it, then pay. Verify the
  existing `receipts` row shows `status='PAID'` and `paid_at` set; `receipt_items`
  unchanged; `receipt_payments` has new payment rows.
- Failure path (simulation): temporarily force `PaidSaleCommitter.commit_payment`
  to raise an exception (or point DB path to an invalid/unavailable DB in a dev
  environment). Verify:
  - status bar shows payment failure,
  - traceback is written to `logs/error.log`,
  - sales table is not cleared,
  - attempts 1 and 2 allow retry,
  - attempt 3 locks PAY as `PAY err` and enables Print,
  - Print outputs a `TEMP-DB-FAIL` snapshot receipt,
  - clear-cart restores PAY to normal and opens the drawer only if the locked
    recovery sale had a cash allocation.

References
----------
- `modules/db_operation/sqlite_runtime.py` — transaction helper (`BEGIN IMMEDIATE`).
- `modules/db_operation/receipt_numbers.py` — `next_receipt_no` (now safe
  to call inside an existing transaction when passed `conn`).
- `modules/db_operation/paid_sale_committer.py` — dedicated atomic commit service.
- `main.py` — payment orchestration, double-submit guard, and hard-fail routing.
- `main.py` also owns the Sales-table readiness gate used before payment.
