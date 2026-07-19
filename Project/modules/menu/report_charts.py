"""Chart report rendering and PDF export helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from PyQt5.QtCore import QPointF, QRectF, Qt, QSize
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QBrush, QPolygonF
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QApplication, QDialog, QFrame, QGridLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from modules.date_time.formatters import format_report_timestamp
from modules.menu.report_viewers import _display_payment_method, _to_ampm_hour_label
from modules.ui_utils.money_format import format_currency, money_value


DEFAULT_CHART_VIEWER_SIZE = (1080, 920)
_APP_INSTANCE = None


def _ensure_application() -> QApplication:
    global _APP_INSTANCE
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    _APP_INSTANCE = app
    return app


def _to_float(value: Any) -> float:
    return money_value(value)


def _fmt_money(value: Any) -> str:
    return format_currency(value)


def _hour_label(hour: int) -> str:
    hour = int(hour) % 24
    suffix = 'am' if hour < 12 else 'pm'
    display = hour % 12
    if display == 0:
        display = 12
    return f'{display}\n{suffix}'


def _truncate(text: Any, width: int) -> str:
    value = str(text or '')
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[:width - 3] + '...'


def _safe_report(report_data: Any) -> dict:
    return report_data if isinstance(report_data, dict) else {}


def _prepare_widget_for_pdf(widget: QWidget) -> QSize:
    widget.ensurePolished()

    layout = widget.layout()
    if layout is not None:
        layout.activate()

    content_size = widget.sizeHint()
    if layout is not None:
        layout_size = layout.sizeHint()
        content_size = QSize(
            max(content_size.width(), layout_size.width()),
            max(content_size.height(), layout_size.height()),
        )

    content_size = QSize(
        max(content_size.width(), widget.minimumSizeHint().width(), widget.minimumWidth()),
        max(content_size.height(), widget.minimumSizeHint().height(), widget.minimumHeight()),
    )
    widget.resize(content_size)
    if layout is not None:
        layout.activate()
    return content_size


class _ChartCard(QFrame):
    def __init__(self, title: str, subtitle: str, chart_widget: QWidget, *, min_height: int = 280):
        super().__init__()
        self.setObjectName('chartCard')
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(min_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setStyleSheet(
            'QFrame#chartCard { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 12px; }'
            'QLabel#chartCardTitle { color: #1F2937; font-weight: 600; font-size: 18px; }'
            'QLabel#chartCardSubtitle { color: #6B7280; font-size: 18px; }'
            'QLabel#chartMetricLabel { color: #374151; font-weight: 500; font-size: 16px; }'
            'QLabel#chartMetricValue { color: #111827; font-weight: 500; font-size: 16px; }'
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        title_lbl = QLabel(title)
        title_lbl.setObjectName('chartCardTitle')
        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setObjectName('chartCardSubtitle')
        subtitle_lbl.setWordWrap(True)

        layout.addWidget(title_lbl)
        layout.addWidget(subtitle_lbl)
        layout.addSpacing(25)
        layout.addWidget(chart_widget, 1)


class _BaseChartWidget(QWidget):
    def __init__(self, *, min_height: int = 220):
        super().__init__()
        self.setMinimumHeight(min_height)
        self.setMinimumWidth(620)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _plot_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(95, 18, -40, -48)


class _HourlySalesChart(_BaseChartWidget):
    def __init__(self, series: Sequence[Dict[str, Any]]):
        super().__init__(min_height=260)
        self._series = list(series)

    def sizeHint(self) -> QSize:
        return QSize(900, 260)

    def _visible_series(self) -> List[Dict[str, Any]]:
        visible = [row for row in self._series if _to_float(row.get('sales_amount')) > 0]
        if not visible:
            return []
        start_index = next((idx for idx, row in enumerate(self._series) if _to_float(row.get('sales_amount')) > 0), 0)
        end_index = len(self._series) - 1 - next((idx for idx, row in enumerate(reversed(self._series)) if _to_float(row.get('sales_amount')) > 0), 0)
        return self._series[start_index : end_index + 1]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor('#FFFFFF'))

        visible_series = self._visible_series()
        if not visible_series:
            painter.setPen(QColor('#6B7280'))
            painter.setFont(QFont('Segoe UI', 12, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, 'No data available')
            return

        plot = self._plot_rect()
        if plot.width() <= 0 or plot.height() <= 0:
            return

        values = [_to_float(row.get('sales_amount')) for row in visible_series]
        labels = [_hour_label(int(row.get('hour_order') or 0)) for row in visible_series]
        max_value = max(values) if values else 0.0
        if max_value <= 0:
            max_value = 1.0

        painter.setPen(QPen(QColor('#D1D5DB'), 1))
        painter.drawRect(plot)

        # Y-axis grid and labels (bold, with padding)
        painter.setFont(QFont('Segoe UI', 10))
        painter.setPen(QColor('#6B7280'))
        label_padding = 8
        for step in range(5):
            y = plot.bottom() - (plot.height() * step / 4)
            painter.drawLine(int(plot.left()), int(y), int(plot.right()), int(y))
            value = max_value * step / 4
            # drawText with padding so labels don't clip into axis
            painter.drawText(int(label_padding), int(y) - 20, int(plot.left() - label_padding - 6), 18, Qt.AlignRight, _fmt_money(value))

        # Build line points at hourly positions and interpolated 30-min midpoints
        points: List[QPointF] = []
        interp_midpoints: List[QPointF] = []
        count = max(1, len(values) - 1)
        for idx, value in enumerate(values):
            x = plot.left() + (plot.width() * idx / count if count else 0)
            y = plot.bottom() - (plot.height() * value / max_value)
            points.append(QPointF(int(x), int(y)))
            # compute midpoint between this and next (30-min marker)
            if idx < len(values) - 1:
                next_val = values[idx + 1]
                mid_x = plot.left() + (plot.width() * (idx + 0.5) / count)
                mid_y_val = (value + next_val) / 2.0
                mid_y = plot.bottom() - (plot.height() * mid_y_val / max_value)
                interp_midpoints.append(QPointF(int(mid_x), int(mid_y)))

        if points:
            poly_points = [QPointF(plot.left(), plot.bottom())] + points + [QPointF(plot.right(), plot.bottom())]
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(30, 112, 255, 36))
            painter.drawPolygon(QPolygonF(poly_points))

            painter.setPen(QPen(QColor('#1E70FF'), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolyline(QPolygonF(points))

            # draw interpolated 30-minute markers (smaller)
            painter.setPen(QPen(QColor('#0F4ED1'), 1))
            painter.setBrush(QBrush(QColor('#1E70FF')))
            for pt in interp_midpoints:
                painter.drawEllipse(pt, 2.0, 2.0)

            # draw main hourly markers
            painter.setPen(QPen(QColor('#0F4ED1'), 1))
            painter.setBrush(QBrush(QColor('#1E70FF')))
            for pt in points:
                painter.drawEllipse(pt, 3.5, 3.5)

        painter.setPen(QColor('#374151'))
        painter.setFont(QFont('Segoe UI', 9))
        for idx, label in enumerate(labels):
            x = plot.left() + (plot.width() * idx / count if count else 0)
            painter.drawText(QRectF(x - 18, plot.bottom() + 6, 36, 36), Qt.AlignCenter, label)


class _PaymentHistogramChart(_BaseChartWidget):
    _palette = [
        QColor('#1E70FF'),
        QColor('#F59E0B'),
        QColor('#10B981'),
        QColor('#EF4444'),
        QColor('#8B5CF6'),
        QColor('#14B8A6'),
        QColor('#F97316'),
        QColor('#64748B'),
    ]

    def __init__(self, rows: Sequence[Dict[str, Any]]):
        super().__init__(min_height=300)
        # normalize labels and amounts and sort by descending amount for histogram
        normalized: List[Dict[str, Any]] = []
        for row in rows:
            label = _display_payment_method(row.get('method'))
            normalized.append({'method': label, 'amount': _to_float(row.get('amount'))})
        self._rows = sorted(normalized, key=lambda r: r['amount'], reverse=True)

    def sizeHint(self) -> QSize:
        return QSize(900, 300)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor('#FFFFFF'))

        rows = self._rows
        if not rows:
            painter.setPen(QColor('#6B7280'))
            painter.setFont(QFont('Segoe UI', 12, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, 'No data available')
            return

        amounts = [r['amount'] for r in rows]
        labels = [r['method'] for r in rows]

        # left area for histogram, right area for legend (increased padding)
        chart_rect = self.rect().adjusted(40, 22, -40, -22)
        if chart_rect.width() <= 0 or chart_rect.height() <= 0:
            return

        # draw axes
        painter.setPen(QPen(QColor('#E5E7EB'), 1))

        max_value = max(amounts) if amounts else 1.0
        bar_area = QRectF(chart_rect.left() + 8, chart_rect.top() + 8, chart_rect.width() - 16, chart_rect.height() - 60)
        n = len(rows)
        bar_w = max(14, (bar_area.width() - (n - 1) * 10) / max(1, n))

        # draw bars (vertical histogram, left->right sorted tall->short)
        for idx, (label, amount) in enumerate(zip(labels, amounts)):
            x = bar_area.left() + idx * (bar_w + 10)
            h = (amount / max_value) * bar_area.height() if max_value else 0
            y = bar_area.bottom() - h
            color = self._palette[idx % len(self._palette)]
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(int(x), int(y), int(bar_w), int(h)))
            # amount label above bar
            painter.setPen(QColor('#111827'))
            painter.setFont(QFont('Segoe UI', 9))
            painter.drawText(QRectF(x, y - 25, bar_w, 16), Qt.AlignCenter, _fmt_money(amount))
            # short label under bar
            painter.setPen(QColor('#374151'))
            painter.setFont(QFont('Segoe UI', 9))
            painter.drawText(QRectF(x, bar_area.bottom() + 12, bar_w, 18), Qt.AlignCenter, _truncate(label, 12))



class _TopProductsBarChart(_BaseChartWidget):
    def __init__(self, rows: Sequence[Dict[str, Any]]):
        super().__init__(min_height=500)
        self._rows = sorted(list(rows), key=lambda row: _to_float(row.get('line_sales')), reverse=True)[:10]

    def _plot_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(230, 22, -150, -54)

    def sizeHint(self) -> QSize:
        return QSize(900, 320)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor('#FFFFFF'))

        rows = self._rows
        if not rows:
            painter.setPen(QColor('#6B7280'))
            painter.setFont(QFont('Segoe UI', 12, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, 'No data available')
            return

        plot = self._plot_rect()
        if plot.width() <= 0 or plot.height() <= 0:
            return

        values = [_to_float(row.get('line_sales')) for row in rows]
        labels = [str(row.get('product_name') or '') for row in rows]
        max_value = max(values) if values else 0.0
        if max_value <= 0:
            max_value = 1.0

        bar_h = 28
        row_gap = 15
        gradient = QLinearGradient(plot.left(), 0, plot.right(), 0)
        gradient.setColorAt(0.0, QColor('#60A5FA'))
        gradient.setColorAt(1.0, QColor('#1E70FF'))

        painter.setFont(QFont('Segoe UI', 10))

        for idx, row in enumerate(rows):
            total_row = bar_h + row_gap
            y = plot.top() + idx * total_row + (row_gap / 2)
            label = labels[idx] if idx < len(labels) else ''
            value = _to_float(row.get('line_sales'))
            bar_w = plot.width() * (value / max_value)
            # draw full product name in the left margin area (expanded)
            label_rect = QRectF(8, y, plot.left() - 26, bar_h + 4)
            painter.setPen(QColor('#374151'))
            # Use QFontMetrics.elidedText for pixel-accurate text truncation
            metrics = painter.fontMetrics()
            available_width = label_rect.width() - 5
            display_text = metrics.elidedText(label, Qt.ElideRight, int(available_width))
            painter.drawText(label_rect, Qt.AlignRight | Qt.AlignVCenter, display_text)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(QRectF(plot.left(), y, bar_w, bar_h), 6, 6)
            painter.setPen(QColor('#111827'))
            painter.drawText(QRectF(plot.left() + bar_w + 12, y - 1, 180, bar_h + 4), Qt.AlignVCenter, _fmt_money(value))


class _ChartReportCanvasPage1(QWidget):
    """Page 1: Headers, metrics, and first two chart cards."""
    def __init__(self, report_data: Any):
        super().__init__()
        self.setObjectName('chartReportCanvasPage1')
        self.setStyleSheet('QWidget#chartReportCanvasPage1 { background: #FFFFFF; }')
        payload = _safe_report(report_data)

        header = payload.get('header') or {}
        sales_summary = payload.get('sales_summary') or {}
        sales_by_hour = payload.get('sales_by_hour') or []
        payment_breakdown = payload.get('payment_breakdown') or []
        peak_hour = payload.get('peak_hour') or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel('Chart Report')
        title.setStyleSheet('font-size: 24px; font-weight: 800; color: #111827;')
        period_from_lbl = QLabel(f"Period From    :  {format_report_timestamp(header.get('period_from'))}")
        period_from_lbl.setWordWrap(True)
        period_from_lbl.setStyleSheet('color: #111827; font-size: 18px;')
        period_to_lbl = QLabel(f"Period To       :  {format_report_timestamp(header.get('period_to'))}")
        period_to_lbl.setWordWrap(True)
        period_to_lbl.setStyleSheet('color: #111827; font-size: 18px;')
        generated_at_lbl = QLabel(f"Generated At  :  {format_report_timestamp(header.get('generated_at'))}")
        generated_at_lbl.setWordWrap(True)
        generated_at_lbl.setStyleSheet('color: #111827; font-size: 18px;')
        generated_by_lbl = QLabel(f"Generated by  :  {header.get('generated_by') or '-'}")
        generated_by_lbl.setWordWrap(True)
        generated_by_lbl.setStyleSheet('color: #111827; font-size: 18px;')
        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(period_from_lbl)
        layout.addSpacing(3)
        layout.addWidget(period_to_lbl)
        layout.addSpacing(10)
        layout.addWidget(generated_at_lbl)
        layout.addSpacing(3)
        layout.addWidget(generated_by_lbl)
        layout.addSpacing(20)

        metrics = QFrame()
        metrics.setStyleSheet('QFrame { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; }')
        metrics_layout = QGridLayout(metrics)
        metrics_layout.setContentsMargins(14, 14, 14, 14)
        metrics_layout.setHorizontalSpacing(5)
        metrics_layout.setVerticalSpacing(20)

        peak_hour_label = _to_ampm_hour_label(peak_hour.get('hour_slot')) or '-'
        metric_rows = [
            ('Daily Avg Gross Sales', _fmt_money(sales_summary.get('gross_sales'))),
            ('Peak Sales Window', peak_hour_label),
            ('Peak Hourly Avg', _fmt_money(peak_hour.get('sales_amount')) if peak_hour and peak_hour.get('sales_amount') is not None else '-'),
        ]
        for row, (label, value) in enumerate(metric_rows):
            label_widget = QLabel(label)
            value_widget = QLabel(value)
            label_widget.setObjectName('chartMetricLabel')
            value_widget.setObjectName('chartMetricValue')
            label_widget.setStyleSheet('font-size: 20px; border: None; color: #374151;')
            value_widget.setStyleSheet('font-size: 20px; border: None; color: #111827;')
            metrics_layout.addWidget(label_widget, row, 0)
            metrics_layout.addWidget(value_widget, row, 1)
        metrics_layout.setColumnStretch(0, 1)
        metrics_layout.setColumnStretch(1, 3)

        layout.addWidget(metrics)

        layout.addWidget(
            _ChartCard(
                '1. Typical Daily Sales Flow',
                'Average sales by hour over the selected range.',
                _HourlySalesChart(sales_by_hour),
                min_height=320,
            )
        )
        layout.addWidget(
            _ChartCard(
                '2. Preferred Payment Methods',
                'Average payment histogram over the selected range.',
                _PaymentHistogramChart(payment_breakdown),
                min_height=300,
            )
        )

    def sizeHint(self) -> QSize:
        return QSize(980, 900)


class _ChartReportCanvasPage2(QWidget):
    """Page 2: Top products chart only."""
    def __init__(self, report_data: Any):
        super().__init__()
        self.setObjectName('chartReportCanvasPage2')
        self.setStyleSheet('QWidget#chartReportCanvasPage2 { background: #FFFFFF; }')
        payload = _safe_report(report_data)

        top_products = payload.get('top_products_by_sales_day') or payload.get('top_products') or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        layout.addWidget(
            _ChartCard(
                '3. Top 10 Best Sellers by Earnings',
                'Products ranked by average daily earnings, sorted highest to lowest.',
                _TopProductsBarChart(top_products),
                min_height=360,
            )
        )
        layout.addStretch(1)

    def sizeHint(self) -> QSize:
        return QSize(980, 600)


class _ChartReportCanvas(QWidget):
    def __init__(self, report_data: Any):
        super().__init__()
        self.setObjectName('chartReportCanvas')
        self.setStyleSheet('QWidget#chartReportCanvas { background: #FFFFFF; }')
        payload = _safe_report(report_data)

        header = payload.get('header') or {}
        sales_summary = payload.get('sales_summary') or {}
        sales_by_hour = payload.get('sales_by_hour') or []
        payment_breakdown = payload.get('payment_breakdown') or []
        top_products = payload.get('top_products_by_sales_day') or payload.get('top_products') or []
        peak_hour = payload.get('peak_hour') or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel('Chart Report')
        title.setStyleSheet('font-size: 24px; font-weight: 800; color: #111827;')
        period_from_lbl = QLabel(f"Period From    :  {format_report_timestamp(header.get('period_from'))}")
        period_from_lbl.setWordWrap(True)
        period_from_lbl.setStyleSheet('color: #111827; font-size: 18px;')
        period_to_lbl = QLabel(f"Period To       :  {format_report_timestamp(header.get('period_to'))}")
        period_to_lbl.setWordWrap(True)
        period_to_lbl.setStyleSheet('color: #111827; font-size: 18px;')
        generated_at_lbl = QLabel(f"Generated At  :  {format_report_timestamp(header.get('generated_at'))}")
        generated_at_lbl.setWordWrap(True)
        generated_at_lbl.setStyleSheet('color: #111827; font-size: 18px;')
        generated_by_lbl = QLabel(f"Generated by  :  {header.get('generated_by') or '-'}")
        generated_by_lbl.setWordWrap(True)
        generated_by_lbl.setStyleSheet('color: #111827; font-size: 18px;')
        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(period_from_lbl)
        layout.addSpacing(3)
        layout.addWidget(period_to_lbl)
        layout.addSpacing(10)
        layout.addWidget(generated_at_lbl)
        layout.addSpacing(3)
        layout.addWidget(generated_by_lbl)
        layout.addSpacing(20)

        metrics = QFrame()
        metrics.setStyleSheet('QFrame { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; }')
        metrics_layout = QGridLayout(metrics)
        metrics_layout.setContentsMargins(14, 14, 14, 14)
        metrics_layout.setHorizontalSpacing(5)
        metrics_layout.setVerticalSpacing(20)

        peak_hour_label2 = _to_ampm_hour_label(peak_hour.get('hour_slot')) or '-'
        metric_rows = [
            ('Daily Avg Gross Sales', _fmt_money(sales_summary.get('gross_sales'))),
            ('Peak Sales Window', peak_hour_label2),
            ('Peak Hourly Avg', _fmt_money(peak_hour.get('sales_amount')) if peak_hour and peak_hour.get('sales_amount') is not None else '-'),
        ]
        for row, (label, value) in enumerate(metric_rows):
            label_widget = QLabel(label)
            value_widget = QLabel(value)
            label_widget.setObjectName('chartMetricLabel')
            value_widget.setObjectName('chartMetricValue')
            label_widget.setStyleSheet('font-size: 20px; border: None; color: #374151;')
            value_widget.setStyleSheet('font-size: 20px; border: None; color: #111827;')
            metrics_layout.addWidget(label_widget, row, 0)
            metrics_layout.addWidget(value_widget, row, 1)
        metrics_layout.setColumnStretch(0, 1)
        metrics_layout.setColumnStretch(1, 3)

        layout.addWidget(metrics)

        layout.addWidget(
            _ChartCard(
                '1. Typical Daily Sales Flow',
                'Average sales by hour over the selected range.',
                _HourlySalesChart(sales_by_hour),
                min_height=320,
            )
        )
        layout.addWidget(
            _ChartCard(
                '2. Preferred Payment Methods',
                'Average payment histogram over the selected range.',
                _PaymentHistogramChart(payment_breakdown),
                min_height=300,
            )
        )
        layout.addWidget(
            _ChartCard(
                '3. Top 10 Best Sellers by Earnings',
                'Products ranked by average daily earnings, sorted highest to lowest.',
                _TopProductsBarChart(top_products),
                min_height=360,
            )
        )

        layout.addStretch(1)

    def sizeHint(self) -> QSize:
        return QSize(980, 1120)


def build_chart_report_canvas(report_data: Any) -> QWidget:
    _ensure_application()
    return _ChartReportCanvas(report_data)


def open_chart_report_viewer(parent_dlg: QDialog, *, report_data: dict | None = None) -> None:
    from modules.menu import report_viewers

    _ensure_application()
    overlay = report_viewers._create_overlay(parent_dlg)
    try:
        viewer, layout = report_viewers._build_shell(parent_dlg, report_type='chart')
        canvas = build_chart_report_canvas(report_data or {})
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet('QScrollArea { background: #FFFFFF; border: none; } QScrollArea > QWidget > QWidget { background: #FFFFFF; }')
        scroll.setAutoFillBackground(True)
        try:
            scroll.viewport().setAutoFillBackground(True)
        except Exception:
            pass
        scroll.setWidget(canvas)
        layout.addWidget(scroll)
        viewer.exec_()
    finally:
        report_viewers._cleanup_overlay(overlay)


def save_chart_report_pdf(report_data: dict | None, out_path) -> Any:
    _ensure_application()
    
    # Build page 1 canvas (headers, metrics, 2 charts)
    page1_canvas = _ChartReportCanvasPage1(report_data or {})
    page1_size = _prepare_widget_for_pdf(page1_canvas)
    
    # Build page 2 canvas (top products chart)
    page2_canvas = _ChartReportCanvasPage2(report_data or {})
    page2_size = _prepare_widget_for_pdf(page2_canvas)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(out_path))
    try:
        printer.setPageMargins(12, 12, 12, 12, QPrinter.Millimeter)
    except Exception:
        pass

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError('Unable to start PDF rendering for chart report.')

    try:
        # Use device pixels and leave a small inset so borders do not clip at the page edge.
        page_rect = printer.pageRect(QPrinter.DevicePixel).adjusted(8, 8, -8, -8)
        fit_margin = 0.94
        
        # Render page 1: scale to fit page width, no vertical scaling
        page1_scale_x = page_rect.width() / max(1, page1_size.width())
        page1_scale_y = page_rect.height() / max(1, page1_size.height())
        page1_scale = min(page1_scale_x, page1_scale_y) * fit_margin
        
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.translate(page_rect.left(), page_rect.top())
        painter.scale(page1_scale, page1_scale)
        page1_canvas.render(painter)
        
        # Start page 2
        printer.newPage()
        painter.resetTransform()
        painter.translate(page_rect.left(), page_rect.top())
        
        # Render page 2: scale to fit page width, no vertical scaling
        page2_scale_x = page_rect.width() / max(1, page2_size.width())
        page2_scale_y = page_rect.height() / max(1, page2_size.height())
        page2_scale = min(page2_scale_x, page2_scale_y) * fit_margin
        
        painter.scale(page2_scale, page2_scale)
        page2_canvas.render(painter)
    finally:
        painter.end()

    return out_path
