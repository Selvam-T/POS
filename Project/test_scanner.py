"""
Simple test script to verify barcode scanner is working.
Run this and scan a barcode to see if it's detected.
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from modules.devices import BarcodeScanner


class ScannerTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Barcode Scanner Test")
        self.setGeometry(100, 100, 400, 200)
        
        # Create UI
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        self.label = QLabel("Waiting for barcode scan...\nScan a barcode now!")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 16pt; padding: 20px;")
        layout.addWidget(self.label)
        
        self.result = QLabel("")
        self.result.setAlignment(Qt.AlignCenter)
        self.result.setStyleSheet("font-size: 14pt; color: blue; padding: 10px;")
        layout.addWidget(self.result)
        
        # Initialize scanner
        print("Initializing scanner...")
        self.scanner = BarcodeScanner()
        self.scanner.barcode_scanned.connect(self.on_barcode)
        self.scanner.start()
        print("Scanner started. Scan a barcode now!")
        
    def on_barcode(self, barcode):
        """Called when barcode is scanned"""
        print(f"✓ BARCODE RECEIVED: {barcode}")
        self.label.setText(f"Last scanned barcode:")
        self.result.setText(barcode)
        self.result.setStyleSheet("font-size: 20pt; color: green; padding: 10px; font-weight: bold;")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScannerTest()
    window.show()
    sys.exit(app.exec_())
