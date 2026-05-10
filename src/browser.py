from __future__ import annotations

import shutil
from pathlib import Path

from src.constants import BROWSER_NAME_FROM_BINARY


def detect_chromium() -> str:
    names = [
        "google-chrome-stable",
        "google-chrome",
        "chrome",
        "chromium-browser",
        "chromium",
        "brave-browser",
        "brave",
        "vivaldi-stable",
        "vivaldi",
    ]
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return ""


def detect_all_chromiums() -> dict[str, str]:
    found: dict[str, str] = {}
    names = [
        ("Google Chrome (Stable)", "google-chrome-stable"),
        ("Google Chrome", "google-chrome"),
        ("Chrome", "chrome"),
        ("Chromium (Browser)", "chromium-browser"),
        ("Chromium", "chromium"),
        ("Brave (Browser)", "brave-browser"),
        ("Brave", "brave"),
        ("Vivaldi Stable", "vivaldi-stable"),
        ("Vivaldi", "vivaldi"),
    ]
    for display_name, binary in names:
        path = shutil.which(binary)
        if path:
            found[display_name] = path
    return found


def resolve_executable(path_or_name: str) -> str:
    path = path_or_name.strip()
    if not path:
        return ""
    if "/" in path:
        return path if Path(path).exists() else ""
    resolved = shutil.which(path)
    return resolved if resolved else ""


def resolve_browser_identity(executable_path: str) -> str:
    try:
        resolved = Path(executable_path).resolve()
    except OSError:
        return "Unknown"
    for binary, name in BROWSER_NAME_FROM_BINARY.items():
        candidate = shutil.which(binary)
        if candidate and Path(candidate).resolve() == resolved:
            return name
    stem = resolved.stem
    for binary, name in BROWSER_NAME_FROM_BINARY.items():
        if binary == stem:
            return name
        if name.lower() == stem.lower():
            return name
    return "Unknown"
