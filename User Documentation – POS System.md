# User Documentation – POS System

**System**: POS for Standalone Store  
**Platform**: Windows Embedded PC with secondary customer-facing display  

---

## 1. Introduction

This POS system allows store staff to scan products, process payments, print receipts, and manage inventory.  
It is designed for fast operation with barcode scanners, receipt printers, a cash drawer, and optional weighing machine.

---

## 2. System Requirements

*   Embedded POS PC with Windows 10/11.
*   Barcode scanner (USB).
*   Epson TM-T82X receipt printer (with cash drawer attached).
*   Optional digital weighing scale (USB/Serial).
*   Secondary screen for customer-facing display.

---

## 3. Starting the Application

1.  Power on the POS terminal.
2.  Double-click the **POS System** icon on the desktop.
3.  Login screen appears (if enabled):
    *   Enter **Username** and **Password**.
    *   Role determines access (Cashier / Manager / Admin).

---

## 4. Main Screen Overview

The main screen has:
*   **Transaction Area**: List of scanned items.
*   **Totals Section**: Subtotal, tax (if configured), and total.
*   **Payment Buttons**: Cash, NETS, Credit Card, PAYNOW.
*   **Receipt Options**: Print receipt (manual or auto).
*   **Menu**: Access reports, stock management, settings.

---

## 5. Performing a Sale

### Step 1: Scan Items
1.  Scan product barcode with the barcode reader.
2.  Product appears in the list with name, price, and quantity = 1.
3.  Repeat for multiple items.
4.  **If the product is sold by weight**:
    *   Scan product barcode.
    *   System prompts to weigh item.
    *   Place item on scale → weight is read automatically.
    *   Total is calculated (weight × unit price).

### Step 2: Review Items
1.  Check product names, quantities, and totals on screen.
2.  Items are also displayed on the customer-facing screen.

### Step 3: Select Payment Method
*   **Cash**:
    *   Select "Cash".
    *   Cash drawer opens automatically.
*   **NETS / Credit Card**:
    *   Select payment type.
    *   Complete payment externally on the terminal.
    *   Confirm in POS.
*   **PAYNOW**:
    *   Select "PAYNOW".
    *   System displays QR code with total and vendor’s bank details.
    *   Customer scans QR with their banking app.

### Step 4: Print Receipt
*   If **Auto Print** mode: receipt prints automatically.
*   If **Manual Print** mode: system asks “Print receipt?”
    *   Select “Yes” to print, “No” to skip.
*   **Cash drawer always opens when Cash is selected** (even if no receipt is printed).

---

## 6. Stock Management

From the **Menu → Inventory**:
*   View product list.
*   Update stock quantities.
*   Add new products (barcode, cost, markup, selling price).
*   System shows low-stock alerts when stock is below the threshold.

---

## 7. Reports

*   **Daily Sales Report**: Shows all transactions for the day.
*   **Product Sales Report**: Products sold, quantity, total sales value.
*   **Payment Method Report**: Breakdown of sales by cash, NETS, credit card, PAYNOW.
*   **Stock Report**: Current stock levels, low-stock alerts.

---

## 8. Settings

*   Configure receipt printing mode (Auto / Manual).
*   Update vendor bank details (for PAYNOW QR).
*   Manage user accounts (Admin only).

---

## 9. Troubleshooting

*   **Printer not printing**:
    *   Check power, USB connection, and paper roll.
    *   Restart POS application.
*   **Cash drawer not opening (cash payment)**:
    *   Ensure drawer is connected to printer.
    *   Test by printing a receipt.
*   **Scale not responding**:
    *   Check cable connection.
    *   Ensure "Weigh Product" option is selected for weight-based items.
*   **Barcode not scanning**:
    *   Ensure cursor is in the product input field.
    *   Check scanner cable.

---

## 10. Safety & Best Practices

*   Always close the day with a report before shutting down.
*   Back up the database file regularly.
*   Only Admins should update product prices and supplier info.
*   Keep cash drawer locked when not in use.