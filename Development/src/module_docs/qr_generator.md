# QR Generator

Summary
-------
`modules/payment/qr_generator.py` builds a PayNow-style dynamic QR payload and renders a QR image suitable for Screen 2 (`screen2QrLabel`).

Key points
----------
- The generator no longer embeds an amount in the QR payload so customers' banking apps will not pre-fill payment amounts.
- This is intentional because POS payment confirmation is not integrated with the banking app; the cashier verifies and records the final payment manually.
- A generic QR avoids stale or incorrect amount QR codes when the cart or payment allocation changes.
- The default reference used in the QR is `merchant_name` from `config.py`, matching the manual preview script's reference rendering path.
- The public API for Screen 2 is `generate_qr_pixmap(ref_value: str | None = None, target_size: int = 250)` which returns a `QPixmap` ready to set on a `QLabel`.
- The QR image includes an overlaid logo and a rounded white card background to match the app styling.

Usage in `customer_display`
---------------------------
Call `generate_and_set_qr(ref=None, size=250)` on the `CustomerDisplayWindow` instance to place the QR into `screen2QrLabel`.

By default, Screen 2 uses generated QR rendering. If
`CUSTOMER_DISPLAY_USE_STATIC_QR_IMAGE` is enabled in `config.py`,
`CustomerDisplayWindow` first tries to load
`assets/images/<CUSTOMER_DISPLAY_QR_IMAGE_FILENAME>` and display that image
instead. If the configured static image is missing or cannot be loaded, the
missing/invalid file is logged and the existing generated QR path is used as
the fallback.

Implementation notes
--------------------
- Currency/MCC/expiry are retained in the payload for compatibility with PayNow scanners, but the amount tag is intentionally omitted.
- Keep the generated card aspect ratio and transparent rounded corners; `target_size` controls the maximum rendered dimension.
- The function depends on PyQt5 to convert the PIL image to a `QPixmap`.

Security and privacy
--------------------
- Because the QR does not include an amount, customers enter the cashier-confirmed payment value manually in their banking apps.
- Reference strings are trimmed to 25 characters to avoid oversized TLV entries.
