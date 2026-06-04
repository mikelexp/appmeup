#!/usr/bin/env python3

from __future__ import annotations

import os
import signal
import sys

from PySide6.QtWidgets import QApplication

from src.constants import APP_ID, APP_NAME
from src.icons import app_icon
from src.logger import setup_logging
from src.main_window import MainWindow

logger = setup_logging(verbose="--verbose" in sys.argv)


def _configure_qt_theme() -> None:
    if os.environ.get("QT_STYLE_OVERRIDE") or os.environ.get("QT_QPA_PLATFORMTHEME"):
        return

    # Let Qt follow the desktop theme via the compatible GTK platform theme.
    os.environ["QT_QPA_PLATFORMTHEME"] = "gtk3"


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    _configure_qt_theme()
    QApplication.setApplicationName(APP_NAME)
    QApplication.setDesktopFileName(APP_ID)
    app = QApplication([])
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    logger.debug("Creating MainWindow")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
