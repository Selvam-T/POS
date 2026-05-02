"""Report viewer is the rendering layer. 
   It takes detailed/summary/chart/inactivity report data and builds the modal viewer UI.
"""

import re
from typing import Any, Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget
from modules.date_time.formatters import format_date, format_report_timestamp
import config

# Viewer size policy REPORT_VIEWER_RATIOS is in `config.py`.
# Keep a pixel fallback in case the shared ratio is not available at runtime.
DEFAULT_REPORT_VIEWER_SIZE = (760, 520)


def _detail_report_variant(report: dict) -> str:
    """Return the detailed-report presentation variant."""
    if not isinstance(report, dict):
        return 'full'
    variant = str(report.get('detail_variant') or report.get('_detail_variant') or 'full').strip().lower()
    return 'minimal' if variant == 'minimal' else 'full'


def _format_qty_unit(qty, unit) -> tuple[str, str]:
    """Format quantity and unit for report display."""
    try:
        qty_float = float(qty or 0.0)
    except Exception:
        qty_float = 0.0

    raw_unit = str(unit or '').strip()
    unit_lower = raw_unit.lower()

    if unit_lower in ('each', 'ea'):
        if 0 < qty_float < 1:
            return f'{qty_float:.2f}', 'ea'
        return str(int(round(qty_float))), 'ea'

    unit_txt = raw_unit or '-'
    if 'kg' in unit_lower:
        if qty_float < 1.0:
            gram_qty = qty_float * 1000
            if 0 < qty_float < 1.0:
                if gram_qty < 1:
                    return f'{gram_qty:.2f}', 'g'
                return f'{gram_qty:.0f}', 'g'
            return '0', 'g'
        return f'{qty_float:.2f}', 'kg'

    if 0 < qty_float < 1:
        return f'{qty_float:.2f}', unit_txt
    return f'{qty_float:.3f}', unit_txt


def _to_float(value) -> float:
    """Coerce a value to float with a 0.0 fallback."""
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _to_ampm_hour_label(hour_slot: Any) -> str:
    """Convert an hour range like '09:00 - 10:00' to AM/PM format."""
    text = str(hour_slot or '').strip()
    if not text:
        return ''

    try:
        parts = [part.strip() for part in text.split('-', 1)]
        if len(parts) != 2:
            return text
        start_txt, end_txt = parts

        from datetime import datetime

        start_dt = datetime.strptime(start_txt, '%H:%M')
        end_dt = datetime.strptime(end_txt, '%H:%M')

        start_label = start_dt.strftime('%I:%M %p').lstrip('0')
        end_label = end_dt.strftime('%I:%M %p').lstrip('0')
        return f'{start_label} - {end_label}'
    except Exception:
        return text


def _create_overlay(parent_dlg: QDialog):
    """Create a dim background overlay above the report menu dialog."""
    try:
        overlay = QWidget(parent_dlg)
        overlay.setObjectName('reportViewerOverlay')
        overlay.setGeometry(parent_dlg.rect())
        overlay.show()
        overlay.raise_()
        return overlay
    except Exception:
        return None


def _cleanup_overlay(overlay):
    """Dispose the dim background overlay if it exists."""
    try:
        if overlay is not None:
            overlay.hide()
            overlay.deleteLater()
    except Exception:
        pass


