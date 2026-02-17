"""Network receipt printer helper using python-escpos."""
import threading

from config import PRINTER_IP, PRINTER_PORT
from modules.ui_utils.error_logger import log_error


def _send_with_escpos(receipt_text: str, ip: str, port: int, timeout: float) -> bool:
    try:
        from escpos.printer import Network
    except Exception as exc:
        try:
            log_error(f"python-escpos import failed: {exc}")
        except Exception:
            pass
        return False

    p = None
    try:
        p = Network(host=ip, port=port, timeout=timeout)
        p.text(receipt_text or "")
        if receipt_text and not receipt_text.endswith("\n"):
            p.text("\n")
        p.cut()
        return True
    except Exception as exc:
        try:
            log_error(f"Printer send failed ({ip}:{port}): {exc}")
        except Exception:
            pass
        return False
    finally:
        if p is not None:
            try:
                p.close()
            except Exception:
                pass


def print_receipt(receipt_text: str, blocking: bool = True, timeout: float = 5.0) -> bool:
    """Send `receipt_text` to the configured network printer."""
    if not receipt_text:
        return False

    if blocking:
        return _send_with_escpos(receipt_text, PRINTER_IP, PRINTER_PORT, timeout)

    try:
        thread = threading.Thread(
            target=_send_with_escpos,
            args=(receipt_text, PRINTER_IP, PRINTER_PORT, timeout),
            daemon=True,
        )
        thread.start()
        return True
    except Exception as exc:
        try:
            log_error(f"Failed to start printer thread: {exc}")
        except Exception:
            pass
        return False
