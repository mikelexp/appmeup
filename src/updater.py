from __future__ import annotations

import json
import logging
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from src.constants import APP_VERSION
from src.logger import setup_logging

logger = setup_logging()

GITHUB_REPO = "mikelexp/appmeup"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
BINARY_NAME = "appmeup"


class UpdateCheckSignals(QObject):
    update_available = Signal(str, str, str)
    up_to_date = Signal()
    error = Signal(str)


class UpdateCheckWorker(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = UpdateCheckSignals()

    def run(self) -> None:
        try:
            req = urllib.request.Request(API_URL, headers={"Accept": "application/json", "User-Agent": "AppMeUp"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            latest_tag = data.get("tag_name", "")
            latest_version = latest_tag.lstrip("v")
            release_url = data.get("html_url", "")

            download_url = ""
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith("-linux-x86_64.tar.gz"):
                    download_url = asset.get("browser_download_url", "")
                    break

            if not download_url:
                self.signals.error.emit("No compatible release found.")
                return

            if latest_version > APP_VERSION:
                self.signals.update_available.emit(latest_version, download_url, release_url)
            else:
                self.signals.up_to_date.emit()

        except Exception as exc:
            logger.warning("Update check failed: %s", exc)
            self.signals.error.emit(str(exc))


class UpdateDownloadSignals(QObject):
    progress = Signal(int, int)
    finished = Signal()
    error = Signal(str)


class UpdateDownloadWorker(QRunnable):
    def __init__(self, download_url: str) -> None:
        super().__init__()
        self.download_url = download_url
        self.signals = UpdateDownloadSignals()

    def run(self) -> None:
        try:
            binary_path = self._get_binary_path()
            if not binary_path:
                self.signals.error.emit("No se encontró el binario de la app.")
                return

            with tempfile.TemporaryDirectory() as tmpdir:
                tarball_path = Path(tmpdir) / "update.tar.gz"
                logger.info("Downloading update from %s", self.download_url)

                urllib.request.urlretrieve(
                    self.download_url,
                    tarball_path,
                )

                with tarfile.open(tarball_path, "r:gz") as tar:
                    tar.extractall(tmpdir)

                new_binary = Path(tmpdir) / BINARY_NAME
                if not new_binary.exists():
                    self.signals.error.emit("El paquete de actualización no es válido.")
                    return

                new_binary.chmod(new_binary.stat().st_mode | 0o111)
                shutil.copy2(new_binary, binary_path)
                logger.info("Updated binary at %s", binary_path)

            self.signals.finished.emit()

        except Exception as exc:
            logger.warning("Update download failed: %s", exc)
            self.signals.error.emit(str(exc))

    @staticmethod
    def _get_binary_path() -> str | None:
        path = Path(sys.argv[0]).resolve()
        if path.name == BINARY_NAME and path.exists():
            return str(path)
        return None
