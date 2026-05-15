from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import QByteArray, QRect, QSize

from src.constants import APP_NAME
from src.logger import setup_logging

logger = setup_logging()

_SETTINGS_DIR = Path.home() / ".local" / "state" / "appmeup"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load settings: %s", exc)
    return {}


def _save_settings(settings: dict) -> None:
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not save settings: %s", exc)


def save_window_geometry(geometry: QRect) -> None:
    settings = _load_settings()
    settings["window"] = {
        "x": geometry.x(),
        "y": geometry.y(),
        "width": geometry.width(),
        "height": geometry.height(),
    }
    _save_settings(settings)


def restore_window_geometry() -> QRect | None:
    settings = _load_settings()
    if "window" in settings:
        w = settings["window"]
        return QRect(w["x"], w["y"], w["width"], w["height"])
    return None


def save_last_browser(path: str) -> None:
    settings = _load_settings()
    settings["last_browser"] = path
    _save_settings(settings)


def load_last_browser() -> str:
    return _load_settings().get("last_browser", "")
