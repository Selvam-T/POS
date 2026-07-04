# ANUMANI POS User Guide

This guide is for cashiers and store staff using the ANUMANI POS application.

## Starting the Application

For the production release:

1. Turn on the POS computer and connected devices.
2. Make sure the barcode scanner, receipt printer, cash drawer, and customer display are connected.
3. Double-click the POS application shortcut or `SelvamPOS.exe`.
4. Log in with the account provided by the administrator.

For a source/development copy:

```cmd
cd Project
python main.py
```

## Main Screen

The main screen is designed for daily sales work.

- The top header shows the date, company name, day, and time.
- The sales table shows products currently in the sale.
- The payment panel is used to complete payment.
- The right-side menu opens tools such as Admin, Reports, Vegetable, Product, Greeting, Device, and Logout.
- Status messages appear at the bottom of the screen when the system needs attention.

## Making a Sale

1. Scan the product barcode.
2. Confirm the item appears in the sales table.
3. Repeat for all customer items.
4. Edit quantity if needed.
5. Check the total amount.
6. Select the payment method.
7. Complete the payment.
8. Print or keep the receipt according to store procedure.

If a scanned product is not found, the Product screen may open so the item can be added.

## Adding Items Manually

Use manual entry only for items that do not have a barcode or are not in the product database.

1. Click the Manual Entry button.
2. Enter the product name, quantity, and unit price.
3. Confirm the entry.
4. The item is added to the current sale.

## Vegetable or Weight-Based Items

Use Vegetable Entry for configured vegetable or weight-based products.

1. Open Vegetable Entry.
2. Select the item.
3. Enter or confirm the quantity or weight.
4. Confirm the entry.
5. The item is added to the sales table.

Items sold by weight should be entered through Vegetable Entry instead of normal barcode scanning.

## Payment Methods

The POS supports common payment recording flows such as:

- Cash
- NETS
- Credit card
- PAYNOW
- Other supported store payment types

For cash payments, the cash drawer may open after the sale is completed. If the drawer or printer fails, follow the store recovery procedure and inform the supervisor.

## Holding a Sale

Use Hold when a customer needs to pause the transaction and return later.

1. Add the items to the sale as usual.
2. Choose Hold Sale.
3. Enter any required customer or note information.
4. Confirm the hold.

The sale is saved as unpaid and can be retrieved later.

## Viewing Held Sales

Use View Hold to load, print, or void held receipts.

1. Open View Hold.
2. Search or select the held receipt.
3. Choose the required action:
   - Load to continue the sale.
   - Load to pay.
   - Print.
   - Void.
4. Confirm the action.

View Hold is normally used only when there is no active sale already in progress.

## Receipt History

Receipt History lets staff search previous receipts.

Common filters include:

- Receipt number
- Receipt status
- Date or date range
- Product code or product name

Depending on permissions and receipt status, receipts may be viewed, printed, or voided.

## Reports

Reports are used to review sales and activity.

Available report options may include:

- Daily or date-range sales
- Payment method totals
- Product and category sales
- Cash outflows
- Summary or detailed report views

Some report options may be restricted to administrator users.

## Product Management

The Product screen is used to add, update, or remove products from the product list.

Typical product information includes:

- Product code or barcode
- Product name
- Unit
- Category
- Supplier
- Cost price
- Selling price

When a sale is already in progress, product update and remove functions may be restricted to protect the active sale.

## Admin Tools

Admin tools may include:

- Admin password changes
- Staff password changes
- Recovery email settings
- Product export
- Screen 2 advertisement settings

Access depends on the logged-in user role.

## Barcode Scanner Tips

- Scan products while the sales screen is active.
- In product, refund, or receipt dialogs, scan only when the product code field is active.
- Do not scan into quantity fields.
- If the scanner types into the wrong field, stop scanning and ask the supervisor to check focus or scanner setup.

## Logging Out

Use the Logout button in the right-side menu.

1. Finish, hold, or cancel the current sale.
2. Click Logout.
3. Confirm logout.

The window close button is disabled for normal operation. Always use Logout so the POS can stop the scanner and close cleanly.

## Basic Troubleshooting

If the POS does not start:

- Check that the POS database is available.
- Restart the POS application.
- Restart the POS computer if needed.
- Contact the supervisor or technical support.

If a product is not found:

- Check the barcode and scan again.
- Search or add the product through Product Management if permitted.
- Ask an administrator if the product should already exist.

If receipt printing fails:

- Check that the printer is powered on.
- Check paper and printer connection.
- Inform the supervisor before repeating payment or receipt actions.

If payment saving fails:

- Do not clear the sale immediately.
- Retry once if instructed by the status message.
- If the issue continues, place the sale on hold and inform the supervisor.

## Daily Good Practice

- Confirm the correct login user before serving customers.
- Keep the scanner pointed away from the keyboard when not scanning.
- Check totals before accepting payment.
- Use Hold instead of clearing a sale if the customer will return.
- Logout before leaving the counter.