def _build_shell(parent_dlg: QDialog, *, report_type: str):
    """Create the modal viewer shell with titlebar close button."""
    rpt = str(report_type or 'summary').strip().lower()
    # Size from config ratios, with screen fallback.
    size_w, size_h = DEFAULT_REPORT_VIEWER_SIZE
    mw = mh = mx = my = 0
    try:
        # Find top-level parent window.
        ref = None
        if parent_dlg is not None:
            ref = parent_dlg
            while getattr(ref, 'parent', None) and ref.parent() is not None:
                ref = ref.parent()

        if ref is not None and hasattr(ref, 'frameGeometry'):
            geom = ref.frameGeometry()
            mw = geom.width()
            mh = geom.height()
            mx = geom.x()
            my = geom.y()
        else:
            # Screen fallback.
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            geom = screen.availableGeometry()
            mw = geom.width()
            mh = geom.height()
            mx = geom.x()
            my = geom.y()

        ratio = getattr(config, 'REPORT_VIEWER_RATIOS', None)
        if isinstance(ratio, (tuple, list)) and len(ratio) >= 2:
            size_w = int(mw * float(ratio[0]))
            size_h = int(mh * float(ratio[1]))
    except Exception:
        size_w, size_h = DEFAULT_REPORT_VIEWER_SIZE

    viewer = QDialog(parent_dlg)
    viewer.setObjectName('reportViewerDialog')
    viewer.setModal(True)
    viewer.setWindowModality(Qt.WindowModal)
    viewer.setWindowFlags(viewer.windowFlags() | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
    viewer.setWindowTitle(f"{rpt.capitalize()} Report Viewer")
    # Apply minimum size and center.
    try:
        min_w = viewer.minimumWidth()
        min_h = viewer.minimumHeight()
        final_w = max(min_w, int(size_w))
        final_h = max(min_h, int(size_h))
        viewer.resize(final_w, final_h)

        # Center over the reference window/screen.
        try:
            dw, dh = viewer.width(), viewer.height()
            dialog_x = mx + (mw - dw) // 2
            dialog_y = my + (mh - dh) // 2
            dialog_x = max(mx, min(dialog_x, mx + mw - dw))
            dialog_y = max(my, min(dialog_y, my + mh - dh))
            viewer.move(dialog_x, dialog_y)
        except Exception:
            pass
    except Exception:
        # Best-effort fallback
        viewer.resize(int(size_w), int(size_h))

    layout = QVBoxLayout(viewer)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)

    return viewer, layout


