from escpos.printer import Network

def mm_to_dots(mm):
    """Convert millimeters to printer dots (Epson TM-T82x ≈ 8 dots/mm at 203 DPI)."""
    return int(mm * 8)

def test_print(ip="192.168.0.10", port=9100, paper_width_mm=80):
    try:
        p = Network(ip, port)

        # --- Constants ---
        total_dots = mm_to_dots(paper_width_mm)  # Total printable width in dots
        max_dots = 576  # TM-T82x hardware max for 80mm roll
        if total_dots > max_dots:
            total_dots = max_dots

        print(f"🧾 Paper width: {paper_width_mm} mm -> {total_dots} dots printable width")

        # --- Helper: Set margins safely ---
        def set_margins(left_mm, right_mm):
            left = mm_to_dots(left_mm)
            right = mm_to_dots(right_mm)
            width = total_dots - (left + right)
            if width <= 0:
                width = total_dots
            p._raw(b'\x1D\x4C' + chr(left).encode() + b'\x00')   # GS L nL nH
            p._raw(b'\x1D\x57' + chr(width).encode() + b'\x00')  # GS W nL nH
            return left, width

        # --- TEST 1: Default margins (full width) ---
        left, width = set_margins(0, 0)
        p._raw(b'\x1B\x4D\x00')  # ESC M 0 → Font A
        p.text("=== TEST 1: FONT A, FULL WIDTH ===\n")
        p.text("Font: A (12x24)\n")
        p.text(f"Margins: Left {left} dots, Width {width} dots\n\n")
        p.text("ABCDEFGHIJKLMNOPQRSTUVWXYZ11111111111111111end\n")
        p.text("abcdefghijklmnopqrstuvwxyz\n")
        p.text("0123456789\n\n")
        p.cut()

        # --- TEST 2: Font B, 2.5mm left, 2.5mm right ---
        left, width = set_margins(2.5, 2.5)
        p._raw(b'\x1B\x4D\x01')  # ESC M 1 → Font B
        p.text("=== TEST 2: FONT B, 2.5MM MARGINS ===\n")
        p.text("Font: B (9x17)\n")
        p.text(f"Left: {left} dots, Width: {width} dots\n\n")
        p.text("ABCDEFGHIJKLMNOPQRSTUVWXYZ\n")
        p.text("abcdefghijklmnopqrstuvwxyz\n")
        p.text("0123456789\n\n")
        p.cut()

        # --- TEST 3: Font A, 5mm left, 5mm right ---
        left, width = set_margins(5, 5)
        p._raw(b'\x1B\x4D\x00')  # Font A
        p.text("=== TEST 3: FONT A, 5MM MARGINS ===\n")
        p.text("Font: A (12x24)\n")
        p.text(f"Left: {left} dots, Width: {width} dots\n\n")
        p.text("ABCDEFGHIJKLMNOPQRSTUVWXYZ\n")
        p.text("abcdefghijklmnopqrstuvwxyz\n")
        p.text("0123456789\n\n")
        p.cut()

        print("✅ Test prints sent successfully.")

    except Exception as e:
        print("❌ Printing failed:", e)

if __name__ == "__main__":
    # change paper_width_mm=58 if you switch rolls
    test_print(paper_width_mm=80)
