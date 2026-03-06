"""Shared receipt printing helper with console fallback."""
from __future__ import annotations

from typing import Dict

from config import ENABLE_PRINTER_PRINT
from modules.ui_utils.error_logger import log_error


def print_receipt_with_fallback(
    receipt_text: str,
    *,
    enable_printer: bool = ENABLE_PRINTER_PRINT,
    blocking: bool = True,
    context: str = "Receipt",
) -> Dict[str, object]:
    """Print receipt text using printer if enabled, else console fallback.

    Returns a dict with: ok (bool), mode ("printer"|"console"|"failed"), error (str|None).
    """
    result: Dict[str, object] = {
        "ok": False,
        "mode": "failed",
        "error": None,
    }

    if not receipt_text:
        result["error"] = "empty"
        return result

    if not enable_printer:
        print(receipt_text)
        result["ok"] = True
        result["mode"] = "console"
        return result

    try:
        from modules.devices import printer_and_drawer as device_printer

        printed_ok = device_printer.print_receipt(receipt_text, blocking=blocking)
        if printed_ok:
            result["ok"] = True
            result["mode"] = "printer"
            return result

        log_error(f"{context} print failed: printer send failed.")
        result["error"] = "send_failed"
        return result
    except Exception as exc:
        log_error(f"{context} print failed: {exc}")
        result["error"] = "exception"
        return result