def _format_detailed_report_text(report: dict) -> tuple[str, set[str], set[str], set[str]]:
    """Render detailed report text and style metadata."""
    if not isinstance(report, dict):
        report = {}

    def _to_int(value) -> int:
        try:
            return int(value or 0)
        except Exception:
            return 0

    def _fmt_money(value) -> str:
        try:
            amount = float(value or 0.0)
        except Exception:
            amount = 0.0
        return f"$ {amount:,.2f}"

    def _truncate(text: str, width: int) -> str:
        s = str(text or '')
        if len(s) <= width:
            return s
        if width <= 3:
            return s[:width]
        return s[: width - 3] + '...'

    sales = report.get('sales_summary') or {}
    payments = report.get('payment_breakdown') or []
    categories = report.get('categories') or []
    top_products = report.get('top_products') or []
    outflows = report.get('cash_outflows') or []
    excluded = report.get('excluded') or {}
    header = report.get('header') or {}

    bold_lines: set[str] = set()
    table_header_lines: set[str] = set()
    blue_lines: set[str] = set()
    
    gross_line = f"{'Gross Sales':<24} : {_fmt_money(sales.get('gross_sales')):>12}"
    net_line = f"{'Net After Outflow':<24} : {_fmt_money(sales.get('net_after_outflows')):>12}"

    lines = [
        'Sales Record & Totals',
        '=' * 72,
        f"Period From   : {format_report_timestamp(header.get('period_from'))}",
        f"Period To     : {format_report_timestamp(header.get('period_to'))}",
        '',
        f"Generated At  : {format_report_timestamp(header.get('generated_at'))}",
        f"Generated By  : {header.get('generated_by') or '-'}",
        '',
        '1. Sales Overview',
        '-' * 72,
        f"{'PAID Receipt Count':<24} : {_to_int(sales.get('paid_receipt_count')):>8}",
        gross_line,
        '',
        f"{'Refund Outflow':<24} : {_fmt_money(sales.get('less_refund_outflow')):>12}",
        f"{'Vendor Outflow':<24} : {_fmt_money(sales.get('less_vendor_outflow')):>12}",
        '',
        net_line,
        '',
        '2. Earnings Received (By Payment Type)',
        '-' * 72,
    ]

    blue_lines.add(gross_line)
    blue_lines.add(net_line)
    is_minimal = _detail_report_variant(report) == 'minimal'

    if payments:
        pay_header = f"{'Method':<24}   {'Amount':>12}"
        lines.append(pay_header)
        lines.append('')
        table_header_lines.add(pay_header)

        for row in payments:
            lines.append(f"{str(row.get('method') or '').upper():<24} : {_fmt_money(row.get('amount')):>12}")
        payment_total = sum(_to_float(row.get('amount')) for row in payments)
    else:
        lines.append('No payment rows.')
        payment_total = 0.0

    lines.append('')
    payment_total_line = f"{'Payment Total':<24} : {_fmt_money(payment_total):>12}"
    lines.append(payment_total_line)
    blue_lines.add(payment_total_line)

    cash_received = sum(_to_float(row.get('amount')) for row in payments if str(row.get('method') or '').upper() == 'CASH')
    refund_outflow = _to_float(sales.get('less_refund_outflow'))
    vendor_outflow = _to_float(sales.get('less_vendor_outflow'))
    cash_outflow = refund_outflow + vendor_outflow
    cash_after_outflow = cash_received - cash_outflow

    lines.extend(['', '3. Cash Drawer Expected', '-' * 72])
    cash_line = f"{'CASH':<24} : {_fmt_money(cash_received):>12}"
    cash_outflow_line = f"{'Refund + Vendor Outflow':<24} : {_fmt_money(cash_outflow):>12}"
    cash_after_line = f"{'Cash After Outflow':<24} : {_fmt_money(cash_after_outflow):>12}"
    lines.append(cash_line)
    lines.append(cash_outflow_line)
    lines.append('')
    lines.append(cash_after_line)
    #blue_lines.update({cash_line, cash_outflow_line, cash_after_line})
    blue_lines.add(cash_after_line)

    qty_unit_w = 14
    money_w = 14
    if not is_minimal:
        lines.extend(['', '4. Earnings Broken Down by Category', '-' * 72])
        name_w = 30
        # Keep header/body columns on identical geometry (including index prefix).
        prod_header = f"{'No.':<4}{'Product Name':<{name_w}} {'Qty Sold':>{qty_unit_w}} {'Amount':>{money_w}}"
        if categories:
            for cat in categories:
                cat_name = str(cat.get('category_name') or 'Uncategorized')
                cat_total = _to_float(cat.get('category_total'))
                lines.append(cat_name)
                bold_lines.add(cat_name)
                lines.append('')
                lines.append(prod_header)
                table_header_lines.add(prod_header)
                for idx, prod in enumerate((cat.get('products') or []), start=1):
                    qty_txt, unit_txt = _format_qty_unit(prod.get('qty_sold'), prod.get('unit'))
                    product_name = _truncate(str(prod.get('product_name') or ''), name_w)
                    qty_unit_txt = f"{qty_txt} {unit_txt}".strip()
                    lines.append(
                        f"{str(idx) + '.':>3} {product_name:<{name_w}} "
                        f"{qty_unit_txt:>{qty_unit_w}} {_fmt_money(prod.get('line_sales')):>{money_w}}"
                    )
                lines.append('')
                total_label_w = 4 + name_w + 1 + qty_unit_w
                total_line = f"{'Total':<{total_label_w}} {_fmt_money(cat_total):>{money_w}}"
                lines.append(total_line)
                blue_lines.add(total_line)
                lines.append('.' * 72)
                lines.append('')
        else:
            lines.append('No category/product rows.')

        lines.extend(['', '5. Top 10 Best Sellers (By Earnings)', '-' * 72])
        if top_products:
            top_name_w = 30
            top_header = f"{'Rank':>4} {'Product Name':<{top_name_w}} {'Qty Sold':>{qty_unit_w}} {'Amount':>{money_w}}"
            lines.append(top_header)
            table_header_lines.add(top_header)

            for row in top_products:
                qty_txt, unit_txt = _format_qty_unit(row.get('qty_sold'), row.get('unit'))
                pname = _truncate(str(row.get('product_name') or ''), top_name_w)
                qty_unit_txt = f"{qty_txt} {unit_txt}".strip()
                lines.append(
                    f"{_to_int(row.get('rank')):>3}. {pname:<{top_name_w}} "
                    f"{qty_unit_txt:>{qty_unit_w}} {_fmt_money(row.get('line_sales')):>{money_w}}"
                )
        else:
            lines.append('No product rows.')

    outflow_section_no = 4 if is_minimal else 6
    lines.extend(['', f'{outflow_section_no}. Cash Outflows Detail', '-' * 72])
    if outflows:
        out_header = f"{'Type':<12} {'Date/Time':<20} {'Cashier':<10} {'Amount':>12}  Note"
        lines.append(out_header)
        table_header_lines.add(out_header)

        for row in outflows:
            outflow_type = row.get('outflow_type')
            if outflow_type == 'VENDOR_OUT':
                out_flow = 'VENDOR'
            elif outflow_type == 'REFUND_OUT':
                out_flow = 'REFUND'
            else:
                out_flow = 'OTHER' # Safe fallback
            lines.append(
                f"{f"{out_flow:<12}"} "
                f"{format_report_timestamp(row.get('created_at')):20} "
                f"{str(row.get('cashier') or ''):10} "
                f"{_fmt_money(row.get('amount')):>12}  "
                f"{str(row.get('note') or '')}"
            )
    else:
        lines.append('No outflow rows.')

    lines.extend(
        [
            '',
            f'{5 if is_minimal else 7}. Other Activity (Unpaid & Cancelled)',
            '-' * 72,
            f"{'UNPAID Receipts Count':<28} : {_to_int(excluded.get('unpaid_receipts_count')):>8}",
            f"{'UNPAID Receipts Total':<28} : {_fmt_money(excluded.get('unpaid_receipts_total')):>12}",
            '',
            f"{'CANCELLED Receipts Count':<28} : {_to_int(excluded.get('cancelled_receipts_count')):>8}",
            f"{'CANCELLED Receipts Total':<28} : {_fmt_money(excluded.get('cancelled_receipts_total')):>12}",
            '',
            'END OF REPORT',
        ]
    )
    return '\n'.join(lines), bold_lines, table_header_lines, blue_lines


