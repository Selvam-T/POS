# table_operations.py - Unit helpers for POS system

UNIT_KG = "Kg"
UNIT_EACH = "Each"

def canonicalize_unit(unit_str: str) -> str:
    """Standardizes any unit string to internal 'Kg' or 'Each'."""
    if not unit_str:
        return UNIT_EACH
    u = unit_str.strip().lower()
    if u in ("kg", "g", "kilo", "kilogram", "kgs"):
        return UNIT_KG
    if u in ("each", "ea", "unit", "pc", "piece"):
        return UNIT_EACH
    return UNIT_EACH  # Default fallback

def get_display_unit(unit_canonical: str, quantity: float) -> str:
    """Derives the UI text from canonical data."""
    if unit_canonical == UNIT_KG:
        return "g" if quantity < 1.0 else "kg"
    return "ea"
