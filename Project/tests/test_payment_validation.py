import pytest

from modules.payment.payment_panel import PaymentPanel


def make_panel(total, last_unalloc, voucher_amt, cash_val=0.0, tender_val=0.0, has_validation_error=False):
    # Create instance without running __init__ to avoid UI dependencies
    p = PaymentPanel.__new__(PaymentPanel)
    p._has_validation_error = has_validation_error
    p._last_unalloc = last_unalloc
    p._widgets = {'cash': 'cash', 'tender': 'tender'}
    p._get_total_amount = lambda: total
    p._get_validated_voucher = lambda widget: int(voucher_amt)
    mapping = {'cash': cash_val, 'tender': tender_val}
    p._get_validated_amount = lambda widget: mapping.get(widget, 0.0)
    return p


def test_exact_allocation_allows_pay():
    p = make_panel(total=10.0, last_unalloc=0.0, voucher_amt=0)
    assert p._is_payment_valid() is True


def test_over_alloc_without_voucher_disallowed():
    p = make_panel(total=10.0, last_unalloc=-1.0, voucher_amt=0)
    assert p._is_payment_valid() is False


def test_over_alloc_eq_voucher_disallowed():
    p = make_panel(total=10.0, last_unalloc=-2.0, voucher_amt=2)
    assert p._is_payment_valid() is False


def test_over_alloc_less_than_voucher_allowed():
    # over_alloc = 1.5 < voucher 2 -> allowed, ensure cash/tender satisfy tender>=cash
    p = make_panel(total=10.0, last_unalloc=-1.5, voucher_amt=2, cash_val=5.0, tender_val=6.0)
    assert p._is_payment_valid() is True


def test_cash_tender_mismatch_disallows():
    p = make_panel(total=10.0, last_unalloc=0.0, voucher_amt=0, cash_val=5.0, tender_val=4.0)
    assert p._is_payment_valid() is False
