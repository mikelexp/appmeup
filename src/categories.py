from __future__ import annotations

import configparser
import re
from pathlib import Path
from typing import Iterable

from src.constants import DESKTOP_APPLICATION_DIRS

_category_cache: list[str] | None = None


def invalidate_category_cache() -> None:
    global _category_cache
    _category_cache = None


def collect_existing_categories() -> list[str]:
    global _category_cache
    if _category_cache is not None:
        return _category_cache

    seen: set[str] = set()
    categories: list[str] = []

    for directory in DESKTOP_APPLICATION_DIRS:
        if not directory.exists():
            continue
        for menu_file in sorted(directory.glob("*.desktop"), key=lambda p: p.name.lower()):
            try:
                parser = configparser.ConfigParser(interpolation=None)
                with menu_file.open("r", encoding="utf-8") as handle:
                    parser.read_file(handle)
                entry = parser["Desktop Entry"]
                raw = entry.get("Categories", "")
            except (OSError, configparser.Error, UnicodeDecodeError, KeyError):
                continue
            for part in re.split(r"[;,]", raw):
                cat = part.strip()
                if cat and cat not in seen:
                    seen.add(cat)
                    categories.append(cat)

    _category_cache = sorted(categories, key=str.casefold)
    return _category_cache


def parse_categories(value: str) -> list[str]:
    if not value.strip():
        return []
    result: list[str] = []
    for part in re.split(r"[;,]", value):
        part = part.strip()
        if part:
            result.append(part)
    return result


def serialize_categories(categories: Iterable[str]) -> str:
    return ";".join(categories) + (";" if categories else "")


def append_category_value(current_value: str, category: str) -> str:
    current = parse_categories(current_value)
    if category in current:
        return current_value
    return serialize_categories(current + [category])
