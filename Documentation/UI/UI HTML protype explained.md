# POS Sales Table UI Prototype in HTML Documentation  
### \*\*\*HTML prototype to be converted to tkinter/ ttkbootstrap\*\*\*

## Main Window Panel 1 – Sales Table UI

### Overview
This HTML prototype represents the **Point-of-Sale (POS) Sales Table Interface**.  
It visualizes the structure, layout, and expected interactivity of the sale transaction window for a standalone retail POS system.  
The prototype includes elements such as the sales transaction table, category buttons, total summary, and control buttons for cancel, on-hold, and view-hold operations.

---

### Layout Description
- **Frame**: The entire UI is enclosed within a bordered frame with a light blue background.
- **Table**: Displays sale transaction items with alternating light-blue and white row colors. The columns include:
  - `X` Button (remove item)
  - Name
  - `-` Button (decrease quantity)
  - Qty (current quantity)
  - `+` Button (increase quantity)
  - Unit Price
  - Total  
- The table has a **default visible height of 15 rows**.  
  - If the number of items exceeds 15, a **vertical scrollbar** automatically appears on the right side of the table.  
  - The scrollbar spans exactly the height of the 15 visible rows of `<td>` elements.  
  - The header row (`<th>`) remains fixed and does not scroll with the table body.  
  - Horizontal scrolling is disabled to maintain alignment and consistent layout within the bordered frame.
- **Buttons Below Table**: Three centered buttons — *Add Miscellaneous*, *Add Vegetables*, and *Add Barcode* — serve to add items into the transaction list.
- **Total Section**: Shows the running total. The text label (“Total:”) is left-aligned, and the value (“$100.99”) is right-aligned within a bordered green box.
- **Bottom Buttons**: *CANCEL* (dark gray), *ON HOLD* (orange), and *VIEW HOLDS* (blue) are centered below the total section.

---

### Functional Specifications
#### 1. Row Controls
- **`X` Button**
  - Removes the selected item row from the table.
  - Also deletes related data objects: receipt entry, customer display entry, and transaction object.
  - Deducts the item’s total price from the overall sale total.

- **`-` Button (Decrement Quantity)**
  - Decreases the quantity of the selected item by one.
  - Updates the displayed quantity and recalculates both the item total and overall sale total.
  - Minimum quantity cannot go below 1.

- **`+` Button (Increment Quantity)**
  - Increases the quantity of the selected item by one.
  - Updates the displayed quantity and recalculates the item total and sale total.

#### 2. Add Item Buttons
- **`Add Barcode` Button**
  - Opens a window to scan or enter a barcode.
  - **Does not directly add products to the sale transaction.**  
    Instead, it adds new products to the **price list table** in the database and **reloads the price list into memory**.
  - When scanning a barcode during a sale:
    - If the product **exists** in the price list, it is fetched and displayed in the sale table.
    - If the product **is not found**, a window appears with a `<h3>` message:  
      *“The product is not in the price list.”*
      Input fields to add product details.  
      At the bottom of the window:
        - **CANCEL** button → closes the window without changes.
        - **OK** button → adds the product to the price list table, reloads the price list into memory, **and adds the item to the current sale transaction table.**

- **`Add Vegetables` Button**
  - Opens a window with two horizontal panels:
    - **Panel 1 (Selection Panel):** Displays up to 10 vegetable buttons (based on `vegetables` table records).
      - If there are more than 10 vegetables, navigation buttons appear for paging.
    - **Panel 2 (Weighed Items Panel):** Lists all weighed vegetables with name, weight (grams), and total price.
      - Includes buttons for:
        - Reading from the digital weighing machine
        - Adding weight manually
        - Removing an item (X button before each row)
        - Cancelling the operation
        - **Add to Sale** — which transfers all listed vegetables to the main transaction table and closes the window.
  - The system recalculates totals when items are added or removed.

- **`Add Miscellaneous` Button**
  - Opens a window with input fields for:
    - Item name (optional)
    - Quantity (optional)
    - Price
  - Adds an entry to the sale table as “Miscellaneous” if no name is given.

#### 3. Transaction Management
- **`CANCEL` Button**
  - Clears all items from the sale transaction table.
  - Resets total to $0.00.
  - Clears any receipt, display, or transaction objects associated with the session.

- **`ON HOLD` Button**
  - Saves the current sale transaction (including receipt number) into the *On Hold* table.
  - Then reset the sales Transaction table, ready for next transaction.
  
- **`VIEW HOLDS` Button**
  - Opens a new window listing all receipts currently *on hold*.
  - Each row in the list displays key details such as receipt number, date, and total.
  - The cashier can select a receipt from the list to **load the corresponding transaction** back into the sales table for continuation.

---

### Data Handling Logic
- When a barcode input is received:
  - The app looks up the **price_list** (loaded in memory).
  - Fetches and displays the item **Name**, **Unit Price**, and sets **Qty = 1** by default.
  - Calculates **Item Total = Unit Price × Quantity**.
  - Adds the item total to the **Sale Total**.
- Subsequent updates (add/remove/decrement/increment) dynamically recalculate and update the displayed totals.

---

## POS Panel 2 – Payment Panel Design Overview

The Payment Panel is divided into three main sections:

### Payment Methods
This section presents four payment options:
- **CASH**
- **NETS**
- **PAYNOW**
- **VOUCHER**

Each payment method row consists of:
- A button to select the payment type.
- An input field where the cashier enters the payment amount.
- A green tick (✔) button to confirm the entered amount.
- A red X button to clear the input field.

#### Behavior Logic
- The cashier can select one or multiple payment methods.
- When **CASH** is chosen and the entered amount ≥ total sale amount, all other payment methods become grayed out (disabled).
- When the user presses the **green tick**, the entered amount is validated against the payable total.
- The **red X** instantly clears that row’s input field.
- If the user fills multiple methods but presses the tick on one of them first:
  - Only that payment method is validated.
  - All other payment fields are cleared automatically.
- Once validated, the *Amount Paid* and *Change Due* fields update below the section.

> **Note:** None of these buttons open new windows or pop-ups. The interaction remains contained within the payment panel.

---

### Keypad Section
A numeric keypad provides quick entry of payment amounts.

- Digits (0–9) and double-zero (00) allow fast manual input.
- `$10`, `$50`, `$100` shortcut buttons insert preset cash amounts.
- **Backspace (⌫ Bksp)** deletes the last digit entered in the active input field.

This keypad is purely for entering amounts; it does not trigger calculations or confirmations.

---

### Refund Section
The refund interface includes:
- **REFUND** button
- **Scan Barcode** input field
- **Refund Amount** display

#### Behavior Logic
- The cashier must press the **REFUND** button before scanning.
- Only then does the system interpret the scanned input as a refund barcode.
- If the Refund button is not pressed, the scanned input will be treated as a sale transaction and appear in Panel 1 instead.
- Once a barcode is scanned while refund mode is active, the product’s price is automatically retrieved and displayed as the *Refund Amount*.

---

### 💡 Summary
| Section | Purpose | Key Interaction |
|----------|----------|----------------|
| Payment Methods | Enter and confirm multiple payment types | Validate with ✔ ; clear with X |
| Keypad | Input numeric amount into active field | Backspace = remove last digit |
| Refund Section | Handle refund transactions | Refund button → activate refund mode |

---

**This document serves as the design and functional reference for implementing both the Sale Transaction Table (Panel 1) and the Payment Panel (Panel 2) in the POS application.**