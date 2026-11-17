# Business Requirements Document 
## Project: Point of Sale (POS) System for Standalone Store
* **Platform**: Windows-based embedded desktop all-in-one PC with secondary customer-facing display
* **Database**: SQLite
* **Prepared by**: Selvam / Vijay
* **Date**: 2 Oct 2025

---

## 1. Introduction
The POS system is intended to streamline sales transactions at a retail store.  
The system will allow the cashier to scan items, accept different forms of payment, capture transaction details, and optionally print receipts.  
It will integrate with hardware devices such as barcode readers, receipt printers, a cash drawer, and potentially a digital weighing machine.

---

## 2. Business Objectives
* Simplify the sales transaction process at the counter.
* Enable multiple payment options (cash, bank card, credit card, PAYNOW).
* Provide flexibility in receipt printing configuration.
* Track sales data for reporting and inventory control.
* Support weight-based product sales (e.g., groceries).
* Provide alerts for low stock levels to ensure timely replenishment.

---

## 3. Scope
### In-Scope
* Barcode scanning of products.
* Sales transaction processing with multiple payment options.
* Receipt printing (manual/automatic mode).
* Cash drawer integration.
* Customer-facing display (show items and total).
* Database design for products, suppliers, transactions, and reports.
* Basic reporting: daily transactions, sales reports by product/payment method.
* Stock management with minimum threshold alerts.
* Support for weight-based products (integration method TBD).

### Out-of-Scope (for now)
* Full accounting integration.
* Online payment gateway integration for NETS/Credit Card (only capturing payment type).
* Discounts and promotions (may be added later).
* Loyalty programs / membership management.
* Multi-store synchronization.

---

## 4. Functional Requirements

### 4.1 Sales Transactions

#### 1. Item Entry
* Cashier scans product barcode → product details (name, unit price) appear in transaction list.
* Each scan adds a row with product details.
* Cumulative total updates automatically.
* For weight-based items: cashier selects “weigh product” (workflow TBD), weight is read from digital weighing machine, multiplied by unit price/kg, and added to transaction.

#### 2. Payment Processing
* **Cash**: Cash drawer opens automatically.
* **NETS / Credit Card**: Payment handled externally, cashier records method in POS.
* **PAYNOW**: QR Code is generated showing vendor bank details and payable amount. Customer scans with bank app, verifies amount and merchant details, and completes payment.
* POS captures payment method for reporting.

#### 3. Receipt Printing
* Vendor can configure receipt printing mode:
    * **Auto Print**: receipt prints after every transaction.
    * **Manual Print**: prompt asks cashier “Print receipt? Yes/No”.
* Regardless of receipt printing, cash drawer must open if cash payment is selected.

---

### 4.2 Database Requirements

#### Core Tables

##### Products
* `ProductID` (PK)
* `ProductName`
* `Barcode`
* `SupplierID` (FK)
* `CostPrice`
* `MarkupPercentage`
* `SellingPrice` (calculated from CostPrice × MarkupPercentage)
* `StockQuantity`
* `MinimumStockThreshold`

##### Suppliers
* `SupplierID` (PK)
* `SupplierName`
* `ContactDetails`

##### Transactions
* `TransactionID` (PK)
* `DateTime`
* `TotalAmount`
* `PaymentMethod` (cash, NETS, credit card, PAYNOW)

##### TransactionDetails
* `TransactionDetailID` (PK)
* `TransactionID` (FK)
* `ProductID` (FK)
* `Quantity / Weight` (in grams)
* `SellingPrice`
* `LineTotal`

##### Users (Optional, for access control)
* `UserID` (PK)
* `Username`
* `Role` (Cashier, Manager, Admin)

#### Optional Future Tables
* Discounts/Promotions (rules, validity, product links).
* Audit Logs (recording voided/refunded transactions).

---

### 4.3 Reporting

* **Daily Sales Report**
    * TransactionID, Date/Time, TotalAmount, PaymentMethod.

* **Product Sales Report**
    * Products sold, quantity/weight, revenue.

* **Payment Method Summary**
    * Totals grouped by cash/NETS/credit card/PAYNOW.

* **Stock Alerts**
    * Products with StockQuantity ≤ MinimumStockThreshold.