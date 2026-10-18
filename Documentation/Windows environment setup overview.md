## 🧩 POS Technical Overview

### 1. Introduction
This document provides the primary technical overview of the **Point-of-Sale (POS)** system designed for a standalone retail store.  
It outlines the environment setup, dependencies, hardware integration, and software architecture.

The POS runs on **Windows 10/11**, using **CPython 3.12.10 (64-bit)** for source development. It interfaces with multiple hardware components:
- **Honeywell barcode scanner** (HID or Serial mode)
- **Epson TM-T82x receipt printer** (ESC/POS over Ethernet or USB)
- **Cash drawer** (triggered via RJ-45 through printer)
- **Digital weighing scale** (planned future integration)

The user interface is built with **PyQt5** and Qt Designer `.ui` files, and data is stored locally in an **SQLite** database.

---

### 2. Environment Setup Summary

Create a project-local virtual environment from the repository root. This keeps the POS dependencies separate from other Python projects:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r Project\requirements.txt
python --version
python -m pip check
```

The version command must report `Python 3.12.10`. See `Python Environment.md` for the canonical setup and the Python install manager fallback.

---

### 3. Python Dependencies and Built-in Modules

| Package | Purpose |
|----------|----------|
| **python-escpos** | ESC/POS printing library for Epson TM-T82x. |
| **pynput** | Keyboard/mouse input monitoring and emulation. |
| **PyQt5** | Cashier and customer-display GUI framework. |
| **qrcode / Pillow** | PayNow QR and image rendering support. |
| **openpyxl / xlwt** | XLSX and legacy XLS report export. |

**Built-in Modules**

| Module | Purpose |
|----------|----------|
| **sqlite3** | Lightweight embedded database for local data storage. |

---

### 4. Technology Stack

| Component | Tool |
|------------|------|
| Operating System | Windows 11 |
| Programming Language | CPython 3.12.10 |
| GUI Framework | PyQt5 |
| Database | SQLite |
| Communication | pyserial / python-escpos |
| Hardware | Barcode scanner, printer, cash drawer, weighing scale |

---

### 5. Architecture and Functional Flow
The POS application follows an **event-driven design**, remaining idle until user or hardware events occur.

**Typical workflow:**
1. Scan barcode using barcode reader.
2. Fetch product data from memory or SQLite database.
3. Display item and price in the sales transaction table.
4. Calculate total and process payment (Cash / NETS / PayNow / Voucher).
5. Print receipt and trigger cash drawer.

**Event examples:**
- `BARCODE_SCANNED` → updates table and total.
- `PAYMENT_CONFIRMED` → triggers receipt print and drawer.
- `REFUND_INITIATED` → opens refund panel for validation.

---

### 6. UI Development Notes
- The initial interface was prototyped in HTML/CSS. The current application is implemented in PyQt5.
- Qt Designer files under `Project/ui/` define the main window and dialogs; `Project/assets/qss/` provides styling.
- The active sales, payment, menu, and customer-display areas are assembled at runtime by `Project/main.py` and its controllers.

---

### 7. Hardware Integration Summary

| Device | Communication | Notes |
|---------|----------------|-------|
| **Barcode Scanner** | HID or Serial (COM port) | Honeywell Orbit MK/MS7120 verified; acts as keyboard input or serial reader. |
| **Receipt Printer** | ESC/POS over Ethernet or USB | Epson TM-T82x; margins and fonts tested with ESC/POS commands. |
| **Cash Drawer** | RJ-45 via Printer Pulse | Opens automatically after successful cash transaction. |
| **Weighing Scale** | Serial input (planned) | Integration will follow barcode and printer completion. |

---

### 8. Database & File Structure
The POS system uses a local **SQLite** database with the following key tables:

| Table | Purpose |
|--------|----------|
| `inventory` | Stores product and barcode information. |
| `supplier` | Supplier details and linked payouts. |
| `daily_transaction` | Records all sales with unique receipt IDs. |
| `refund` | Tracks customer refunds. |
| `credit_sale` | Manages sales on credit. |
| `cash_payout` | Logs cash disbursements to suppliers or expenses. |

**Project Directory Example:**
```
C:\Users\SELVAM\OneDrive\Desktop\POS\
```

---

### 9. Referenced Files
| File | Description |
|------|--------------|
| `UI_Design_POS.md` | UI layout, structure, and style guide. |
| `printer.py` | ESC/POS margin and font test script. |
| `README.md` | Original environment and dependency notes. |
| `.env` (planned) | For configuration variables like company name. |
| `POS_Technical_Overview.md` | This document – consolidated system overview. |

---

### 10. Summary
The verified source-development setup uses **CPython 3.12.10**, PyQt5, and a project-local virtual environment. The POS uses an event-driven UI and local SQLite database. Build and hardware validation are still required before deploying a new client package.
