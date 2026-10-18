# Historical POS User Interface Prototype

> This is a historical Tkinter/ttkbootstrap prototype. The current POS application uses PyQt5 with Qt Designer `.ui` files; use `Project/README.md` and `Project/Documentation/` for current implementation guidance.

## Introduction
The initial POS interface was first prototyped in **HTML/CSS** to visualize layout, spacing, and color combinations. 
That served as a blueprint for converting the design to a native **Python GUI** built using **Tkinter** with **ttkbootstrap** themes, 
ensuring a touch-friendly, modern, and event-driven desktop interface. 
This document describes the **UI structure**, component mapping, and functional layout in the ttkbootstrap implementation.

---

## 🧱 UI Structure Overview

```
POSApp (ttkbootstrap.Window)
 ├─ TopBar (burger icon + title)
 ├─ Sidebar (collapsible)
 └─ MainLayout (2 columns)
     ├─ Panel1_Transaction
     │    ├─ Tableview (Sales Items)
     │    ├─ Category Buttons
     │    ├─ Total Section
     │    └─ Bottom Buttons
     └─ Panel2_Payment
          ├─ Payment Methods
          ├─ Summary (Amount Tendered / Change Due)
          ├─ Keypad (numeric input)
          └─ Refund Section
```

---

## 🎨 ttkbootstrap Theme
Preferred theme: **simplex**  
Other acceptable themes: *sandstone*, *solar*, *darkly*  
The chosen theme maintains bright contrast, modern buttons, and soft corner radius for a clean retail interface.

---

## 🧩 Panel 1 – Transaction Area

### Components
| Section | Widget Type | Description |
|----------|--------------|--------------|
| Sales Table | `Tableview` | Displays scanned or selected items with editable Quantity (`Qty`) column. |
| Category Buttons | `ttk.Button` | “Add Vegetable”, “Add Miscellaneous”, etc. for quick product entry. |
| Total Section | `ttk.Label` | Displays running total; bound to a `StringVar`. |
| Bottom Buttons | `ttk.Button` | CANCEL, ON HOLD, and VIEW HOLDS operations. |

### Behavior
- The **Tableview** supports row insertion when a barcode is scanned.  
- Quantity updates automatically recalculate subtotal and total.  
- CANCEL clears all rows; ON HOLD stores transaction temporarily.

---

## 💳 Panel 2 – Payment Section

### Components
| Section | Widget | Purpose |
|----------|---------|----------|
| Payment Methods | Frame of Buttons + Entry + Check + Clear | CASH, NETS, PAYNOW, VOUCHER methods, each with input and validation. |
| Amount Summary | `ttk.Label` | Displays calculated Amount Tendered and Change Due. |
| Keypad | `ttk.Button` grid | Allows numeric entry to currently active input field. |
| Refund Section | `Frame` | REFUND button + barcode input for processing returns. |

### Behavior
- Pressing ✔ validates input for the selected payment method.  
- Only one method can finalize the payment at a time.  
- Change Due auto-updates when Amount ≥ Total.  
- Refund section handles scanned barcodes and shows refund amount.

---

## 🍔 Sidebar Menu

### Structure
- Burger icon (☰) at top-left toggles sidebar visibility.  
- Sidebar contains buttons like:
  - AI (Product Info, Remedy, Cooking, Benefits)
  - Receipt (Greeting configuration)
  - Product Management
  - Reports
  - Cash Drawer
  - Login / Logout

### Behavior
- Sidebar slides in/out using `.place()` animation.  
- Disappears on outside mouse click or when ESC pressed.  
- Future integration: link menu buttons to corresponding management windows.

---

## ⚙️ Event-Driven Design Notes
- **No continuous loop** for polling — relies on UI events (button clicks, keypresses, barcode input).  
- Barcode input handled through focused Entry widget or event binding.  
- Future enhancements may use an application-wide event dispatcher for:
  - BARCODE_SCANNED
  - PAYMENT_CONFIRMED
  - REFUND_PROCESSED

---

## 📦 Next Steps
1. Implement full layout in Python (`POSApp` class).  
2. Add dynamic data binding to SQLite inventory.  
3. Integrate hardware events (barcode scanner, cash drawer, printer).  
4. Update this document as components evolve.

---

*Document version 1.0 — last updated automatically.*
