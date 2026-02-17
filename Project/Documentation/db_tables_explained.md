# Database Tables Explained

This document describes the purpose and structure of each database table used in the POS system, including both system tables and those required by the finalized design policy.

---

## System Tables

### sqlite_sequence
- **Purpose:** Internal SQLite helper table.
- **Description:** Automatically created by SQLite when AUTOINCREMENT is used on a table's primary key. Tracks the last sequence number used for AUTOINCREMENT columns. Not part of the POS business logic.

---

## POS System Tables

---

### 1. Receipts Table
The **receipts** table serves as the primary header for every transaction, whether it is paid immediately, placed on hold, or subsequently cancelled.
- **Identification:** Each entry uses a unique receipt number formatted as YYYYMMDD-####, with the counter capped at 9999.
- **Customer & Staff Info:** A customer name is mandatory only for "Hold Sales" (status: UNPAID) and remains empty for standard paid transactions. The cashier_name captures the logged-in user at the time of the transaction.
- **Financials & Status:** Stores the grand_total (sum of all item totals) and a status field, which can be 'PAID', 'UNPAID', or 'CANCELLED'.
- **Temporal Tracking:** Includes timestamps for created_at, paid_at, and cancelled_at. A note field is utilised specifically for UNPAID or CANCELLED records.

### 2. Receipt_items Table
This table stores the specific products associated with a receipt, functioning as a historical snapshot.
- **Data Integrity:** Records the product name, category, and price at the exact moment of sale; this ensures that if a product's details are changed in the main Product_list later, the historical receipt remains accurate.
- **Detail-Oriented:** Each row includes a line_no to maintain the order of items, the product_code, quantity (integer or float), unit (e.g., Kg or Each), and the line_total.
- **Linking:** Links to the parent receipt via a receipt_id. Notably, this table does not require its own created_at field, as it relies on the parent receipt's timestamp.

### 3. Receipt_payments Table
The **receipt_payments** table is designed to handle the complexities of payment processing, particularly when multiple methods are used.
- **Multi-Type Support:** Allows a single receipt to be paid using various types, including CASH, NETS, PAYNOW, or OTHER.
- **Structure:** Each entry records the receipt_id, the specific payment_type, the tendered amount, and the amount allocated to that type.
- **Tendered vs Amount:** For CASH, `tendered` is the amount handed over by the customer and `amount` is the portion applied to the receipt total. Change due is `tendered - amount`. For non-cash types (NETS, PAYNOW, OTHER), `tendered` equals `amount`.
- **Logic:** This table is only populated when a payment is actually processed; for "Hold Sales" (UNPAID status), no entries are made in this table until the customer returns to pay.

### 4. Cash_outflows Table
The **cash_outflows** table (which replaced the originally proposed cash_movements table) tracks money leaving the system to simplify accounting and reporting.
- **Purpose:** Captures refunds and vendor payments independently of specific receipt-item tracking, as the system focuses on cash flow rather than strict inventory auditing.
- **Movement Types:** The movement_type is restricted to 'REFUND_OUT' and 'VENDOR_OUT'.
- **Reporting:** Essential for calculating the net total in sales reports by subtracting these outflows from the total sales. Includes a note field to capture specific details about the refund or vendor transaction.

---

### 5. Product_list Table
The **Product_list** table is the master catalog for all products available in the POS system. It is referenced for product lookups, pricing, and inventory management.

- **Purpose:** Stores the current details for every product, including code, name, category, supplier, pricing, unit, and last update timestamp. Used for product selection, price calculation, and barcode scanning.
- **Structure:**
	- `product_code` (TEXT, PRIMARY KEY): Unique identifier for each product (e.g., barcode or custom code).
	- `name` (TEXT, NOT NULL): Product name, displayed in menus and receipts.
	- `category` (TEXT): Product category (e.g., Beverages, Vegetables).
	- `supplier` (TEXT): Supplier or vendor name.
	- `selling_price` (REAL, NOT NULL): Current selling price.
	- `cost_price` (REAL): Purchase cost for accounting.
	- `unit` (TEXT): Unit of measure (e.g., Kg, Each).
	- `last_updated` (TEXT): ISO timestamp of last modification.
- **Integration:**
	- Product cache is loaded from this table at startup for fast lookups.
	- CRUD operations (add, update, delete) are managed via the Product Management dialog and backend modules.
	- Historical product details are snapshotted in `receipt_items` at sale time to preserve accuracy.
	- Normalization scripts ensure consistent casing and formatting for product fields.
	- Barcode scanning and menu dialogs reference this table for product validation and display.

