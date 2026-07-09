"""Receipt text generator for console printing (v1)."""

from __future__ import annotations

from datetime import datetime
from typing import List

import config
from modules.db_operation import receipt_repo
from modules.db_operation.users_repo import get_username_by_id
from modules.ui_utils.greeting_state import current_greeting
from modules.ui_utils.money_format import round_money


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
    rounded = round(float(qty), 2)
    if abs(rounded - round(rounded)) < 0.0001:
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def _left_width(width: int) -> int:
    return max(1, width - config.RECEIPT_AMOUNT_WIDTH - config.RECEIPT_GAP)


def _item_amount_width() -> int:
    return int(getattr(config, "RECEIPT_ITEM_AMOUNT_WIDTH", config.RECEIPT_AMOUNT_WIDTH))


def _item_left_width(width: int) -> int:
    return max(1, width - _item_amount_width() - config.RECEIPT_GAP)


def _center_line(text: str, width: int) -> str:
    return (text or "").strip().center(width)

def _left_line(text: str, width: int) -> str:
    return (text or "").strip().ljust(width)


def _line_with_amount(left_text: str, amount_text: str, width: int) -> str:
    left_width = _left_width(width)
    left = (left_text or "")[:left_width].ljust(left_width)
    amount = (amount_text or "").rjust(config.RECEIPT_AMOUNT_WIDTH)
    return f"{left}{' ' * config.RECEIPT_GAP}{amount}"


def _format_receipt_amount(amount: float) -> str:
    rounded = round_money(amount)
    if rounded < 0:
        return f"-$ {abs(rounded):.2f}"
    return f"$ {rounded:.2f}"


def _resolve_cashier_name(cashier_id: object) -> str:
    try:
        if cashier_id is None:
            return ""
        username = get_username_by_id(int(cashier_id))
        return str(username or "").strip()
    except Exception:
        return ""


def _item_line(qty: float, unit: str, unit_price: float, name: str, line_total: float, width: int) -> str:
    left_width = _item_left_width(width)
    item_amount_width = _item_amount_width()
    # Reserve space for: qty, one space, product name, one space, and unit price column
    product_width = max(1, left_width - (config.RECEIPT_QTY_WIDTH + 2 + item_amount_width))

    original_unit = unit

    if unit == "Each":
        unit = "ea"
    elif unit == "Kg":
        if qty < 1.0:
            unit = "g"
            qty *= 1000
        else:
            unit = "kg"

    qty_text = f"{_format_qty(qty)} {unit}".strip()[:config.RECEIPT_QTY_WIDTH].ljust(config.RECEIPT_QTY_WIDTH)
    raw_name = str(name or "")
    if len(raw_name) > product_width:
        if product_width <= 3:
            name_text = "." * product_width
        else:
            name_text = (raw_name[: product_width - 3] + "...")
    else:
        name_text = raw_name.ljust(product_width)
    price_text = f"{unit_price:.2f}".rjust(item_amount_width)
    # Single space between qty and name, and between name and unit price
    left_text = f"{qty_text} {name_text} {price_text}"
    amount_text = f"{line_total:.2f}"
    main_line = f"{left_text}{' ' * config.RECEIPT_GAP}{amount_text.rjust(item_amount_width)}"

    return main_line

def _item_header(width: int) -> str:
    left_width = _item_left_width(width)
    item_amount_width = _item_amount_width()
    # Reserve space for unit price column inside the left area so columns fit the receipt width
    product_width = max(1, left_width - (config.RECEIPT_QTY_WIDTH + 2 + item_amount_width))
    qty_text = "Qty".ljust(config.RECEIPT_QTY_WIDTH)
    hdr_name = "Product"
    if len(hdr_name) > product_width:
        name_text = hdr_name[:product_width]
    else:
        name_text = hdr_name.ljust(product_width)
    price_text = "Price".rjust(item_amount_width)
    left_text = f"{qty_text} {name_text} {price_text}"
    return f"{left_text}{' ' * config.RECEIPT_GAP}{'Total'.rjust(item_amount_width)}"


