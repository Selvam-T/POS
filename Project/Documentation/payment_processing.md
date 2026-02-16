# Payment Processing and Receipt Commit Logic

This document explains how the application finalizes a sale when the user
clicks the PAY button. The implementation guarantees atomicity (single
commit/rollback) and handles both new sales and held (UNPAID) receipts.

Overview
--------
- UI layer (`modules/payment/payment_panel.py`): validates inputs and emits the
  `payRequested` signal with a normalized payment payload. It does not write
  to the database.
- Application layer (`main.py`): listens for `payRequested`, prepares payment
  data, applies a double-submit guard, and delegates DB finalization to
  `modules/payment/sale_committer.py`.
- Service layer (`modules/payment/sale_committer.py`): executes the multi-table
  DB commit inside one transaction using `modules/db_operation/db.transaction`.

Why the app layer performs DB commits
-------------------------------------
- Finalizing a sale touches multiple tables: `receipt_counters` (for the
  daily counter), `receipts` (header), `receipt_items`, and `receipt_payments`.
- To avoid partial commits (e.g., header inserted but items or payments fail),
  all writes must occur inside a single DB transaction. The application
  orchestrator (`main.py`) owns the sales table and receipt context and is the
  natural place to coordinate this atomic operation.
- The `transaction()` helper in `modules/db_operation/db.py` uses
  `BEGIN IMMEDIATE` to acquire a write lock early and ensures `COMMIT` on
  success and `ROLLBACK` on exception.

High-level commit flow
----------------------
1. Validation: `PaymentPanel` ensures payment totals and tender are valid and
   enables the PAY action only when rules are satisfied.
2. Build payload: `main.py` collects a snapshot of sale items and the
   selected payment split from the UI payload.
3. Double-submit guard: `main.py` checks `_payment_in_progress`. If a commit is
  already running, it shows "Payment is already processing..." and exits.
4. Open DB connection: obtain a single sqlite3 connection via `get_conn()`.
5. Begin transaction: `with transaction(conn):` (this runs `BEGIN IMMEDIATE`).
6. Within the transaction:
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
     method used (CASH, NETS, PAYNOW, VOUCHER, ...).
7. Commit: if all statements succeed the transaction commits; otherwise
   an exception rolls back all changes and the calling UI layer is informed.
8. Finalize UI state: `_payment_in_progress` is cleared and pay-button state is
  recalculated in `finally` to avoid a stuck disabled button.

Important implementation details
--------------------------------
- `next_receipt_no` must be called with the same `conn` used by the
  transaction so the counter update participates in the same atomic boundary.
  The code checks `conn.in_transaction` and avoids nested `BEGIN` errors.
- The code is schema-tolerant: helper functions in `main.py` detect common
  column names (e.g. `receipt_no` vs `receipt_number`, `quantity` vs `qty`)
  to work with minor schema variants.
- Hard-fail error handling: `main.py` routes commit exceptions through
  `modules/ui_utils/dialog_utils.report_exception(...)` so failures are both:
  - logged with traceback detail (for troubleshooting), and
  - shown as a concise message on the MainWindow status bar.
- On commit failure, the current sale is intentionally preserved (sales table is
  not cleared) so cashiers can retry payment or choose an explicit fallback.

DB CRUD failure fallback (operations runbook)
---------------------------------------------
When payment commit fails, do **not** move to the next customer immediately.

Recommended cashier action order:
1. Retry PAY once after confirming network/DB availability.
2. If it fails again, place the sale on HOLD (preserve cart and continue queue).
3. Escalate persistent failures to supervisor/IT and use `log/error.log`
   traceback entries for diagnosis.

Why this is required:
- Atomic transaction rollback means no partial receipt is saved on failure.
- Because the sale is still in the UI, clearing it blindly would risk revenue
  loss or mismatch between physical payment and DB records.

Testing recommendations
-----------------------
- Happy path: scan two items, open payment panel, allocate full cash, click
  PAY. Verify the following in the DB:
  - `receipt_counters` counter incremented for today's date
  - One row in `receipts` with status='PAID'
  - Two rows in `receipt_items` linked to that receipt
  - One or more rows in `receipt_payments` covering the grand total
- Held receipt path: create a hold (UNPAID), load it, then pay. Verify the
  existing `receipts` row shows `status='PAID'` and `paid_at` set; `receipt_items`
  unchanged; `receipt_payments` has new payment rows.
- Failure path (simulation): temporarily force `SaleCommitter.commit_payment`
  to raise an exception (or point DB path to an invalid/unavailable DB in a dev
  environment). Verify:
  - status bar shows payment failure,
  - traceback is written to `log/error.log`,
  - sales table is not cleared,
  - user can retry or put sale on hold.

References
----------
- `modules/db_operation/db.py` — transaction helper (`BEGIN IMMEDIATE`).
- `modules/db_operation/receipt_numbers.py` — `next_receipt_no` (now safe
  to call inside an existing transaction when passed `conn`).
- `modules/db_operation/receipts_repo.py` — simple repo helpers used elsewhere.
- `modules/payment/sale_committer.py` — dedicated atomic commit service.
- `main.py` — payment orchestration, double-submit guard, and hard-fail routing.