class _ReportTextHighlighter(QSyntaxHighlighter):
    """Apply lightweight styling to key lines in QPlainTextEdit."""

    def __init__(self, document, *, bold_lines: set[str], table_header_lines: set[str], blue_lines: set[str]):
        super().__init__(document)
        self._bold_lines = bold_lines
        self._table_header_lines = table_header_lines
        self._blue_lines = blue_lines

        self._body_fmt = QTextCharFormat()
        self._body_fmt.setFontFamily('Courier New')
        self._body_fmt.setFontFixedPitch(True)
        self._body_fmt.setFontWeight(50)
        self._body_fmt.setFontPointSize(12)
        self._body_fmt.setForeground(QColor('#000000'))

        self._title_fmt = QTextCharFormat()
        self._title_fmt.setFontFamily('Courier New')
        self._title_fmt.setFontFixedPitch(True)
        self._title_fmt.setFontWeight(75)
        self._title_fmt.setFontPointSize(16)

        self._section_fmt = QTextCharFormat()
        self._section_fmt.setFontFamily('Courier New')
        self._section_fmt.setFontFixedPitch(True)
        self._section_fmt.setFontWeight(75)
        self._section_fmt.setFontPointSize(14)

        self._bold_fmt = QTextCharFormat()
        self._bold_fmt.setFontFamily('Courier New')
        self._bold_fmt.setFontFixedPitch(True)
        self._bold_fmt.setFontWeight(75)
        self._bold_fmt.setFontPointSize(12)

        self._table_header_fmt = QTextCharFormat()
        self._table_header_fmt.setFontFamily('Courier New')
        self._table_header_fmt.setFontFixedPitch(True)
        self._table_header_fmt.setFontWeight(50)
        self._table_header_fmt.setFontPointSize(12)
        self._table_header_fmt.setForeground(QColor('#7A4A21'))

        self._blue_fmt = QTextCharFormat()
        self._blue_fmt.setFontFamily('Courier New')
        self._blue_fmt.setFontFixedPitch(True)
        self._blue_fmt.setFontWeight(75)
        self._blue_fmt.setFontPointSize(12)
        self._blue_fmt.setForeground(QColor('#1E70FF'))

    def highlightBlock(self, text: str) -> None:
        # Base formatting for alignment.
        self.setFormat(0, len(text), self._body_fmt)

        if text in ('Sales Record & Totals', 'Sales Trends & Patterns', 'INACTIVE PRODUCTS REPORT'):
            self.setFormat(0, len(text), self._title_fmt)
            return

        # Only treat single-digit numbered lines as section headers
        # (prevents multi-digit product ranks like "10." from matching).
        if re.match(r'^[1-9]\.\s', text):
            self.setFormat(0, len(text), self._section_fmt)
            return

        if text in self._table_header_lines:
            self.setFormat(0, len(text), self._table_header_fmt)
            return

        if text in self._blue_lines:
            self.setFormat(0, len(text), self._blue_fmt)
            return

        if text in self._bold_lines:
            self.setFormat(0, len(text), self._bold_fmt)


