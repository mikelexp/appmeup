from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Iterable
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


def shell_join(tokens: Iterable[str]) -> str:
    return " ".join(shlex.quote(t) for t in tokens)


def default_user_data_dir(desktop_filename: str) -> str:
    stem = Path(desktop_filename).stem
    slug = slugify(stem) or "webapp"
    return str(PROFILE_DIR / slug)


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes")
