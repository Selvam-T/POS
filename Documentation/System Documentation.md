# System Documentation

**Project**: POS System for Standalone Store  
**Platform**: Windows Embedded PC with Customer-Facing Display  
**Database**: SQLite  
**Language/Framework**: Python (front-end + hardware integration)  

---

## 1. System Architecture

### 1.1 High-Level Diagram (conceptual)

```
[Barcode Reader] ──► [POS Application UI] ──► [SQLite Database] ──► [Reports]
│ │
│ ├──► [Receipt Printer (Epson TM-T82X)]
│ ├──► [Cash Drawer via Printer Port]
│ ├──► [Customer Display Screen]
│ └──► [Weighing Machine (RS232/USB)]

```
### 1.2 Components

#### POS Front-End (Python App)
*   Cashier interface (scan, view cart, select payment).
*   Configurable receipt printing (auto/manual).
*   Customer-facing display output.
*   Handles weighing machine input (via serial/USB).

#### Database Layer (SQLite)
*   Stores product catalog, suppliers, stock levels.
*   Stores transactions and transaction details.
*   Provides data for reports.

#### Hardware Integration Layer
*   **Barcode Scanner**: USB HID (acts like keyboard input).
*   **Receipt Printer**: Epson TM-T82X, ESC/POS commands.
*   **Cash Drawer**: Triggered via printer’s RJ port.
*   **Weighing Machine**: RS232/USB (pyserial library).
*   **Customer Display**: Mirrors or simplified display (Python GUI fullscreen on secondary screen).

---

## 2. Database Schema

### 2.1 Tables

#### Products
| Field                   | Type    | Description                       |
| :---------------------- | :------ | :-------------------------------- |
| ProductID (PK)          | INTEGER | Unique ID                         |
| ProductName             | TEXT    | Product name                      |
| Barcode                 | TEXT    | UPC/EAN code                      |
| SupplierID (FK)         | INTEGER | Supplier reference                |
| CostPrice               | REAL    | Purchase cost                     |
| MarkupPercentage        | REAL    | Markup multiplier                 |
| SellingPrice            | REAL    | Computed selling price            |
| StockQuantity           | REAL    | Quantity in stock (units or grams)|
| MinimumStockThreshold   | REAL    | Alert threshold                   |
| SoldByWeight            | BOOLEAN | Flag: 0 = per unit, 1 = by weight |

#### Suppliers
| Field          | Type    | Description   |
| :------------- | :------ | :------------ |
| SupplierID (PK)| INTEGER | Unique ID     |
| SupplierName   | TEXT    | Name          |
| ContactDetails | TEXT    | Phone/email   |

#### Transactions
| Field           | Type    | Description                  |
| :-------------- | :------ | :--------------------------- |
| TransactionID (PK)| INTEGER | Unique ID                    |
| DateTime        | TEXT    | Timestamp                    |
| TotalAmount     | REAL    | Total transaction value      |
| PaymentMethod   | TEXT    | Cash / NETS / Credit / PAYNOW|

#### TransactionDetails
| Field             | Type    | Description                |
| :---------------- | :------ | :------------------------- |
| TransactionDetailID | INTEGER | Unique ID                  |
| TransactionID (FK)| INTEGER | Parent transaction         |
| ProductID (FK)    | INTEGER | Product reference          |
| Quantity          | REAL    | Number of units or weight in grams|
| SellingPrice      | REAL    | Price per unit/gram        |
| LineTotal         | REAL    | Total for this item        |

#### Users (Optional, for roles)
| Field       | Type    | Description          |
| :---------- | :------ | :------------------- |
| UserID (PK) | INTEGER | Unique ID            |
| Username    | TEXT    | Login name           |
| Role        | TEXT    | Cashier / Manager / Admin|

---

## 3. Workflows

### 3.1 Sales Transaction Workflow
1.  Cashier scans product barcode.
2.  POS retrieves product from database.
3.  If product is `SoldByWeight = False`: add as 1 unit.
4.  If `SoldByWeight = True`: prompt cashier to weigh item.
    *   Cashier selects "Weigh Product".
    *   POS reads weight from scale.
    *   Line total = weight × selling price/kg.
5.  POS updates transaction list + running total.
6.  Cashier selects payment method.
    *   **Cash**: open cash drawer.
    *   **NETS/Credit**: record method only.
    *   **PAYNOW**: generate QR code with vendor bank details + total.
7.  Receipt handling:
    *   If Auto Print → send receipt to printer.
    *   If Manual Print → prompt cashier.
8.  Transaction saved to `Transactions` + `TransactionDetails`.

### 3.2 Stock Alert Workflow
1.  After every sale, `StockQuantity` updated.
2.  If `StockQuantity <= MinimumStockThreshold`:
    *   POS logs an alert (optional: send message/email).

---

## 4. Hardware Integration Notes

*   **Barcode Scanner**: No coding needed (acts as keyboard).
*   **Receipt Printer**: Use Epson ESC/POS commands via Python (e.g., `python-escpos`).
*   **Cash Drawer**: Opened by sending pulse command through printer.
*   **Weighing Machine**: Use Python `pyserial` to read COM port values.
    *   Example: scale outputs "WT: 2.345 kg".
    *   POS parses numeric value, converts to grams, and multiplies by price.
*   **Customer Display**: Run second window (Tkinter, PyQt, or Pygame) in fullscreen mode showing product list + total.

---

## 5. Reports

*   Daily Sales Report (by date, totals).
*   Product Sales Report (top-selling items, weight/units).
*   Payment Method Report (totals by cash, NETS, credit, PAYNOW).
*   Stock Report (current stock levels, low-stock alerts).

---

## 6. Security & Access

*   Restrict config settings (receipt printing mode, product pricing, supplier updates) to Admin role.
*   Cashiers only handle transactions.
*   Managers can view reports.

---

## 7. Deployment Notes

*   **OS**: Windows 10/11 Pro (embedded PC).
*   **Dependencies**: Python 3.x, SQLite, `pyserial`, `python-escpos`, GUI toolkit (Tkinter/PyQt).
*   **Installation**:
    *   Install Python + dependencies.
    *   Install Epson printer driver.
    *   Configure secondary display.
    *   Connect weighing machine via USB/COM.