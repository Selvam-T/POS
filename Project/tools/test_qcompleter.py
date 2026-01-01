import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QCompleter
from PyQt5.QtCore import Qt

class DemoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QLineEdit + QCompleter Demo")
        layout = QVBoxLayout(self)

        self.label = QLabel("Type to search (try: CAR, DOG, O):")
        layout.addWidget(self.label)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Search Product Name")
        layout.addWidget(self.line_edit)

        # Test data
        product_names = ["CAR1", "CAR2", "CAR3", "DOG", "DOGO", "ODOG"]

        completer = QCompleter(product_names, self.line_edit)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.line_edit.setCompleter(completer)

        # Show selected value
        self.line_edit.editingFinished.connect(self.show_selected)

    def show_selected(self):
        self.label.setText(f"Selected: {self.line_edit.text()}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DemoWidget()
    w.show()
    sys.exit(app.exec_())