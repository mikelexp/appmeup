from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


_SYSTEM_PLUGIN_PATHS = (
    Path("/usr/lib/qt6/plugins"),
    Path("/usr/lib64/qt6/plugins"),
    Path("/usr/lib/x86_64-linux-gnu/qt6/plugins"),
)


def configure_qt_theme() -> str:
    """Configure Qt to follow Plasma without overriding the user's widget style."""
    if os.environ.get("QT_STYLE_OVERRIDE") or os.environ.get("QT_QPA_PLATFORMTHEME"):
        return "user override"

    bundled_plugin_path = Path(
        str(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    )
    breeze_plugin_path = next(
        (path for path in _SYSTEM_PLUGIN_PATHS if (path / "styles" / "breeze6.so").exists()),
        None,
    )
    if breeze_plugin_path is None:
        # Do not point Qt at a platform theme that the bundled application does
        # not have. Qt can use its default theme without a platform theme plugin.
        if (bundled_plugin_path / "platformthemes" / "libqgtk3.so").is_file():
            os.environ["QT_QPA_PLATFORMTHEME"] = "gtk3"
            return "gtk3"
        return "default"

    plugin_paths = [str(breeze_plugin_path)]
    configured_plugin_path = os.environ.get("QT_PLUGIN_PATH")
    if configured_plugin_path:
        plugin_paths.insert(0, configured_plugin_path)

    bundled_plugin_path_string = str(bundled_plugin_path)
    if bundled_plugin_path_string not in plugin_paths:
        plugin_paths.insert(0, bundled_plugin_path_string)
    os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_paths)
    os.environ["QT_QPA_PLATFORMTHEME"] = "kde"

    plasma_style = _plasma_widget_style()
    if plasma_style:
        os.environ["QT_STYLE_OVERRIDE"] = plasma_style
        return f"kde/{plasma_style}"
    return "kde"


def _plasma_widget_style() -> str | None:
    """Read the widget style selected by Plasma without replacing user overrides."""
    settings_path = Path.home() / ".config" / "kdeglobals"
    style = ""
    if settings_path.is_file():
        style = QSettings(str(settings_path), QSettings.Format.IniFormat).value(
            "KDE/widgetStyle", "", type=str
        ).strip()
    if not style:
        try:
            result = subprocess.run(
                ["kreadconfig6", "--group", "KDE", "--key", "widgetStyle"],
                check=False,
                capture_output=True,
                text=True,
                timeout=1,
            )
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result is not None and result.returncode == 0:
            style = result.stdout.strip()
    return style or None


def is_dark_theme() -> bool:
    return QApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128


def ensure_placeholder_text_contrast(app: QApplication) -> None:
    """Fix placeholder text only when the active desktop theme lacks contrast."""
    palette = app.palette()
    base = palette.color(QPalette.ColorRole.Base)
    placeholder = palette.color(QPalette.ColorRole.PlaceholderText)
    if contrast_ratio(base, placeholder) >= 3.0:
        return

    palette.setColor(QPalette.ColorRole.PlaceholderText, palette.color(QPalette.ColorRole.Mid))
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
