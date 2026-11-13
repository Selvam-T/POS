# POS Technical Overview

This document describes the POS application's implementation stack, source
layout, and runtime/peripheral context. It is not the system workflow or
database-schema reference; see `System Documentation.md` for those topics.

## Technology Stack

| Area | Current implementation |
|---|---|
| Application | Python desktop application |
| GUI | PyQt5 with Qt Designer `.ui` files and QSS stylesheets |
| Database | SQLite |
| Product lookup | In-memory cache loaded from the product database |
| Source-development baseline | CPython 3.12.10, 64-bit |
| Production distribution | PyInstaller bundle with its runtime included |

`Project/requirements.txt` is the authoritative dependency manifest. It
currently declares PyQt5, pynput, lxml, jsbeautifier, python-escpos, openpyxl,
xlwt, qrcode, and Pillow. Use `Python Environment.md` for the canonical
environment setup, verification steps, and production-build cautions.

## Source Layout

| Location | Responsibility |
|---|---|
| `Project/main.py` | Application entry point and top-level UI composition. |
| `Project/modules/db_operation/` | SQLite connections, repositories, product cache, and receipt commit services. |
| `Project/modules/sales/` | Sales panel and sale-entry, hold, and recovery dialogs. |
| `Project/modules/payment/` | Payment panel, QR generation, receipt generation, and refund workflow. |
| `Project/modules/devices/` | Barcode scanner handling and printer/cash-drawer helpers. |
| `Project/modules/customer_display/` and `Project/modules/main_window/` | Customer-display UI and its controller integration. |
| `Project/ui/` | Qt Designer interface definitions. |
| `Project/assets/qss/` | Application stylesheets. |

For code-level behavior, see the focused documents in
`Project/Documentation/`.

## Runtime and Peripheral Context

- **Barcode scanner:** Scanner input is routed through the application's
  scanner/focus handling. The scanner is not assumed to be a serial device.
- **Receipt printer and cash drawer:** Printer and drawer helpers are part of
  the application. The connected printer model and transport are
  deployment-specific.
- **Customer display:** The project contains a customer-display component
  integrated with the main window.
- **Weighing scale:** Vegetable entry supports weight-based product workflows,
  but this overview does not claim that a serial scale is integrated.

The device manager feature for configuring scanners, printers, and scales was
shelved and is outside the current project scope.

## Deployment

The production application is distributed as a PyInstaller bundle whose
runtime is part of the deployed application folder. Source development and
testing use the local Python environment described in `Python Environment.md`.
Before a new production bundle is released, validate both the source
application and the packaged executable with the target devices and workflows.