def _append_header_info(lines: List[str], width: int) -> None:
    lines.append(_center_line(str(getattr(config, "COMPANY_NAME", "")), width))
    lines.append(_center_line(str(getattr(config, "ADDRESS_LINE_1", "")), width))
    lines.append(_center_line(str(getattr(config, "ADDRESS_LINE_2", "")), width))
    lines.append("")


def _append_receipt_info(
    lines: List[str],
    *,
    receipt_no: str,
    cashier_name: str,
    created_text: str,
    width: int,
) -> None:
    lines.append(_left_line(f"Receipt id: {receipt_no}", width))
    if cashier_name:
        lines.append(_left_line(f"Served by : {cashier_name}", width))
    lines.append(_left_line(f"Date      : {created_text}", width))
    lines.append("")


def _items_table_sections(
    *,
    items: list[dict],
    width: int,
    qty_key: str,
    name_key: str,
    unit_key: str,
    unit_price_key: str,
    line_total_key: str,
    payable_total: float | None = None,
) -> tuple[list[str], list[str], float]:
    table_lines = [_item_header(width), "-" * width]

    total_amount = 0.0
    for item in items or []:
        qty = float(item.get(qty_key) or item.get("qty") or 0.0)
        unit = str(item.get(unit_key) or "").strip()
        unit_price = float(item.get(unit_price_key) or 0.0)
        name = str(item.get(name_key) or item.get("product_name") or "")
        line_total = float(item.get(line_total_key) or 0.0)
        total_amount += line_total
        table_lines.append(_item_line(qty, unit, unit_price, name, line_total, width))
    table_lines.append("-" * width)

    subtotal = round_money(total_amount)
    payable = round_money(payable_total if payable_total is not None else subtotal)
    rounding_adjustment = round_money(payable - subtotal)
    total_label = "Total (round):" if abs(rounding_adjustment) >= 0.01 else "Total:"
    summary_lines = [_line_with_amount(total_label, _format_receipt_amount(payable), width), ""]
    return table_lines, summary_lines, payable


def _append_items_table(
    lines: List[str],
    *,
    items: list[dict],
    width: int,
    qty_key: str,
    name_key: str,
    unit_key: str,
    unit_price_key: str,
    line_total_key: str,
    payable_total: float | None = None,
) -> float:
    table_lines, summary_lines, payable = _items_table_sections(
        items=items,
        width=width,
        qty_key=qty_key,
        name_key=name_key,
        unit_key=unit_key,
        unit_price_key=unit_price_key,
        line_total_key=line_total_key,
        payable_total=payable_total,
    )
    lines.extend(table_lines)
    lines.extend(summary_lines)
    return payable


def _append_payment_breakdown(
    lines: List[str],
    *,
    status: str,
    payments: list[dict] | None,
    payable_total: float,
    width: int,
) -> None:
    status_clean = str(status or "").strip().upper()
    if status_clean not in ("PAID", "UNPAID", "CANCELLED"):
        status_clean = "UNKNOWN"
    if status_clean != "PAID" or payments is None:
        lines.append(_center_line(f"Receipt Status is {status_clean}", width))
        return

    cash_tendered = 0.0
    total_tendered = 0.0
    cash_amount = 0.0
    for pay in payments:
        ptype = str(pay.get("payment_type") or "")
        tendered = float(pay.get("tendered") or 0.0)
        amount = float(pay.get("amount") or 0.0)
        total_tendered += tendered
        if ptype.upper() == "CASH":
            cash_tendered += tendered
            cash_amount += amount
            continue
        if ptype.upper() == "OTHER":
            ptype = "VOUCHER"
        lines.append(_line_with_amount(f"{ptype}:", f"$ {tendered:.2f}", width))

    # Compute change only from cash tendered. Voucher overpayments do not produce cash refunds.
    cash_change = max(0.0, round(cash_tendered - cash_amount, 2))
    overpaid = max(0.0, round(total_tendered - payable_total - cash_change, 2))

    if cash_tendered > 0:
        lines.append(_line_with_amount("Cash Tendered:", f"$ {cash_tendered:.2f}", width))
    lines.append("-" * width)
    lines.append(_line_with_amount("Total Tendered:", f"$ {total_tendered:.2f}", width))
    
    if cash_change > 0:
        lines.append("")
        lines.append(_line_with_amount("Cash Change:", f"$ {cash_change:.2f}", width))

    # Show voucher overpayment note when applicable
    if overpaid > 0:
        lines.append("")
        lines.append(_center_line("No change issued on voucher payment.", width))
        lines.append("-" * width)