def _render_placeholder(layout: QVBoxLayout, *, report_type: str) -> None:
    """Render placeholder content for non-detailed report types."""
    rpt = str(report_type or 'summary').strip().lower()
    msg = QLabel(f'No {rpt} content available.')
    msg.setObjectName('reportViewerMessageLabel')
    msg.setAlignment(Qt.AlignCenter)
    msg.setWordWrap(True)
    layout.addWidget(msg)


def _render_text_report(
    layout: QVBoxLayout,
    *,
    report_text: str,
    bold_lines: set[str],
    table_header_lines: set[str],
    blue_lines: set[str],
) -> None:
    """Render searchable monospaced text report content."""
    search_row = QHBoxLayout()
    search_row.setSpacing(8)

    search_label = QLabel('Find:')
    search_label.setObjectName('reportViewerSearchLabel')
    search_row.addWidget(search_label)

    search_input = QLineEdit()
    search_input.setObjectName('reportViewerSearchInput')
    search_input.setPlaceholderText('Search text in report...')
    search_row.addWidget(search_input)

    search_row.addStretch()
    layout.addLayout(search_row)

    text_box = QPlainTextEdit()
    text_box.setObjectName('reportViewerTextEdit')
    text_box.setReadOnly(True)
    text_box.setLineWrapMode(QPlainTextEdit.NoWrap)
    text_box.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    text_box.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    text_box.setPlainText(report_text)
    text_box._report_highlighter = _ReportTextHighlighter(  # keep reference alive
        text_box.document(), bold_lines=bold_lines, table_header_lines=table_header_lines, blue_lines=blue_lines
    )
    layout.addWidget(text_box)

    def _highlight_matches(term: str) -> None:
        """Highlight search matches."""
        if not term:
            text_box.setExtraSelections([])
            return

        doc = text_box.document()
        cursor = doc.find(term, 0)
        selections = []

        while not cursor.isNull():
            sel = QTextEdit.ExtraSelection()
            fmt = QTextCharFormat()
            fmt.setBackground(QColor('#FFF59D'))
            sel.format = fmt
            sel.cursor = cursor
            selections.append(sel)
            cursor = doc.find(term, cursor)

        text_box.setExtraSelections(selections)

    def _find_text() -> None:
        term = search_input.text()
        if not term:
            text_box.setExtraSelections([])
            return
        _highlight_matches(term)
        if not text_box.find(term):
            cursor = text_box.textCursor()
            cursor.movePosition(cursor.Start)
            text_box.setTextCursor(cursor)
            text_box.find(term)

    search_input.textChanged.connect(_highlight_matches)
    search_input.returnPressed.connect(_find_text)


def _render_detailed(layout: QVBoxLayout, *, report_data: dict) -> None:
    """Render detailed report text with search."""
    report_text, bold_lines, table_header_lines, blue_lines = _format_detailed_report_text(report_data)
    _render_text_report(
        layout,
        report_text=report_text,
        bold_lines=bold_lines,
        table_header_lines=table_header_lines,
        blue_lines=blue_lines,
    )


