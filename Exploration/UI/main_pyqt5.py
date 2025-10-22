# main.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt


class POSWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("POS — Panels Side by Side")

        layout = QHBoxLayout(self)

        # ---------- Panel 1 (Transaction) ----------
        panel1 = QVBoxLayout()
        title1 = QLabel("<h2>Transaction</h2>")

        table = QTableWidget(5, 5)
        table.setHorizontalHeaderLabels(["", "Name", "Qty", "Unit Price", "Total"])
        for i in range(5):
            table.setItem(i, 1, QTableWidgetItem(f"Item {i+1}"))
            table.setItem(i, 2, QTableWidgetItem("1"))
            table.setItem(i, 3, QTableWidgetItem("2.00"))
            table.setItem(i, 4, QTableWidgetItem("2.00"))

        total_label = QLabel("Total: $100.99")

        buttons_bottom = QHBoxLayout()
        for name in ["CANCEL", "ON HOLD", "VIEW HOLDS"]:
            buttons_bottom.addWidget(QPushButton(name))

        panel1.addWidget(title1)
        panel1.addWidget(table)
        panel1.addWidget(total_label)
        panel1.addLayout(buttons_bottom)

        left_panel = QFrame()
        left_panel.setLayout(panel1)
        left_panel.setStyleSheet("background-color: lightblue; border: 2px solid black;")

        # ---------- Panel 2 (Payment) ----------
        panel2 = QVBoxLayout()
        title2 = QLabel("<h2>Payment</h2>")
        payment_grid = QGridLayout()
        methods = ["CASH", "NETS", "PAYNOW", "VOUCHER"]
        for i, name in enumerate(methods):
            payment_grid.addWidget(QPushButton(name), i, 0)
            payment_grid.addWidget(QLineEdit(), i, 1)
            payment_grid.addWidget(QPushButton("✔"), i, 2)
            payment_grid.addWidget(QPushButton("X"), i, 3)

        panel2.addWidget(title2)
        panel2.addLayout(payment_grid)

        right_panel = QFrame()
        right_panel.setLayout(panel2)
        right_panel.setStyleSheet("background-color: #ffe8cc; border: 2px solid black;")

        # Combine both panels
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = POSWindow()
    window.show()
    sys.exit(app.exec_())
