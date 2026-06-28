from modules.payment.receipt_generator import generate_receipt_text_from_snapshot


def test_receipt_snapshot_shows_rounding_adjustment_when_payable_total_differs():
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

    assert "Subtotal:" in text
    assert "$ 1.04" in text
    assert "Rounding:" in text
    assert "-$ 0.04" in text
    assert "Grand Total:" in text
    assert "$ 1.00" in text
