from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, qVersion
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from src.constants import APP_ID, APP_NAME


@dataclass(frozen=True)
class ThemeReport:
    style: str
    pyside_version: str
    qt_version: str
    plugin_path: str
    style_source: str
    platform: str


def configure_qt_platform() -> str:
    """Prepare desktop integration without changing user-selected variables."""
    if "QT_QPA_PLATFORMTHEME" not in os.environ and _is_plasma_session():
        plugin_path = Path(str(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)))
        if _has_platform_theme_plugin(plugin_path):
            os.environ["QT_QPA_PLATFORMTHEME"] = "kde"
            return "kde platform theme"

    if "QT_STYLE_OVERRIDE" in os.environ or "QT_QPA_PLATFORMTHEME" in os.environ:
        return "user override"
    return "Qt default"


def configure_qt_theme() -> str:
    """Compatibility name for callers using the previous bootstrap API."""
    return configure_qt_platform()


def inspect_effective_theme(app: QApplication) -> ThemeReport:
    """Inspect Qt's actual style and use a safe style only without integration."""
    style_source = "Qt"
    platform = app.platformName().lower()
    user_selected_platform = "QT_QPA_PLATFORMTHEME" in os.environ
    user_selected_style = "QT_STYLE_OVERRIDE" in os.environ
    if (platform in {"offscreen", "minimal", "minimalegl", "vnc"}
            and not user_selected_platform and not user_selected_style):
        breeze = QStyleFactory.create("Breeze")
        if breeze is not None:
            app.setStyle(breeze)
            style_source = "Breeze fallback"
        else:
            fusion = QStyleFactory.create("Fusion")
            if fusion is not None:
                app.setStyle(fusion)
                style_source = "Fusion fallback"

    return ThemeReport(
        style=app.style().objectName(),
        pyside_version=_pyside_version(),
        qt_version=qVersion(),
        plugin_path=str(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)),
        style_source=style_source,
        platform=platform,
    )


def create_application(argv: list[str] | None = None) -> tuple[QApplication, ThemeReport]:
    """Create QApplication only after Qt platform integration is configured."""
    configure_qt_platform()
    QApplication.setApplicationName(APP_NAME)
    QApplication.setDesktopFileName(APP_ID)
    app = QApplication(sys.argv if argv is None else argv)
    return app, inspect_effective_theme(app)


def _pyside_version() -> str:
    from PySide6 import __version__

    return __version__


def _is_plasma_session() -> bool:
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    return "kde" in desktop or "plasma" in desktop or bool(os.environ.get("KDE_FULL_SESSION"))


def _has_platform_theme_plugin(plugin_path: Path) -> bool:
    theme_dir = plugin_path / "platformthemes"
    try:
        return any(path.is_file() and "KDEPlasmaPlatformTheme" in path.name
                   for path in theme_dir.iterdir())
    except OSError:
        return False


def is_dark_theme() -> bool:
    return QApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128


def ensure_placeholder_text_contrast(app: QApplication) -> None:
    """Fix placeholder text only when the active desktop theme lacks contrast."""
    palette = app.palette()
    base = palette.color(QPalette.ColorRole.Base)
    placeholder = palette.color(QPalette.ColorRole.PlaceholderText)
    if contrast_ratio(base, placeholder) >= 3.0:
        return

    text = palette.color(QPalette.ColorRole.Text)
    if contrast_ratio(base, text) >= 3.0:
        palette.setColor(QPalette.ColorRole.PlaceholderText, text)
    else:
        palette.setColor(QPalette.ColorRole.PlaceholderText, palette.color(QPalette.ColorRole.WindowText))
    app.setPalette(palette)


def contrast_ratio(first: QColor, second: QColor) -> float:
    def luminance(color: QColor) -> float:
        channels = []
        for channel in (color.red(), color.green(), color.blue()):
            value = channel / 255
            channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    lighter = max(luminance(first), luminance(second))
    darker = min(luminance(first), luminance(second))
    return (lighter + 0.05) / (darker + 0.05)
