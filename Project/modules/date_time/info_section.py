
from PyQt5.QtWidgets import QWidget, QMainWindow, QLabel
from PyQt5.QtCore import QTimer, QDateTime, Qt, QLocale
from config import COMPANY_NAME, DATE_FMT, DAY_FMT, TIME_FMT

class InfoSectionController(QWidget):
    def __init__(self):
        super().__init__()
        self.labelCompany = None
        self.labelDate = None
        self.labelDayTime = None
        self.timer = None
        self._clockLocale = QLocale(QLocale.English)

    def bind(self, root: QMainWindow):
        self.labelCompany = root.findChild(QLabel, 'labelCompany')
        self.labelDate = root.findChild(QLabel, 'labelDate')
        self.labelDayTime = root.findChild(QLabel, 'labelDayTime')
        if self.labelCompany:
            self.labelCompany.setText(COMPANY_NAME)
            self.labelCompany.setAlignment(Qt.AlignCenter)
        if self.labelDate:
            self.labelDate.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        if self.labelDayTime:
            self.labelDayTime.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return self

    def start_clock(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()
        return self

    def _update_clock(self):
        now = QDateTime.currentDateTime()
        if self.labelDate:
            date_text = self._clockLocale.toString(now.date(), DATE_FMT)
            self.labelDate.setText(date_text)
        if self.labelDayTime:
            day_text = self._clockLocale.toString(now.date(), DAY_FMT)
            time_text = now.toString(TIME_FMT).upper()
            self.labelDayTime.setText(f"{day_text}   {time_text}")
