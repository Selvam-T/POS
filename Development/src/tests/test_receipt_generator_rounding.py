from modules.payment.receipt_generator import generate_receipt_text_from_snapshot


def test_receipt_snapshot_marks_total_as_rounded_when_payable_total_differs():
    text = generate_receipt_text_from_snapshot(
        items=[
            {
                "quantity": 1,
                "name": "Rounding Item",
                "unit": "Each",
                "unit_price": 1.04,
                "line_total": 1.04,
            }
        ],
        payments=[{"payment_type": "CASH", "amount": 1.0, "tendered": 1.0}],
        status="PAID",
        payable_total=1.0,
    )

    assert "$ 1.04" in text
    assert "Subtotal:" not in text
    assert "Rounding:" not in text
    assert "Grand Total:" not in text
    assert "Total (round):" in text
    assert "$ 1.00" in text


def test_receipt_snapshot_uses_plain_total_when_no_rounding_applies():
    text = generate_receipt_text_from_snapshot(
        items=[
            {
                "quantity": 2,
                "name": "Plain Item",
                "unit": "Each",
                "unit_price": 1.50,
                "line_total": 3.00,
            }
        ],
        status="UNPAID",
        payable_total=3.00,
    )

    assert "Total:" in text
    assert "Total (round):" not in text
    assert "$ 3.00" in text
