from __future__ import annotations

from typing import Optional


def canonicalize_product_code(code: Optional[str]) -> str:
    """Canonical form for product codes / barcodes used as keys and for storage."""
    return (code or "").strip().upper()


def canonicalize_title_text(text: Optional[str]) -> str:
    """Best-effort title/camel-ish casing for human-entered strings.

    Used for product names, suppliers, and (later) notes.
    """
    s = (text or "").strip()
    if not s:
        return ""

    for ch in ("_", "-", "\t"):
        s = s.replace(ch, " ")

    parts = [p for p in s.split(" ") if p]
    return " ".join([p[:1].upper() + p[1:].lower() if p else "" for p in parts])
