# test_font.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtGui import QFontDatabase, QFont

def main():
    app = QApplication(sys.argv)

    families = QFontDatabase().families()

    root = QWidget()
    root.setWindowTitle("Installed Fonts (rendered in their own family)")
    root.resize(700, 900)

    scroll = QScrollArea(root)
    scroll.setWidgetResizable(True)

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setSpacing(6)
    layout.setContentsMargins(10, 10, 10, 10)

    for fam in families:
        lbl = QLabel(fam)
        # Use a readable size; adjust if too big/small on your screen
        lbl.setFont(QFont(fam, 14))
        layout.addWidget(lbl)

    # Add a little stretch so it doesn't hug the bottom
    layout.addStretch(1)

    scroll.setWidget(container)

    outer = QVBoxLayout(root)
    outer.addWidget(scroll)

    root.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()