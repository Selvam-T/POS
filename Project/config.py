"""
Configuration file for POS application.

This file centralizes color definitions and other configuration values
that need to be shared across multiple modules.
"""

# =============================================================================
# TABLE ROW COLORS
# =============================================================================
# Alternating row colors for the sales table.
#
# WHY DEFINED IN PYTHON INSTEAD OF QSS:
# -----------------------------------------------------------------------------
# Qt's QSS does support alternating row colors via QTableWidget::item:alternate,
# but that only works when table.setAlternatingRowColors(True) is enabled.
#
# In our sales table, we have cell widgets (QLineEdit for quantity input and
# QPushButton for delete) embedded in columns 2 and 5. These widgets sit inside
# container QWidgets, and their background colors must be set programmatically
# via setStyleSheet() to match the row color. QSS alternating colors don't
# automatically propagate to these embedded widgets.
#
# Therefore, we:
# 1. Disable Qt's built-in alternating colors (setAlternatingRowColors(False))
# 2. Manually assign background colors to both QTableWidgetItems (via setBackground)
#    and container widgets (via setStyleSheet) in Python
# 3. Centralize color values here for maintainability
# -----------------------------------------------------------------------------

ROW_COLOR_EVEN = '#add8e6'  # Light blue for even rows (0, 2, 4, ...)
ROW_COLOR_ODD = '#ffffe0'   # Light yellow for odd rows (1, 3, 5, ...)

# Highlight color for row deletion preview
ROW_COLOR_DELETE_HIGHLIGHT = '#ff6b6b'  # Light red/salmon

# =============================================================================
# ICONS
# =============================================================================
# Icon file paths
ICON_DELETE = 'assets/icons/delete.svg'  # Delete/remove button icon
