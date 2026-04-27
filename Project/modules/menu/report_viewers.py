"""UI-only report viewer helpers.

This module owns report viewer dialogs and rendering. It intentionally keeps
all data fetching outside (for example in report_generator / reports_repo).
"""

import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget
from modules.date_time.formatters import format_report_timestamp
import config

# Viewer size policy moved to `config.py` as `REPORT_VIEWER_RATIOS`.
# Keep a pixel fallback in case ratios are not available at runtime.
DEFAULT_REPORT_VIEWER_SIZE = (760, 520)


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
    # Resolve size from config.REPORT_VIEWER_RATIOS using the main/top-level
    # window frame geometry (matches DialogWrapper behavior). Fall back to
    # primary screen when main window cannot be determined.
    size_w, size_h = DEFAULT_REPORT_VIEWER_SIZE
    mw = mh = mx = my = 0
    try:
        # Find top-level ancestor (should be the main window when parent_dlg
        # was created via DialogWrapper or setParent(main_window)).
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
            # Fallback to primary screen available geometry
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            geom = screen.availableGeometry()
            mw = geom.width()
            mh = geom.height()
            mx = geom.x()
            my = geom.y()

        ratio = getattr(config, 'REPORT_VIEWER_RATIOS', {}).get(rpt)
        if ratio:
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
    # Enforce minimum size from .ui and center on main window
    try:
        min_w = viewer.minimumWidth()
        min_h = viewer.minimumHeight()
        final_w = max(min_w, int(size_w))
        final_h = max(min_h, int(size_h))
        viewer.resize(final_w, final_h)

        # Center the viewer over the reference window/screen
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
    """Render fixed-width text and style metadata for detailed report data."""
    if not isinstance(report, dict):
        report = {}

    def _to_float(value) -> float:
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    def _to_int(value) -> int:
        try:
            return int(value or 0)
        except Exception:
            return 0

    def _fmt_money(value) -> str:
        return f"$ {_to_float(value):,.2f}"

    def _truncate(text: str, width: int) -> str:
        s = str(text or '')
        if len(s) <= width:
            return s
        if width <= 3:
            return s[:width]
        return s[: width - 3] + '...'

    def _fmt_qty_unit(qty, unit) -> tuple[str, str]:
        raw_unit = str(unit or '').strip()
        unit_lower = raw_unit.lower()
        if unit_lower in ('each', 'ea'):
            return str(int(round(_to_float(qty)))), 'Ea'

        unit_txt = raw_unit or '-'
        if 'kg' in unit_lower:
            # Only convert to grams if the weight is less than 1.0 kg
            if qty < 1.0:
                gram_qty = qty * 1000
                qty_txt = f"{gram_qty:.0f}"  # Whole number for grams
                unit_txt = 'g'
            else:
                # Keep as kg for 1.0 and above, use 2 decimals (e.g., 1.50 kg)
                qty_txt = f"{qty:.2f}"
                unit_txt = 'kg' 
        else:
            # Default behavior for non-weight units (Each, Pcs, etc.)
            qty_txt = f"{qty:.3f}"
        return qty_txt, unit_txt

    sales = report.get('sales_summary') or {}
    payments = report.get('payment_breakdown') or []
    categories = report.get('categories') or []
    top_products = report.get('top_products') or []
    outflows = report.get('cash_outflows') or []
    excluded = report.get('excluded') or {}
    header = report.get('header') or {}

    bold_lines: set[str] = set()
    table_header_lines: set[str] = set()
    brown_lines: set[str] = set()
    
    gross_line = f"{'Gross Sales':<24} : {_fmt_money(sales.get('gross_sales')):>12}"
    net_line = f"{'Net After Outflow':<24} : {_fmt_money(sales.get('net_after_outflows')):>12}"

    lines = [
        'DETAILED SALES REPORT',
        '=' * 72,
        f"Period        : {format_report_timestamp(header.get('period_from'))} to {format_report_timestamp(header.get('period_to'))}",
        f"Generated At  : {format_report_timestamp(header.get('generated_at'))}",
        f"Generated By  : {header.get('generated_by') or '-'}",
        '',
        '1. Sales Summary',
        '-' * 72,
        f"{'PAID Receipt Count':<24} : {_to_int(sales.get('paid_receipt_count')):>8}",
        '',
        gross_line,
        f"{'Refund Outflow':<24} : {_fmt_money(sales.get('less_refund_outflow')):>12}",
        f"{'Vendor Outflow':<24} : {_fmt_money(sales.get('less_vendor_outflow')):>12}",
        '',
        net_line,
        '',
        '2. Payment Method Breakdown',
        '-' * 72,
    ]

    brown_lines.add(gross_line)
    brown_lines.add(net_line)

    pay_header = f"{'Method':<20} {'Amount':>12}"
    lines.append(pay_header)
    table_header_lines.add(pay_header)

    if payments:
        for row in payments:
            lines.append(f"{str(row.get('method') or '').upper():<20} {_fmt_money(row.get('amount')):>12}")
        payment_total = sum(_to_float(row.get('amount')) for row in payments)
    else:
        lines.append('No payment rows.')
        payment_total = 0.0

    lines.append('')
    payment_total_line = f"{'PAYMENT TOTAL':<20} {_fmt_money(payment_total):>12}"
    lines.append(payment_total_line)
    brown_lines.add(payment_total_line)

    lines.extend(['', '3. Category Breakdown with Products', '-' * 72])
    name_w = 30
    qty_w = 8
    unit_w = 6
    money_w = 12
    # Keep header/body columns on identical geometry (including index prefix).
    prod_header = f"{'No.':<4}{'Product Name':<{name_w}} {'Qty Sold':>{qty_w}} {'':<{unit_w}} {'Amount':>{money_w}}"
    if categories:
        for cat_idx, cat in enumerate(categories):
            cat_name = str(cat.get('category_name') or 'Uncategorized')
            cat_total = _to_float(cat.get('category_total'))
            lines.append(cat_name)
            bold_lines.add(cat_name)
            lines.append('')
            lines.append(prod_header)
            table_header_lines.add(prod_header)
            for idx, prod in enumerate((cat.get('products') or []), start=1):
                qty_txt, unit_txt = _fmt_qty_unit(prod.get('qty_sold'), prod.get('unit'))
                product_name = _truncate(str(prod.get('product_name') or ''), name_w)
                lines.append(
                    f"{str(idx) + '.':>3} {product_name:<{name_w}} "
                    f"{qty_txt:>{qty_w}} {unit_txt:<{unit_w}} {_fmt_money(prod.get('line_sales')):>{money_w}}"
                )
            lines.append('')
            total_label_w = 4 + name_w + 1 + qty_w + 1 + unit_w
            total_line = f"{'Total':<{total_label_w}} {_fmt_money(cat_total):>{money_w}}"
            lines.append(total_line)
            brown_lines.add(total_line)
            #if cat_idx < len(categories) - 1:
            lines.append('.' * 72)
            lines.append('')
    else:
        lines.append('No category/product rows.')

    lines.extend(['', '4. Top 10 Products', '-' * 72])
    top_name_w = 30
    top_header = f"{'Rank':>4} {'Product Name':<{top_name_w}} {'Qty Sold':>{qty_w}} {'':<{unit_w}} {'Amount':>{money_w}}"
    lines.append(top_header)
    table_header_lines.add(top_header)
    if top_products:
        for row in top_products:
            qty_txt, unit_txt = _fmt_qty_unit(row.get('qty_sold'), row.get('unit'))
            pname = _truncate(str(row.get('product_name') or ''), top_name_w)
            lines.append(
                f"{_to_int(row.get('rank')):>3}. {pname:<{top_name_w}} "
                f"{qty_txt:>{qty_w}} {unit_txt:<{unit_w}} {_fmt_money(row.get('line_sales')):>{money_w}}"
            )
    else:
        lines.append('No product rows.')

    lines.extend(['', '5. Cash Outflows Detail', '-' * 72])
    out_header = f"{'Type':<12} {'Date/Time':<20} {'Cashier':<10} {'Amount':>12}  Note"
    lines.append(out_header)
    table_header_lines.add(out_header)
    if outflows:
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
            '6. Excluded / Operational Section',
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
    return '\n'.join(lines), bold_lines, table_header_lines, brown_lines


