"""Network receipt printer and cash drawer helper using python-escpos.

This module is the consolidated device wrapper for printing and cash-drawer
operations. It replaces the older `printer.py` module name for clarity.
"""
import threading

from config import PRINTER_IP, PRINTER_PORT
from modules.ui_utils.error_logger import log_error_message


def _set_receipt_style(printer, style: str) -> None:
    if style == "company":
        printer.set(align="left", font="a", width=1, height=2)
    elif style in ("table", "greeting"):
        printer.set(align="left", font="b", width=1, height=1)
    else:
        printer.set(align="left", font="a", width=1, height=1)


def _send_text(printer, text: str) -> None:
    printer.text(text or "")
    if text and not text.endswith("\n"):
        printer.text("\n")


def _send_with_escpos(
    receipt_text: str,
    ip: str,
    port: int,
    timeout: float,
    receipt_sections: list[dict[str, str]] | None = None,
) -> bool:
    try:
        from escpos.printer import Network
    except Exception as exc:
        try:
            log_error_message(f"python-escpos import failed: {exc}")
        except Exception:
            pass
        return False

    p = None
    try:
        p = Network(host=ip, port=port, timeout=timeout)
        if receipt_sections:
            for section in receipt_sections:
                _set_receipt_style(p, str(section.get("style") or "normal"))
                _send_text(p, str(section.get("text") or ""))
            _set_receipt_style(p, "normal")
        else:
            _send_text(p, receipt_text)
        p.cut()
        return True
    except Exception as exc:
        try:
            log_error_message(f"Printer send failed ({ip}:{port}): {exc}")
        except Exception:
            pass
        return False
    finally:
        if p is not None:
            try:
                p.close()
            except Exception:
                pass


def print_receipt(
    receipt_text: str,
    *,
    receipt_sections: list[dict[str, str]] | None = None,
    blocking: bool = True,
    timeout: float = 5.0,
) -> bool:
    """Send `receipt_text` to the configured network printer."""
    if not receipt_text:
        return False

    if blocking:
        return _send_with_escpos(receipt_text, PRINTER_IP, PRINTER_PORT, timeout, receipt_sections)

    try:
        thread = threading.Thread(
            target=_send_with_escpos,
            args=(receipt_text, PRINTER_IP, PRINTER_PORT, timeout, receipt_sections),
            daemon=True,
        )
        thread.start()
        return True
    except Exception as exc:
        try:
            log_error_message(f"Failed to start printer thread: {exc}")
        except Exception:
            pass
        return False


def _open_cash_drawer_escpos(pin: int, ip: str, port: int, timeout: float) -> bool:
    try:
        from escpos.printer import Network
    except Exception as exc:
        try:
            log_error_message(f"python-escpos import failed (cash drawer): {exc}")
        except Exception:
            pass
        return False

    p = None
    try:
        p = Network(host=ip, port=port, timeout=timeout)
        p.cashdraw(int(pin))
        return True
    except Exception as exc:
        try:
            log_error_message(f"Cash drawer pulse failed ({ip}:{port}, pin={pin}): {exc}")
        except Exception:
            pass
        return False
    finally:
        if p is not None:
            try:
                p.close()
            except Exception:
                pass


def open_cash_drawer(pin: int = 2, blocking: bool = True, timeout: float = 2.0) -> bool:
    """Send ESC/POS cash drawer pulse to configured network printer."""
    if blocking:
        return _open_cash_drawer_escpos(pin, PRINTER_IP, PRINTER_PORT, timeout)

    try:
        thread = threading.Thread(
            target=_open_cash_drawer_escpos,
            args=(pin, PRINTER_IP, PRINTER_PORT, timeout),
            daemon=True,
        )
        thread.start()
        return True
    except Exception as exc:
        try:
            log_error_message(f"Failed to start cash-drawer thread: {exc}")
        except Exception:
            pass
        return False
