from types import SimpleNamespace

from PyQt5.QtWidgets import QApplication, QLineEdit

from main import MainLoader


_APP = None


def ensure_app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def test_sale_total_changed_updates_payment_without_stealing_qty_focus():
    app = ensure_app()
    qty = QLineEdit()
    qty.setObjectName("qtyInput")
    qty.show()
    qty.setFocus()
    app.processEvents()

    calls = []
    panel = SimpleNamespace(
        set_payment_default=lambda total, focus=True: calls.append((total, focus))
    )
    window = MainLoader.__new__(MainLoader)
    window.payment_panel_controller = panel
    window._update_customer_display_from_sales = lambda: None

    MainLoader._on_sale_total_changed(window, 1.10)

    assert calls == [(1.10, False)]
    qty.close()
