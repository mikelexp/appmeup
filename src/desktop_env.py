from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def current_desktop() -> str:
    return os.environ.get("XDG_CURRENT_DESKTOP", "").lower()


def detect_refresh_commands() -> list[list[str]]:
    desktop = current_desktop()
    commands: list[list[str]] = []
    if "kde" in desktop:
        if shutil.which("kbuildsycoca6"):
            commands.append(["kbuildsycoca6"])
        elif shutil.which("kbuildsycoca5"):
            commands.append(["kbuildsycoca5"])
        elif shutil.which("kbuildsycoca4"):
            commands.append(["kbuildsycoca4"])
    if "gnome" in desktop or "unity" in desktop:
        if shutil.which("update-desktop-database"):
            commands.append(["update-desktop-database"])
        if Path("/usr/share/glib-2.0/schemas/gschemas.compiled").exists():
            commands.append(["glib-compile-schemas", "/usr/share/glib-2.0/schemas/"])
    if shutil.which("xdg-desktop-menu"):
        commands.append(["xdg-desktop-menu", "forceupdate"])
    if shutil.which("gtk-update-icon-cache"):
        home = Path.home()
        for theme_dir in [home / ".local/share/icons/hicolor", Path("/usr/share/icons/hicolor")]:
            if theme_dir.exists():
                commands.append(["gtk-update-icon-cache", "-f", "-t", str(theme_dir)])
    return commands


def run_refresh_commands() -> list[str]:
    results: list[str] = []
    for cmd in detect_refresh_commands():
        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append(f"Warning: {shlex.join(cmd)} failed: {exc}")
    return results


def reveal_in_file_manager(path: Path) -> None:
    desktop = current_desktop()
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    if "kde" in desktop:
        subprocess.Popen(["kioclient5", "select", str(path)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif "gnome" in desktop or "unity" in desktop or "pantheon" in desktop:
        subprocess.Popen(["gio", "open", str(parent)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif "xfce" in desktop or "lxqt" in desktop:
        subprocess.Popen(["xdg-open", str(parent)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif "cinnamon" in desktop:
        subprocess.Popen(["cinnamon-open", str(parent)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif "mate" in desktop:
        subprocess.Popen(["caja", "--no-desktop", str(parent)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(parent)))
