import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase

app = QApplication(sys.argv)
font_db = QFontDatabase()
print("Available font families:")
for family in font_db.families():
    print(family)
