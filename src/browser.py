from __future__ import annotations

import shutil
from pathlib import Path

from src.constants import BROWSER_DETECTION_ORDER, BROWSER_DISPLAY_NAMES, BROWSER_NAME_FROM_BINARY


def detect_chromium() -> str:
    for name in BROWSER_DETECTION_ORDER:
        path = shutil.which(name)
        if path:
            return path
    return ""


def detect_all_chromiums() -> dict[str, str]:
    found: dict[str, str] = {}
    for binary in BROWSER_DETECTION_ORDER:
        path = shutil.which(binary)
        if path:
            found[BROWSER_DISPLAY_NAMES[binary]] = path
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
