## 🧩 POS Technical Overview

### 1. Introduction
This document provides the primary technical overview of the **Point-of-Sale (POS)** system designed for a standalone retail store.  
It outlines the environment setup, dependencies, hardware integration, and software architecture.

The POS runs on **Windows 11**, using **Python 3.13** as the main interpreter. It interfaces with multiple hardware components:
- **Honeywell barcode scanner** (HID or Serial mode)
- **Epson TM-T82x receipt printer** (ESC/POS over Ethernet or USB)
- **Cash drawer** (triggered via RJ-45 through printer)
- **Digital weighing scale** (planned future integration)

The user interface is built using **Tkinter** with **ttkbootstrap**, and data is stored locally in an **SQLite** database.

---

### 2. Environment Setup Summary
Two Python environments exist on the system:

1. **Standalone Python 3.13**  
   - Location: `C:\Users\SELVAM\AppData\Local\Programs\Python\Python313\`  
   - Default interpreter used for all POS development.  
   - All dependencies installed here.

2. **Miniconda Environment**  
   - Originally used for the AIAP Machine Learning project.  
   - Not required for POS development unless isolated environments are needed.

**Verify active interpreter:**
```sh
python -c "import sys; print(sys.executable)"
```

**Install dependencies:**
```sh
python -m pip install pyserial pyusb python-escpos pynput PyQt5 ttkbootstrap
```

**Confirm installation:**
```sh
pip show pyserial
pip show ttkbootstrap
```

---

### 3. Python Dependencies and Built-in Modules

| Package | Purpose |
|----------|----------|
| **pyserial** | Serial communication with barcode scanner or weighing scale. |
| **pyusb** | Low-level USB communication for non-COM devices. |
| **python-escpos** | ESC/POS printing library for Epson TM-T82x. |
| **pynput** | Keyboard/mouse input monitoring and emulation. |
| **PyQt5** | Optional GUI framework alternative to Tkinter. |
| **ttkbootstrap** | Modern theme enhancement for Tkinter GUI. |

**Built-in Modules**

| Module | Purpose |
|----------|----------|
| **tkinter** | GUI toolkit for the main POS interface. |
| **sqlite3** | Lightweight embedded database for local data storage. |

---

### 4. Technology Stack

| Component | Tool |
|------------|------|
| Operating System | Windows 11 |
| Programming Language | Python 3.13 |
| GUI Framework | Tkinter + ttkbootstrap |
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
- The initial prototype was built in **HTML/CSS**, then translated to **Tkinter/ttkbootstrap**.
- Refer to `UI_Design_POS.md` for the detailed layout structure and widget hierarchy.
- Uses ttkbootstrap components like `Tableview`, `ToastNotification`, and input validation (`add_regex_validation`).
- Panels are organized as class-based frames:
  - **Panel 1** – Sales Transaction
  - **Panel 2** – Payment & Refund
  - **Panel 3** – Menu / Settings
- Preferred themes: *Simplex*, *Sandstone*, and *Solar* (rated 4/5).

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
The system is now configured to run under **Standalone Python 3.13**, with all dependencies installed and hardware components verified. The POS uses an event-driven model, modern Tkinter UI, and local database integration — providing a strong foundation for further feature development such as configuration menus, scale input, and multi-display support.