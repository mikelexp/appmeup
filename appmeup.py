#!/usr/bin/env python3

from __future__ import annotations

import signal
import sys

from PySide6.QtWidgets import QApplication

from src.constants import APP_ID, APP_NAME
from src.icons import app_icon
from src.main_window import MainWindow


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    QApplication.setApplicationName(APP_NAME)
    QApplication.setDesktopFileName(APP_ID)
    app = QApplication([])
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
