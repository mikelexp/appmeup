#!/usr/bin/env python3

from __future__ import annotations

import signal
import sys

from PySide6.QtWidgets import QApplication

from src.constants import APP_ID, APP_NAME
from src.icons import app_icon
from src.logger import setup_logging
from src.main_window import MainWindow
from src.theme import configure_qt_theme, ensure_placeholder_text_contrast

logger = setup_logging(verbose="--verbose" in sys.argv)


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    theme_mode = configure_qt_theme()
    logger.debug("Qt theme integration: %s", theme_mode)
    QApplication.setApplicationName(APP_NAME)
    QApplication.setDesktopFileName(APP_ID)
    app = QApplication([])
    ensure_placeholder_text_contrast(app)
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    logger.debug("Creating MainWindow")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
