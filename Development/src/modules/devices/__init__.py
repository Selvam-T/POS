"""
Device modules for POS system.
Provides interfaces for hardware devices:
- scanner.py: Barcode scanner
- receipt_printer.py: Receipt printer (future)
- weighing_scale.py: Digital weighing scale (future)
- secondary_display.py: Customer display (future)
"""

from .scanner import BarcodeScanner

__all__ = ['BarcodeScanner']