class _ReportTextHighlighter(QSyntaxHighlighter):
    """Apply lightweight styling to key lines in QPlainTextEdit."""

    def __init__(self, document, *, bold_lines: set[str], table_header_lines: set[str], brown_lines: set[str]):
        super().__init__(document)
        self._bold_lines = bold_lines
        self._table_header_lines = table_header_lines
        self._brown_lines = brown_lines

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
        self._table_header_fmt.setForeground(QColor('#1E70FF'))

        self._brown_fmt = QTextCharFormat()
        self._brown_fmt.setFontFamily('Courier New')
        self._brown_fmt.setFontFixedPitch(True)
        self._brown_fmt.setFontWeight(50)
        self._brown_fmt.setFontPointSize(12)
        self._brown_fmt.setForeground(QColor('#7A4A21'))

    def highlightBlock(self, text: str) -> None:
        # Apply one common monospaced baseline to all lines for strict column alignment.
        self.setFormat(0, len(text), self._body_fmt)

        if text == 'DETAILED SALES REPORT':
            self.setFormat(0, len(text), self._title_fmt)
            return

        if re.match(r'^\d+\.\s', text):
            self.setFormat(0, len(text), self._section_fmt)
            return

        if text in self._table_header_lines:
            self.setFormat(0, len(text), self._table_header_fmt)
            return

        if text in self._brown_lines:
            self.setFormat(0, len(text), self._brown_fmt)
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


def _render_detailed(layout: QVBoxLayout, *, report_data: dict) -> None:
    """Render detailed text report with search and scrollbars."""
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
    report_text, bold_lines, table_header_lines, brown_lines = _format_detailed_report_text(report_data)
    text_box.setPlainText(report_text)
    text_box._report_highlighter = _ReportTextHighlighter(  # keep reference alive
        text_box.document(), bold_lines=bold_lines, table_header_lines=table_header_lines, brown_lines=brown_lines
    )
    layout.addWidget(text_box)

    def _highlight_matches(term: str) -> None:
        """Highlight all search matches with yellow background."""
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


def open_report_viewer(parent_dlg: QDialog, *, report_type: str, report_data: dict = None) -> None:
    """Open report viewer with a shared shell and type-specific renderer."""
    overlay = _create_overlay(parent_dlg)
    try:
        rpt = str(report_type or 'summary').strip().lower()
        viewer, layout = _build_shell(parent_dlg, report_type=rpt)

        if rpt == 'detail':
            _render_detailed(layout, report_data=report_data or {})
        else:
            _render_placeholder(layout, report_type=rpt)

        viewer.exec_()
    finally:
        _cleanup_overlay(overlay)