def _append_greeting(lines: List[str], *, status: str, width: int) -> None:
    if str(status or "").strip().upper() == "PAID":
        lines.append("")
        lines.append(_center_line(current_greeting(), width))


def _receipt_sections_from_data(
    *,
    receipt_no: str,
    cashier_name: str,
    created_text: str,
    status: str,
    items: list[dict],
    payments: list[dict] | None,
    payable_total: float | None,
    width: int,
    qty_key: str,
    name_key: str,
    unit_key: str,
    unit_price_key: str,
    line_total_key: str,
    include_greeting: bool = True,
    extra_blank_before_payment: bool = True,
) -> list[dict[str, str]]:
    company_lines = [_center_line(str(getattr(config, "COMPANY_NAME", "")), width)]
    normal_lines = [
        _center_line(str(getattr(config, "ADDRESS_LINE_1", "")), width),
        _center_line(str(getattr(config, "ADDRESS_LINE_2", "")), width),
        "",
    ]
    _append_receipt_info(
        normal_lines,
        receipt_no=receipt_no,
        cashier_name=cashier_name,
        created_text=created_text,
        width=width,
    )

    table_lines, summary_lines, calculated_total = _items_table_sections(
        items=items,
        width=width,
        qty_key=qty_key,
        name_key=name_key,
        unit_key=unit_key,
        unit_price_key=unit_price_key,
        line_total_key=line_total_key,
        payable_total=payable_total,
    )

    payment_lines: list[str] = [""] if extra_blank_before_payment else []
    _append_payment_breakdown(
        payment_lines,
        status=status,
        payments=payments,
        payable_total=calculated_total,
        width=width,
    )

    sections = [
        {"style": "company", "text": "\n".join(company_lines)},
        {"style": "normal", "text": "\n".join(normal_lines)},
        {"style": "table", "text": "\n".join(table_lines)},
        {"style": "summary", "text": "\n".join(summary_lines + payment_lines)},
    ]

    if include_greeting:
        greeting_lines: list[str] = []
        _append_greeting(greeting_lines, status=status, width=width)
        if greeting_lines:
            sections.append({"style": "greeting", "text": "\n".join(greeting_lines)})
    return sections


def generate_receipt_text(receipt_no: str, width: int = config.RECEIPT_DEFAULT_WIDTH) -> str:
    try:
        header = receipt_repo.get_receipt_header_by_no(receipt_no)
        if not header:
            raise ValueError(f"Receipt not found: {receipt_no}")

        receipt_id = header.get("receipt_id")
        created_at_raw = str(header.get("created_at") or "")
        created_at = _format_datetime(created_at_raw)
        status = str(header.get("status") or "")
        cashier_name = _resolve_cashier_name(header.get("cashier_id"))
        header_total = float(header.get("grand_total") or 0.0)

        items = receipt_repo.list_receipt_items_by_no(receipt_no, receipt_id=receipt_id)
        payments = receipt_repo.list_receipt_payments_by_no(receipt_no, receipt_id=receipt_id)
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError("Receipt data unavailable.") from exc

    lines: List[str] = []
    # 1. header info
    _append_header_info(lines, width)
    # 2. receipt info
    _append_receipt_info(
        lines,
        receipt_no=receipt_no,
        cashier_name=cashier_name,
        created_text=created_at,
        width=width,
    )
    # 3. tabled items with receipt total
    payable_total = _append_items_table(
        lines,
        items=items,
        width=width,
        qty_key="qty",
        name_key="product_name",
        unit_key="unit",
        unit_price_key="unit_price",
        line_total_key="line_total",
        payable_total=header_total if header_total > 0 else None,
    )
    lines.append("")
    # 4. Payment breakdown depending on receipt status
    _append_payment_breakdown(
        lines,
        status=status,
        payments=payments,
        payable_total=payable_total,
        width=width,
    )
    # 5. greeting
    _append_greeting(lines, status=status, width=width)

    return "\n".join(lines)


