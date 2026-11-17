# System Documentation

This is the system-level reference for the POS application: its main components,
data responsibilities, and business workflows. For the implementation stack,
source layout, and runtime environment, see `POS_Technical_Overview.md` and
`Python Environment.md`. For detailed table definitions, see
`../../Development/src/module_docs/db_tables_explained.md`.

## System Architecture

```text
Barcode scanner
      |
      v
Barcode manager --> Product cache (loaded from Product_list)
                           |
                           v
                    Sales table and total
                           |
             +-------------+-------------+
             |                           |
             v                           v
       Payment workflow           Customer display
             |
             v
       PaidSaleCommitter
             |
             +--> receipts
             +--> receipt_items
             +--> receipt_payments

Refund and vendor outflows --> cash_outflows
Reports --------------------> database repositories
Printer and cash drawer <---- successful payment / receipt actions
```

The application is a desktop POS built with PyQt5 and SQLite. Product lookups
use an in-memory cache populated from the product catalog. Receipt writes are
handled by database services; the UI and business workflows use repository
modules instead of issuing SQL directly.

## Data Responsibilities

The application database uses these primary data areas:

| Data area | Responsibility |
|---|---|
| `Product_list` and `Category` | Current product catalog and category data used for product selection and lookup. |
| `receipts` | Receipt identity, status, totals, and transaction-level information, including held sales. |
| `receipt_items` | Product and price snapshots for each receipt, preserving sale-time details. |
| `receipt_payments` | Payment method allocations and cash tender/change information for paid receipts. |
| `cash_outflows` | Refund, vendor, and other supported cash-flow records. |
| `users` | POS login and account state. |
| `receipt_counters` | Receipt number allocation. |

This table list is a conceptual map, not a substitute for the schema reference.
See `../../Development/src/module_docs/db_tables_explained.md` for field-level details,
constraints, and behavior.

## Core Workflows

### Product lookup and sale entry

At startup, the application loads product data into its in-memory cache. A
barcode scan is routed according to the active UI and focus rules. A successful
lookup supplies product details to the sales workflow, which updates the sales
table and payable total. Manual and vegetable entry have their own dialogs and
validation flows.

### Payment and receipt persistence

The cashier selects and allocates payment methods in the payment panel. A
successful payment is committed atomically to `receipts`, `receipt_items`, and
`receipt_payments`. If the database commit fails, the current sale is retained
for recovery rather than silently discarded.

### Held sales

A held sale is saved as an unpaid receipt. It can later be retrieved through
View Hold and loaded, paid, printed, or voided according to its state and the
available actions.

### Refunds, outflows, and reports

Refund and vendor flows record supported cash movements in `cash_outflows`.
Reports combine receipt and outflow data through the database reporting layer.
Receipt item snapshots preserve the product details used when the sale was
made, even if the current product catalog changes later.

### Customer display and peripherals

The application includes a customer-display component and printer/cash-drawer
support. Device configuration and weighing-scale integration should not be
assumed from this overview; refer to the current implementation and deployment
guidance for the status of a specific device.

## Current Scope Notes

- The POS database schema and application workflows are authoritative over the
  older conceptual schema sometimes found in planning documents.
- A weighing-scale serial integration is not described here as an implemented
  feature.
- The standalone Device Manager feature was shelved and is not part of the
  project scope.
