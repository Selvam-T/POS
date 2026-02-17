"""Receipt text generator for console printing (v1)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

import config
from modules.db_operation import receipt_repo


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_greeting() -> str:
    path = _project_root() / "AppData" / "greeting.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return str(data.get("selected", "")).strip()
    except Exception:
        return "Have a nice day !"


def _format_datetime(raw: str) -> str:
    if not raw:
        return ""

    parsed = None
    for fmt in (
        None,
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ):
        try:
            if fmt is None:
                parsed = datetime.fromisoformat(str(raw))
            else:
                parsed = datetime.strptime(str(raw), fmt)
            break
        except Exception:
            continue

    if parsed is None:
        return str(raw)

    text = parsed.strftime("%d %b %Y %I:%M %p")
    return text.replace("AM", "am").replace("PM", "pm")


def _format_qty(qty: float) -> str:
    if qty is None:
        return "0"
    rounded = round(float(qty), 3)
    if abs(rounded - round(rounded)) < 0.0001:
        return str(int(round(rounded)))
    return f"{rounded:.3f}".rstrip("0").rstrip(".")


def _left_width(width: int) -> int:
    return max(1, width - config.RECEIPT_AMOUNT_WIDTH - config.RECEIPT_GAP)


def _center_line(text: str, width: int) -> str:
    return (text or "").strip().center(width)


def _line_with_amount(left_text: str, amount_text: str, width: int) -> str:
    left_width = _left_width(width)
    left = (left_text or "")[:left_width].ljust(left_width)
    amount = (amount_text or "").rjust(config.RECEIPT_AMOUNT_WIDTH)
    return f"{left}{' ' * config.RECEIPT_GAP}{amount}"


def _item_line(qty: float, name: str, line_total: float, width: int) -> str:
    left_width = _left_width(width)
    product_width = max(1, left_width - (config.RECEIPT_QTY_WIDTH + 3))

    qty_text = _format_qty(qty)[:config.RECEIPT_QTY_WIDTH].ljust(config.RECEIPT_QTY_WIDTH)
    name_text = (name or "")[:product_width].ljust(product_width)
    left_text = f"{qty_text}  {name_text}"
    amount_text = f"${line_total:.2f}"
    return f"{left_text}{' ' * config.RECEIPT_GAP}{amount_text.rjust(config.RECEIPT_AMOUNT_WIDTH)}"


def _item_header(width: int) -> str:
    left_width = _left_width(width)
    product_width = max(1, left_width - (config.RECEIPT_QTY_WIDTH + 3))
    qty_text = "Qty".ljust(config.RECEIPT_QTY_WIDTH)
    name_text = "Product".ljust(product_width)
    left_text = f"{qty_text}  {name_text}"
    return f"{left_text}{' ' * config.RECEIPT_GAP}{'Total'.rjust(config.RECEIPT_AMOUNT_WIDTH)}"


def generate_receipt_text(receipt_no: str, width: int = config.RECEIPT_DEFAULT_WIDTH) -> str:
    try:
        header = receipt_repo.get_receipt_header_by_no(receipt_no)
        if not header:
            raise ValueError(f"Receipt not found: {receipt_no}")

        receipt_id = header.get("receipt_id")
        created_at_raw = str(header.get("created_at") or "")
        created_at = _format_datetime(created_at_raw)
        status = str(header.get("status") or "")

        items = receipt_repo.list_receipt_items_by_no(receipt_no, receipt_id=receipt_id)
        payments = receipt_repo.list_receipt_payments_by_no(receipt_no, receipt_id=receipt_id)
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError("Receipt data unavailable.") from exc

    total_qty = 0.0
    total_amount = 0.0
    for item in items:
        total_qty += float(item.get("qty") or 0.0)
        total_amount += float(item.get("line_total") or 0.0)

    cash_amount = 0.0
    cash_tendered = 0.0
    for pay in payments:
        ptype = str(pay.get("payment_type") or "").upper()
        amount = float(pay.get("amount") or 0.0)
        tendered = float(pay.get("tendered") or amount)
        if ptype == "CASH":
            cash_amount += amount
            cash_tendered += tendered

    change_amount = max(0.0, round(cash_tendered - cash_amount, 2))

    lines: List[str] = []
    lines.append(_center_line(str(getattr(config, "COMPANY_NAME", "")), width))
    lines.append(_center_line(str(getattr(config, "ADDRESS_LINE_1", "")), width))
    lines.append(_center_line(str(getattr(config, "ADDRESS_LINE_2", "")), width))
    lines.append("")
    lines.append(_center_line(f"Receipt id: {receipt_no}", width))
    lines.append(_center_line("Served by dummy", width))
    lines.append(_center_line(created_at, width))
    lines.append("")
    lines.append(_item_header(width))
    lines.append("-" * width)
    for item in items:
        qty = float(item.get("qty") or 0.0)
        name = str(item.get("product_name") or "")
        line_total = float(item.get("line_total") or 0.0)
        lines.append(_item_line(qty, name, line_total, width))
    lines.append("-" * width)

    lines.append(_line_with_amount("Grand Total:", f"${total_amount:.2f}", width))
    lines.append("")

    status_clean = status.strip().upper()
    if status_clean not in ("PAID", "UNPAID", "CANCELLED"):
        status_clean = "UNKNOWN"

    if status_clean != "PAID":
        lines.append(_center_line(f"Receipt Status is {status_clean}", width))
    else:
        for pay in payments:
            ptype = str(pay.get("payment_type") or "")
            amount = float(pay.get("amount") or 0.0)
            if ptype.upper() == "CASH":
                continue
            lines.append(_line_with_amount(f"{ptype}:", f"${amount:.2f}", width))

        if cash_amount > 0:
            lines.append(_line_with_amount("Cash Tendered:", f"${cash_tendered:.2f}", width))
            if change_amount > 0:
                lines.append("")
                lines.append(_line_with_amount("Cash Change:", f"${change_amount:.2f}", width))

    lines.append("")
    lines.append(_center_line(_load_greeting(), width))

    return "\n".join(lines)