def generate_receipt_sections(receipt_no: str, width: int = config.RECEIPT_DEFAULT_WIDTH) -> list[dict[str, str]]:
    try:
        header = receipt_repo.get_receipt_header_by_no(receipt_no)
        if not header:
            raise ValueError(f"Receipt not found: {receipt_no}")

        receipt_id = header.get("receipt_id")
        created_at_raw = str(header.get("created_at") or "")
        created_at = _format_datetime(created_at_raw)
        status = str(header.get("status") or "")
        cashier_name = _resolve_cashier_name(header.get("cashier_id"))
        header_total = float(header.get("grand_total") or 0.0)

        items = receipt_repo.list_receipt_items_by_no(receipt_no, receipt_id=receipt_id)
        payments = receipt_repo.list_receipt_payments_by_no(receipt_no, receipt_id=receipt_id)
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError("Receipt data unavailable.") from exc

    return _receipt_sections_from_data(
        receipt_no=receipt_no,
        cashier_name=cashier_name,
        created_text=created_at,
        status=status,
        items=items,
        payments=payments,
        payable_total=header_total if header_total > 0 else None,
        width=width,
        qty_key="qty",
        name_key="product_name",
        unit_key="unit",
        unit_price_key="unit_price",
        line_total_key="line_total",
    )


def generate_receipt_text_from_snapshot(
    *,
    items: list[dict],
    payments: list[dict] | None = None,
    receipt_no: str = "TEMP",
    status: str = "UNPAID",
    created_at: str | None = None,
    cashier_name: str = "",
    payable_total: float | None = None,
    width: int = config.RECEIPT_DEFAULT_WIDTH,
) -> str:
    created_text = _format_datetime(created_at) if created_at else _format_datetime(datetime.now().isoformat())
    lines: List[str] = []
    # 1. header info
    _append_header_info(lines, width)
    # 2. receipt info
    _append_receipt_info(
        lines,
        receipt_no=receipt_no,
        cashier_name=cashier_name,
        created_text=created_text,
        width=width,
    )
    # 3. tabled items with receipt total
    total_amount = _append_items_table(
        lines,
        items=items,
        width=width,
        qty_key="quantity",
        name_key="name",
        unit_key="unit",
        unit_price_key="unit_price",
        line_total_key="line_total",
        payable_total=payable_total,
    )
    # 4. Payment breakdown depending on receipt status
    _append_payment_breakdown(
        lines,
        status=status,
        payments=payments,
        payable_total=total_amount,
        width=width,
    )

    return "\n".join(lines)


def generate_receipt_sections_from_snapshot(
    *,
    items: list[dict],
    payments: list[dict] | None = None,
    receipt_no: str = "TEMP",
    status: str = "UNPAID",
    created_at: str | None = None,
    cashier_name: str = "",
    payable_total: float | None = None,
    width: int = config.RECEIPT_DEFAULT_WIDTH,
) -> list[dict[str, str]]:
    created_text = _format_datetime(created_at) if created_at else _format_datetime(datetime.now().isoformat())
    return _receipt_sections_from_data(
        receipt_no=receipt_no,
        cashier_name=cashier_name,
        created_text=created_text,
        status=status,
        items=items,
        payments=payments,
        payable_total=payable_total,
        width=width,
        qty_key="quantity",
        name_key="name",
        unit_key="unit",
        unit_price_key="unit_price",
        line_total_key="line_total",
        include_greeting=False,
        extra_blank_before_payment=False,
    )
