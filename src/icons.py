from __future__ import annotations

import re
import shutil
import ssl
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QImage, QPixmap

from src.constants import ICON_DIR
from src.logger import setup_logging
from src.utils import slugify

logger = setup_logging()


def app_asset_path(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / name


def app_icon() -> QIcon:
    pixmap = QPixmap(str(app_asset_path("icon.png")))
    if not pixmap.isNull():
        return QIcon(pixmap)
    return QIcon()


def webapp_icon(icon_name: str) -> QIcon:
    if not icon_name:
        return app_icon()
    path = Path(icon_name).expanduser()
    if path.is_absolute():
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon
        return app_icon()
    icon = QIcon.fromTheme(icon_name)
    if not icon.isNull():
        return icon
    return app_icon()


class IconLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.icons: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "link":
            return
        attrs_dict = dict(attrs)
        rel = attrs_dict.get("rel", "")
        if "icon" not in rel:
            return
        href = attrs_dict.get("href", "")
        sizes = attrs_dict.get("sizes", "")
        type_ = attrs_dict.get("type", "")
        if href:
            self.icons.append({"href": href, "sizes": sizes or "", "type": type_ or ""})


def parse_icon_sizes(value: str) -> tuple[tuple[int, int], ...]:
    if not value.strip():
        return ()
    result: list[tuple[int, int]] = []
    for part in re.split(r"\s+", value.strip()):
        part = part.strip()
        if not part or part == "any":
            continue
        m = re.match(r"^(\d+)\s*[xX]\s*(\d+)$", part)
        if m:
            result.append((int(m.group(1)), int(m.group(2))))
    return tuple(result)


def score_icon_candidate(
    href: str,
    sizes_str: str,
    type_str: str,
    preferred_size: int = 64,
) -> int:
    score = 0
    sizes = parse_icon_sizes(sizes_str)
    if sizes:
        best = min(sizes, key=lambda s: abs(s[0] - preferred_size))
        diff = abs(best[0] - preferred_size)
        if diff == 0:
            score += 50
        elif diff <= 16:
            score += 30
        else:
            score += 10
    else:
        score += 20
    if type_str in ("image/png", "image/svg+xml"):
        score += 15
    if not urlparse(href).path.endswith(".ico"):
        score += 5
    return score


def fetch_url(url: str, ignore_ssl_errors: bool = False) -> bytes:
    req = Request(url, headers={"User-Agent": "AppMeUp/1.0"})
    ctx = ssl.create_default_context()
    if ignore_ssl_errors:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urlopen(req, timeout=15, context=ctx) as response:
            return response.read()
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc


def fetch_icon_for_url(page_url: str, slug: str, ignore_ssl_errors: bool = False) -> Path:
    logger.debug("Fetching icon for URL: %s", page_url)
    page_html = fetch_url(page_url, ignore_ssl_errors=ignore_ssl_errors).decode("utf-8", errors="replace")
    parser = IconLinkParser()
    parser.feed(page_html)

    candidates: list[tuple[int, str]] = []
    for icon in parser.icons:
        href = icon["href"]
        sizes = icon["sizes"]
        type_ = icon["type"]
        absolute = urljoin(page_url, href)
        score = score_icon_candidate(href, sizes, type_)
        candidates.append((score, absolute))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_url = candidates[0][1]
    else:
        parsed = urlparse(page_url)
        best_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"

    logger.debug("Best icon URL: %s", best_url)
    data = fetch_url(best_url, ignore_ssl_errors=ignore_ssl_errors)

    qimg = QImage()
    if not qimg.loadFromData(QByteArray(data)):
        raise RuntimeError(f"Could not decode icon from {best_url}")

    target = local_icon_target(slug)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not qimg.save(str(target), "PNG"):
        raise RuntimeError(f"Failed to save icon to {target}")
    logger.debug("Icon saved to %s", target)
    return target


def local_icon_target(slug: str) -> Path:
    return ICON_DIR / f"{slug}.png"


def icon_slug_for_desktop_filename(filename: str) -> str:
    return slugify(Path(filename).stem)


def store_icon_file(source_path: str, slug: str) -> Path:
    source = Path(source_path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"Icon not found: {source}")
    target = local_icon_target(slug)
    target.parent.mkdir(parents=True, exist_ok=True)
    ext = source.suffix.lower()
    if ext in (".svg", ".svgz"):
        shutil.copy2(str(source), str(target.with_suffix(".svg")))
        return Path(str(target.with_suffix(".svg")))
    if ext in (".png", ".jpg", ".jpeg", ".webp"):
        qimg = QImage(str(source))
        if qimg.isNull():
            raise ValueError(f"Could not decode icon: {source}")
        if not qimg.save(str(target), "PNG"):
            raise ValueError(f"Failed to save icon to {target}")
        return target
    raise ValueError(f"Unsupported icon format: {ext}")