def _format_summary_report_text(report: dict) -> tuple[str, set[str], set[str], set[str]]:
    """Render summary report text and style metadata."""
    if not isinstance(report, dict):
        report = {}

    def _to_int(value) -> int:
        try:
            return int(value or 0)
        except Exception:
            return 0

    def _fmt_money(value) -> str:
        return f"$ {_to_float(value):,.2f}"

    def _fmt_number(value) -> str:
        return f"{_to_float(value):,.2f}"

    def _truncate(text: str, width: int) -> str:
        s = str(text or '')
        if len(s) <= width:
            return s
        if width <= 3:
            return s[:width]
        return s[: width - 3] + '...'

    header = report.get('header') or {}
    sales = report.get('sales_summary') or {}
    sales_by_hour = report.get('sales_by_hour') or []
    peak_hour = report.get('peak_hour') or {}
    top_qty_by_hour = report.get('top_products_by_qty_hour') or []
    top_sales_by_hour = report.get('top_products_by_sales_hour') or []
    top_qty_day = report.get('top_products_by_qty_day') or []
    top_sales_day = report.get('top_products_by_sales_day') or []
    excluded = report.get('excluded') or {}

    bold_lines: set[str] = set()
    table_header_lines: set[str] = set()
    blue_lines: set[str] = set()

    gross_line = f"{'Avg Gross Sales':<24} : {_fmt_money(sales.get('gross_sales')):>12}"
    refund_line = f"{'Avg Refund Outflow':<24} : {_fmt_money(sales.get('less_refund_outflow')):>12}"
    vendor_line = f"{'Avg Vendor Outflow':<24} : {_fmt_money(sales.get('less_vendor_outflow')):>12}"
    net_line = f"{'Avg Net After Outflows':<24} : {_fmt_money(sales.get('net_after_outflows')):>12}"

    lines = [
        'Sales Trends & Patterns',
        '=' * 72,
        f"Period From   : {format_report_timestamp(header.get('period_from'))}",
        f"Period To     : {format_report_timestamp(header.get('period_to'))}",
        '',
        f"Generated At  : {format_report_timestamp(header.get('generated_at'))}",
        f"Generated By  : {header.get('generated_by') or '-'}",
        '',
        '1. Average Sales Summary',
        '-' * 70,
        f"{'Avg Paid Receipt Count':<24} : {_fmt_number(sales.get('paid_receipt_count')):>12}",
        gross_line,
        '',
        refund_line,
        vendor_line,
        '',
        net_line,
    ]
    blue_lines.update({gross_line, net_line})

    lines.extend(['', '2. Average Hourly Earnings', '-' * 70])
    if sales_by_hour:
        hour_header = f"{'Hour Slot':<24} {'Avg Revenue':>12}"
        lines.append(hour_header)
        table_header_lines.add(hour_header)

        for row in sales_by_hour:
            hour_slot = _to_ampm_hour_label(row.get('hour_slot'))
            amount = _fmt_money(row.get('sales_amount'))
            lines.append(f"{hour_slot:<24} {amount:>12}")
    else:
        lines.append('No sales by hour rows.')

    peak_hour_label = _to_ampm_hour_label(peak_hour.get('hour_slot')) or '-'
    peak_hour_amount = _fmt_money(peak_hour.get('sales_amount')) if peak_hour else _fmt_money(0.0)
    peak_line = f"{'Peak Avg Hour':<24} {peak_hour_label:<14} ({peak_hour_amount})"
    lines.append('')
    lines.append(peak_line)
    blue_lines.add(peak_line)

    name_w = 28
    qty_unit_w = 16
    sales_w = 12
    # Add extra horizontal gap between Avg Qty and Avg Revenue by inserting two spaces
    top_header = f"{'Rank':>4} {'Product Name':<{name_w}} {'Avg Qty':>{qty_unit_w}}  {'Avg Revenue':>{sales_w}}"

    def _split_by_unit_type(products: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Split products into pieces (each/ea) and weight (kg/g) groups."""
        pieces = []
        weight = []
        for p in products:
            unit_lower = str(p.get('unit', '')).lower()
            if unit_lower in ('each', 'ea'):
                pieces.append(p)
            elif 'kg' in unit_lower or 'g' in unit_lower:
                weight.append(p)
        return pieces, weight

    def _sort_products_for_display(products: List[Dict[str, Any]], primary_metric: str = 'qty') -> List[Dict[str, Any]]:
        """Sort products by primary metric desc, secondary by line_sales desc for tie-break."""
        if primary_metric == 'qty':
            return sorted(products, key=lambda p: (_to_float(p.get('qty_sold', 0)), _to_float(p.get('line_sales', 0))), reverse=True)
        else:  # primary_metric == 'sales' or 'earnings'
            return sorted(products, key=lambda p: (_to_float(p.get('line_sales', 0)), _to_float(p.get('qty_sold', 0))), reverse=True)

    def _render_product_list(products: List[Dict[str, Any]], limit: int | None = None) -> None:
        """Render a list of products with optional limit."""
        if limit:
            products = products[:limit]
        
        if not products:
            return
        
        lines.append(top_header)
        table_header_lines.add(top_header)
        
        for idx, row in enumerate(products, start=1):
            qty_txt, unit_txt = _format_qty_unit(row.get('qty_sold'), row.get('unit'))
            qty_unit_txt = f"{qty_txt} {unit_txt}".strip()
            pname = _truncate(str(row.get('product_name') or ''), name_w)
            lines.append(
                f"{idx:>3}. {pname:<{name_w}} "
                # two spaces inserted before revenue column to increase gap
                f"{qty_unit_txt:>{qty_unit_w}}  {_fmt_money(row.get('line_sales')):>{sales_w}}"
            )

    def _append_group_section_split(title: str, groups: List[Dict[str, Any]], section_no: int, primary_metric: str = 'qty', per_unit_limit: int = 3) -> None:
        """Render hourly groups split by unit type (pieces and weight)."""
        lines.extend(['', f'{section_no}. {title}', '-' * 70])
        for group in groups:
            hour_slot = _to_ampm_hour_label(group.get('hour_slot'))
            products = group.get('products') or []
            lines.append(hour_slot)
            bold_lines.add(hour_slot)
            
            if products:
                pieces, weight = _split_by_unit_type(products)
                pieces = _sort_products_for_display(pieces, primary_metric)
                weight = _sort_products_for_display(weight, primary_metric)
                
                # Render pieces sub-list
                if pieces:
                    _render_product_list(pieces, limit=per_unit_limit)
                
                # Render weight sub-list with separator
                if weight:
                    lines.append('')  # Blank row separator
                    _render_product_list(weight, limit=per_unit_limit)
                
                if not pieces and not weight:
                    lines.append('No product rows.')
            else:
                lines.append('No product rows.')
            lines.append('')

    def _append_day_section_split(title: str, rows: List[Dict[str, Any]], section_no: int, primary_metric: str = 'qty', pieces_limit: int = 10, weight_limit: int = 5) -> None:
        """Render daily sellers split by unit type (pieces and weight)."""
        lines.extend(['', f'{section_no}. {title}', '-' * 70])
        
        if rows:
            pieces, weight = _split_by_unit_type(rows)
            pieces = _sort_products_for_display(pieces, primary_metric)
            weight = _sort_products_for_display(weight, primary_metric)
            
            # Render pieces sub-list
            if pieces:
                _render_product_list(pieces, limit=pieces_limit)
            
            # Render weight sub-list with separator
            if weight:
                lines.append('')  # Blank row separator
                _render_product_list(weight, limit=weight_limit)
            
            if not pieces and not weight:
                lines.append('No product rows.')
        else:
            lines.append('No product rows.')

    # Sections 3 & 4: swap positions of hourly sections
    _append_group_section_split('Top Earning Items (By Hour)', top_sales_by_hour, 3, primary_metric='sales')
    _append_group_section_split('Most Popular Items (By Hour)', top_qty_by_hour, 4, primary_metric='qty')

    # Sections 5 & 6: swap positions of daily consistent sellers
    _append_day_section_split('Most Consistent Sellers (By Earnings)', top_sales_day, 5, primary_metric='sales')
    _append_day_section_split('Most Consistent Sellers (By Quantity)', top_qty_day, 6, primary_metric='qty')

    lines.extend(['', 'END OF REPORT'])

    return '\n'.join(lines), bold_lines, table_header_lines, blue_lines


def _render_summary(layout: QVBoxLayout, *, report_data: dict) -> None:
    """Render summary report text with search."""
    report_text, bold_lines, table_header_lines, blue_lines = _format_summary_report_text(report_data)
    _render_text_report(
        layout,
        report_text=report_text,
        bold_lines=bold_lines,
        table_header_lines=table_header_lines,
        blue_lines=blue_lines,
    )


def _format_inactivity_report_text(report: dict) -> tuple[str, set[str], set[str], set[str]]:
    """Render inactivity report text and style metadata."""
    if not isinstance(report, dict):
        report = {}

    header = report.get('header') or {}
    sections = report.get('sections') or []
    summary = report.get('summary') or {}

    def _fmt_date(value) -> str:
        return format_date(value, fmt='%d/%m/%Y') or 'Never Sold'

    def _fit(text: Any, width: int) -> str:
        s = str(text or '-')
        if len(s) <= width:
            return s
        if width <= 3:
            return s[:width]
        return s[: width - 3] + '...'

    bold_lines: set[str] = set()
    table_header_lines: set[str] = set()
    blue_lines: set[str] = set()

    period_checked = format_date(header.get('period_checked'), fmt='%d/%m/%Y') or '-'
    generated_at = format_report_timestamp(header.get('generated_at'))
    generated_by = header.get('generated_by') or '-'

    lines = [
        'INACTIVE PRODUCTS REPORT',
        '=' * 70,
        f"Period Checked : up to {period_checked}",
        f"Generated At    : {generated_at}",
        f"Generated By    : {generated_by}",
        '',
    ]

    code_w = 14
    name_w = 30
    category_w = 20
    date_w = 10

    def _col(text: Any, width: int) -> str:
        return _fit(text, width)

    def _row(parts: List[tuple[Any, int]]) -> str:
        return '  '.join(f"{_col(value, width):<{width}}" for value, width in parts)

    def _category_cell(value: Any) -> str:
        text = str(value or '').strip()
        if not text:
            return '-'.ljust(category_w)
        return _fit(text, category_w)

    header_line = _row(
        [
            ('Product Code', code_w),
            ('Product Name', name_w),
            ('Category', category_w),
            ('Last Sold', date_w),
        ]
    )

    bucket_sections = {str(section.get('bucket') or ''): section for section in sections}

    lines.extend(
        [
            '1. SUMMARY',
            '-' * 70,
            '',
        ]
    )

    bucket_counts = summary.get('bucket_counts') or {}
    summary_rows = [
        ('3–6 Months No Sale', bucket_counts.get('3_6', 0)),
        ('6–12 Months No Sale', bucket_counts.get('6_12', 0)),
        ('More Than 1 Year No Sale', bucket_counts.get('1_plus', 0)),
        ('Never Sold', bucket_counts.get('never', 0)),
    ]
    summary_label_w = 42
    for label, count in summary_rows:
        line = f"{label:<{summary_label_w}} : {int(count or 0)} products"
        lines.append(line)
        blue_lines.add(line)

    total_line = f"{'Total Inactive Products':<{summary_label_w}} : {int(summary.get('total_inactive_products') or 0)} products"
    lines.extend(['', total_line, ''])
    blue_lines.add(total_line)

    for idx, bucket_key in enumerate(('3_6', '6_12', '1_plus', 'never'), start=2):
        section = bucket_sections.get(bucket_key) or {'title': '', 'products': []}
        title = str(section.get('title') or '').strip() or f'SECTION {idx}'
        rows = section.get('products') or []
        lines.extend(['', f'{idx}. {title}', '-' * 70, ''])
        if rows:
            lines.append(header_line)
            table_header_lines.add(header_line)
            for row in rows:
                lines.append(
                    _row(
                        [
                            (row.get('product_code'), code_w),
                            (row.get('product_name'), name_w),
                            (_category_cell(row.get('category')), category_w),
                            (_fmt_date(row.get('last_sold')), date_w),
                        ]
                    )
                )
        else:
            lines.append('No inactive products in this bucket.')

    lines.extend(['', '-' * 70, 'END OF REPORT'])
    blue_lines.add(total_line)

    return '\n'.join(lines), bold_lines, table_header_lines, blue_lines


def _render_inactivity(layout: QVBoxLayout, *, report_data: dict) -> None:
    """Render inactivity report text with search."""
    report_text, bold_lines, table_header_lines, blue_lines = _format_inactivity_report_text(report_data)
    _render_text_report(
        layout,
        report_text=report_text,
        bold_lines=bold_lines,
        table_header_lines=table_header_lines,
        blue_lines=blue_lines,
    )


def open_report_viewer(parent_dlg: QDialog, *, report_type: str, report_data: dict = None) -> None:
    """Open the report viewer."""
    overlay = _create_overlay(parent_dlg)
    try:
        rpt = str(report_type or 'summary').strip().lower()
        if rpt == 'chart':
            from modules.menu import report_charts

            report_charts.open_chart_report_viewer(parent_dlg, report_data=report_data or {})
            return
        viewer, layout = _build_shell(parent_dlg, report_type=rpt)

        if rpt == 'detail':
            _render_detailed(layout, report_data=report_data or {})
        elif rpt == 'summary':
            _render_summary(layout, report_data=report_data or {})
        elif rpt == 'inactivity':
            _render_inactivity(layout, report_data=report_data or {})
        else:
            _render_placeholder(layout, report_type=rpt)

        viewer.exec_()
    finally:
        _cleanup_overlay(overlay)
