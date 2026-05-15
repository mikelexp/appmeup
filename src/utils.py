from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from src.constants import PROFILE_DIR


def slugify(text: str) -> str:
    text = text.strip().lower().replace(" ", "-")
    text = re.sub(r"[^a-z0-9\-_.]", "", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"-+", "-", text).strip("-.")
    return text.lstrip(".")


def is_probable_webapp(exec_tokens: list[str]) -> bool:
    return any("--app=" in t for t in exec_tokens)


def default_user_data_dir(desktop_filename: str) -> str:
    stem = Path(desktop_filename).stem
    slug = slugify(stem) or "webapp"
    return str(PROFILE_DIR / slug)


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes")


def validate_url(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.\-]*://', url):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return url
