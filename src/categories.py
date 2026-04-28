from __future__ import annotations

import configparser
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Iterable

from xdg.BaseDirectory import xdg_data_dirs
from xdg.Exceptions import ParsingError
from xdg.Menu import parse as parse_xdg_menu

from src.constants import DESKTOP_APPLICATION_DIRS


def _collect_categories_from_expr(node: ET.Element, target: set[str], negate: bool = False) -> None:
    include = node.get("Include", "")
    exclude = node.get("Exclude", "")
    if include:
        for cat in re.split(r"[,|]", include):
            cat = cat.strip()
            if cat and cat.startswith("!"):
                if not negate:
                    _collect_categories_from_expr(node, target, negate=True)
            elif not negate:
                target.add(cat)
    if exclude:
        for cat in re.split(r"[,|]", exclude):
            cat = cat.strip()
            if cat and not cat.startswith("!"):
                target.discard(cat)


def _menu_categories(menu: ET.Element) -> set[str]:
    cats: set[str] = set()
    for child in menu:
        tag = child.tag
        if tag == "DefaultAppDir":
            continue
        if tag == "Name":
            continue
        if tag == "Directory":
            continue
        if tag == "DirectoryDir":
            continue
        if tag == "AppDir":
            continue
        if tag == "Move":
            continue
        if tag == "OnlyUnallocated":
            continue
        if tag == "NotOnlyUnallocated":
            continue
        if tag == "Deleted":
            continue
        if tag == "NotDeleted":
            continue
        if tag in ("Include", "Exclude"):
            _collect_categories_from_expr(child, cats)
        elif tag == "Menu":
            cats.update(_menu_categories(child))
    return cats


def _menu_child_names(menu: ET.Element) -> set[str]:
    names: set[str] = set()
    for child in menu:
        if child.tag == "Menu":
            for grandchild in child:
                if grandchild.tag == "Name":
                    names.add(grandchild.text or "")
                    break
    return names


def _menu_name_variants(name: str) -> set[str]:
    return {name, name.lower(), name.replace("-", " "), name.replace("-", " ").lower()}


def _preferred_category(menu_name: str, counts: dict[str, int]) -> str | None:
    variants = _menu_name_variants(menu_name)
    best = None
    best_count = 0
    for cat, count in counts.items():
        cat_lower = cat.lower().replace("-", " ").replace("_", " ")
        if cat_lower in variants or cat in variants or cat.lower() in variants:
            if count > best_count:
                best = cat
                best_count = count
    return best


def _collect_menu_file_categories(menu_file: Path) -> list[str]:
    try:
        root = parse_xdg_menu(str(menu_file))
    except (ParsingError, OSError):
        return []
    menu_cats = _menu_categories(root)
    child_names = _menu_child_names(root)
    if not menu_cats:
        return []
    menu_name = menu_file.stem.replace("-", " ").title()
    counts = Counter(menu_cats)
    preferred = _preferred_category(menu_name, counts)
    if preferred:
        counts[preferred] += 1000
    sorted_cats = [cat for cat, _ in counts.most_common()]
    return sorted_cats


def collect_existing_categories() -> list[str]:
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

    return sorted(categories, key=str.casefold)


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
