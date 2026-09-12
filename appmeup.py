#!/usr/bin/env python3

from __future__ import annotations

import os
import signal
import sys

from src.icons import app_icon
from src.logger import setup_logging
from src.main_window import MainWindow
from src.theme import create_application, ensure_placeholder_text_contrast

logger = setup_logging(verbose="--verbose" in sys.argv)


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app, theme_report = create_application(sys.argv)
    ensure_placeholder_text_contrast(app)
    logger.debug(
        "Qt runtime: platform_theme=%r style_override=%r plugin_path=%r "
        "platform=%s style=%s source=%s PySide6=%s Qt=%s",
        os.environ.get("QT_QPA_PLATFORMTHEME"),
        os.environ.get("QT_STYLE_OVERRIDE"),
        theme_report.plugin_path,
        theme_report.platform,
        theme_report.style,
        theme_report.style_source,
        theme_report.pyside_version,
        theme_report.qt_version,
    )
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    logger.debug("Creating MainWindow")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
