# QR Generator

Summary
-------
`modules/payment/qr_generator.py` builds a PayNow-style dynamic QR payload and renders a QR image suitable for Screen 2 (`screen2QrLabel`).

Key points
----------
- The generator no longer embeds an amount in the QR payload so customers' banking apps will not pre-fill payment amounts.
- The default reference used in the QR is `COMPANY_NAME` from `config.py` (falls back to `merchant_name`).
- The public API for Screen 2 is `generate_qr_pixmap(ref_value: str | None = None, target_size: int = 250)` which returns a `QPixmap` ready to set on a `QLabel`.
- The QR image includes an overlaid logo and a rounded white card background to match the app styling.

Usage in `customer_display`
---------------------------
Call `generate_and_set_qr(ref=None, size=250)` on the `CustomerDisplayWindow` instance to generate and place the QR into `screen2QrLabel`.

Implementation notes
--------------------
- Currency/MCC/expiry are retained in the payload for compatibility with PayNow scanners, but the amount tag is intentionally omitted.
- Keep the generated image square and provide a `target_size` parameter to control final pixel dimensions (default 250x250).
- The function depends on PyQt5 to convert the PIL image to a `QPixmap`.

Security and privacy
--------------------
- Because the QR does not include an amount, customers are not shown payment values on their banking apps.
- Reference strings are trimmed to 25 characters to avoid oversized TLV entries.