---

## Helper Table: receipt_counters  

The `receipt_counters` table is a small, permanent helper table used to track the last allocated receipt number for each day. It is not a business or transaction table, but is essential for generating unique, sequential receipt numbers in the format `YYYYMMDD-####`.

**Purpose:**
- Ensures that each new receipt number for a given day is unique and sequential, starting from 1 and incrementing up to 9999.
- Prevents receipt number collisions, even with multiple cashiers or concurrent transactions.

**Structure:**
- `date` (TEXT, PRIMARY KEY): The date in `YYYYMMDD` format.
- `counter` (INTEGER): The last used receipt number for that date.

**How it works:**
- When a new receipt is started, the system checks if an entry exists for today:
	- If yes, it increments the counter and updates the row.
	- If no, it inserts a new row for today with the counter set to 1.
- This table only stores the latest counter for each day, not every individual receipt number.
- The actual receipt details are stored in the `receipts` table.

---
## Mapping of Functions to Database Tables

Below is a mapping of functions in `modules/db_operation/` related to each database table:

**Product_list**
- modules/db_operation/products_repo.py:
	- add_product
	- update_product
	- delete_product
	- get_product_full
	- get_product_slim
	- list_products
	- list_products_slim
- modules/db_operation/product_cache.py:
	- load_product_cache
	- refresh_product_cache
	- get_product_info
	- upsert_cache_item
	- remove_cache_item

**sqlite_sequence**
- No direct functions; this is an internal SQLite table, not managed by application code.

**receipts**
- modules/db_operation/sale_committer.py:
	- SaleCommitter.commit_payment (creates or marks receipts as PAID)

**receipt_items**
- modules/db_operation/sale_committer.py:
	- SaleCommitter.commit_payment (inserts receipt_items rows)

**receipt_payments**
- modules/db_operation/sale_committer.py:
	- SaleCommitter.commit_payment (inserts receipt_payments rows)

**cash_outflows** (implemented as cash_movements)
- modules/db_operation/cash_movements_repo.py:
	- ensure_table
	- add_movement
	- list_movements

---
## On the Shared 'note' Column in Receipts and Cash_outflows

The `note` column in both the `receipts` table and the `cash_outflows` table now stores the same information for refund transactions. When a user processes a refund, the reason provided in the notes column is updated in both tables, ensuring consistency and traceability.

**Key Points:**

- **Unified Information:**
	- For refunds, the same note (reason) is recorded in both the `receipts` and `cash_outflows` tables.
	- This ensures that the refund reason is visible in both transaction history and accounting reports.

- **Other Scenarios:**
	- For other transaction types (e.g., hold, cancel, vendor payments), notes may still be used independently in each table as appropriate.

By updating the notes in both tables for refunds, the system maintains clear and consistent record-keeping across transaction and accounting layers.
---

## On the Shared 'created_at' Column Across Tables

1. **Distinct Meanings of 'created_at'**
   Each table uses this column to record a specific, independent event:
   - **Receipts Table:** Here, `created_at` represents the original transaction date and time. It marks when the items were first scanned and the receipt number was generated, regardless of whether it was paid immediately or placed on hold.
   - **Receipt_payments Table:** In this table, `created_at` records the exact moment a payment was processed. This is crucial because a receipt might be "created" today (placed on hold) but "paid" tomorrow; thus, the `created_at` in the payments table would differ from the one in the receipts table.
   - **Cash_outflows Table:** This column captures the timing of money leaving the system, such as when a refund is issued or a vendor is paid. Since these outflows are often independent of the original sale timing, they require their own temporal marker for accurate daily reporting.

- **Database Structure:**
	- In the schema, these are unique fields: `receipts.note` and `cash_outflows.note`.
	- There is no technical collision because they belong to different tables that are queried for different reasons (e.g., the `receipts` note is used in the "View Hold" UI, while the `cash_outflows` note is used for the "Sales Report").

- **Populating Logic:**
	- In the **receipts** table, the `note` field is filled when a user puts a sale on hold or deletes a record in "View Hold" mode.
	- In the **cash_outflows** table, the `note` field captures specific info like the **receipt number for a refund** or the **description of a vendor transaction**.

- **Design Policy:**
	- The sources confirm that while the `note` field is not required for standard paid transactions, it is mandatory or optional for specific status changes (UNPAID/CANCELLED) and for all cash movements to ensure clear record-keeping.

By maintaining these as separate columns in their respective tables, the system can track the "why" behind a held receipt separately from the "why" behind a cash refund, ensuring **accounting principles** are followed without data overlapping.
---
