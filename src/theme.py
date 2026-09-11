from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QLibraryInfo
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def configure_qt_theme() -> str:
    """Use the desktop's Qt theme without loading plugins from another Qt."""
    style_overridden = "QT_STYLE_OVERRIDE" in os.environ
    platform_overridden = "QT_QPA_PLATFORMTHEME" in os.environ
    bundled_plugin_path = Path(str(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)))

    if not platform_overridden and _is_plasma_session():
        # A distro PySide6 uses the distro Qt plugin directory. A wheel does
        # not, so do not inject a plugin directory from a different Qt build.
        if _has_platform_theme_plugin(bundled_plugin_path):
            os.environ["QT_QPA_PLATFORMTHEME"] = "kde"
            return "kde (system Qt plugins)"

    if style_overridden or platform_overridden:
        return "user override"
    return "default (Qt theme integration unavailable)"


def _is_plasma_session() -> bool:
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    return "kde" in desktop or "plasma" in desktop or bool(os.environ.get("KDE_FULL_SESSION"))


def _has_platform_theme_plugin(plugin_path: Path) -> bool:
    return (plugin_path / "platformthemes" / "KDEPlasmaPlatformTheme6.so").is_file()


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
