from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from src.icons import fetch_icon_for_url, icon_slug_for_desktop_filename
from src.logger import setup_logging

logger = setup_logging()


class IconFetchWorker(QRunnable):
    def __init__(self, url: str, filename: str, ignore_ssl: bool = False) -> None:
        super().__init__()
        self.url = url
        self.filename = filename
        self.ignore_ssl = ignore_ssl

    def run(self) -> None:
        try:
            slug = icon_slug_for_desktop_filename(self.filename)
            icon_path = fetch_icon_for_url(self.url, slug, ignore_ssl_errors=self.ignore_ssl)
            self.signals.finished.emit(str(icon_path))
        except Exception as exc:
            logger.warning("Icon fetch failed for %s: %s", self.url, exc)
            self.signals.error.emit(str(exc))


class IconFetchSignals(QObject):
    finished = Signal(str)
    error = Signal(str)


IconFetchWorker.signals = IconFetchSignals()
