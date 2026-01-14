import datetime
import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase


def _tool_log(message: str) -> None:
    try:
        root = Path(__file__).resolve().parents[1]
        log_dir = root / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "tools.log"
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] list_fonts: {message}{os.linesep}")
    except Exception:
        pass

app = QApplication(sys.argv)
font_db = QFontDatabase()
_tool_log("Available font families:")
for family in font_db.families():
    _tool_log(family)
