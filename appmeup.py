#!/usr/bin/env python3

from __future__ import annotations

import configparser
import os
import re
import shlex
import shutil
import ssl
import subprocess
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


APP_ID = "mikelexp.appmeup"
APP_NAME = "AppMeUp!"
USER_APPLICATIONS_DIR = Path.home() / ".local/share/applications"
DESKTOP_APPLICATION_DIRS = [
    USER_APPLICATIONS_DIR,
    Path("/usr/local/share/applications"),
    Path("/usr/share/applications"),
]
ICON_DIR = Path.home() / ".local/share/icons/appmeup"
ICON_THEME_DIR = Path.home() / ".local/share/icons/hicolor"
PROFILE_DIR = Path.home() / ".local/share/appmeup/profiles"
DEFAULT_CATEGORIES = ""
DEFAULT_CATEGORY_CHOICES = ["AudioVideo", "Development", "Education", "Game", "Graphics", "Network", "Office", "Settings", "System", "Utility", "WebBrowser"]
WEBAPP_MARKER_KEY = "X-AppMeUp-WebApp"
WEBAPP_VERSION_KEY = "X-AppMeUp-Version"
ICON_SSL_IGNORE_KEY = "X-AppMeUp-IgnoreIconSSLErrors"
ICON_PREVIEW_SIZE = 64


def app_asset_path(name: str) -> Path:
    return Path(__file__).resolve().with_name(name)


def app_icon() -> QIcon:
    icon_path = app_asset_path("icon.png")
    return QIcon(str(icon_path)) if icon_path.exists() else QIcon()


def webapp_icon(icon_name: str) -> QIcon:
    candidate = icon_name.strip()
    if not candidate:
        return app_icon()

    path = Path(candidate).expanduser()
    if path.exists():
        return QIcon(str(path))

    theme_icon = QIcon.fromTheme(candidate)
    if not theme_icon.isNull():
        return theme_icon

    return app_icon()


def detect_chromium() -> str:
    candidates = [
        "chromium",
        "chromium-browser",
        "google-chrome-stable",
        "google-chrome",
        "chrome",
    ]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return ""


def resolve_executable(path_or_name: str) -> str:
    candidate = path_or_name.strip()
    if not candidate:
        return ""
    if os.path.isabs(candidate):
        return candidate if Path(candidate).exists() else ""
    return shutil.which(candidate) or ""


def current_desktop() -> str:
    """Return the active desktop environment identifier, lowercased."""
    de = os.environ.get("XDG_CURRENT_DESKTOP", os.environ.get("DESKTOP_SESSION", ""))
    return de.lower()


def detect_refresh_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    de = current_desktop()

    # KDE Plasma: rebuild the system configuration cache
    for binary in ("kbuildsycoca6", "kbuildsycoca5", "kbuildsycoca"):
        if shutil.which(binary):
            commands.append([binary])
            break

    # Standard freedesktop MIME/desktop database (GNOME, XFCE, Cinnamon, MATE, LXQt, Budgie…)
    if shutil.which("update-desktop-database"):
        commands.append(["update-desktop-database", str(USER_APPLICATIONS_DIR)])

    # Force desktop menu rebuild — picks up new entries immediately in XFCE, MATE, Cinnamon, LXQt
    if shutil.which("xdg-desktop-menu"):
        commands.append(["xdg-desktop-menu", "forceupdate"])

    # Refresh the local icon theme cache so updated launcher icons are visible immediately.
    if shutil.which("gtk-update-icon-cache") and ICON_THEME_DIR.exists():
        commands.append(["gtk-update-icon-cache", "-f", "-t", str(ICON_THEME_DIR)])

    # GNOME Shell: notify the shell via dbus so the launcher updates without a logout
    if "gnome" in de or "budgie" in de or "unity" in de:
        if shutil.which("gdbus"):
            commands.append([
                "gdbus", "call", "--session",
                "--dest", "org.gnome.Shell",
                "--object-path", "/org/gnome/Shell",
                "--method", "org.gnome.Shell.Eval",
                "''",
            ])

    return commands


def run_refresh_commands() -> list[str]:
    messages: list[str] = []
    de = current_desktop()
    if de:
        messages.append(f"Desktop: {de}")
    for command in detect_refresh_commands():
        try:
            completed = subprocess.run(command, check=True, capture_output=True, text=True)
            output = completed.stdout.strip() or completed.stderr.strip()
            label = " ".join(command)
            messages.append(f"{label}: ok" if not output else f"{label}: {output}")
        except (OSError, subprocess.CalledProcessError) as exc:
            messages.append(f"{' '.join(command)}: {exc}")
    if len(messages) == (1 if de else 0):
        messages.append(
            "No desktop refresh tools found (kbuildsycoca, update-desktop-database, xdg-desktop-menu).\n"
            "You may need to log out and back in for the app to appear in the launcher."
        )
    return messages


def reveal_in_file_manager(path: Path) -> None:
    target_dir = path.parent if path.suffix else path
    target_dir.mkdir(parents=True, exist_ok=True)

    commands = []
    if shutil.which("xdg-open"):
        commands.append(["xdg-open", str(target_dir)])
    if sys.platform == "darwin" and shutil.which("open"):
        commands.append(["open", str(target_dir)])

    for command in commands:
        try:
            subprocess.Popen(command)
            return
        except OSError:
            continue

    raise RuntimeError("Could not open the target folder in the file manager.")


def collect_existing_categories() -> list[str]:
    categories = set(DEFAULT_CATEGORY_CHOICES)

    for directory in DESKTOP_APPLICATION_DIRS:
        if not directory.exists():
            continue
        for desktop_file in directory.glob("*.desktop"):
            parser = configparser.ConfigParser(interpolation=None)
            try:
                with desktop_file.open("r", encoding="utf-8") as handle:
                    parser.read_file(handle)
            except (OSError, configparser.Error, UnicodeDecodeError):
                continue

            if "Desktop Entry" not in parser:
                continue
            value = parser["Desktop Entry"].get("Categories", "")
            for category in value.split(";"):
                cleaned = category.strip()
                if cleaned:
                    categories.add(cleaned)

    return sorted(categories, key=str.lower)


def parse_categories(value: str) -> list[str]:
    seen: set[str] = set()
    categories: list[str] = []
    for category in value.split(";"):
        cleaned = category.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            categories.append(cleaned)
    return categories


def serialize_categories(categories: Iterable[str]) -> str:
    cleaned = [category.strip() for category in categories if category.strip()]
    return f"{';'.join(cleaned)};" if cleaned else ""


def append_category_value(current_value: str, category: str) -> str:
    selected = parse_categories(current_value)
    cleaned = category.strip()
    if cleaned and cleaned not in selected:
        selected.append(cleaned)
    return serialize_categories(selected)


def slugify(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip().lower())
    normalized = normalized.strip("._-")
    return normalized or "webapp"


def is_probable_webapp(exec_tokens: list[str]) -> bool:
    if not exec_tokens:
        return False
    binary = Path(exec_tokens[0]).name.lower()
    if "chrome" not in binary and "chromium" not in binary:
        return False
    return any(token.startswith("--app=") for token in exec_tokens[1:])


def shell_join(tokens: Iterable[str]) -> str:
    return shlex.join(list(tokens))


def default_user_data_dir(desktop_filename: str) -> str:
    stem = Path(desktop_filename.strip() or "webapp.desktop").stem
    return str(PROFILE_DIR / slugify(stem))


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class IconLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        data = {key.lower(): value or "" for key, value in attrs}
        rel = data.get("rel", "").lower()
        href = data.get("href", "").strip()
        if not href:
            return
        if "icon" in rel or "apple-touch-icon" in rel or "mask-icon" in rel:
            self.links.append(href)


def fetch_url(url: str, ignore_ssl_errors: bool = False) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    context = ssl._create_unverified_context() if ignore_ssl_errors else None
    with urlopen(request, timeout=10, context=context) as response:
        return response.read()


def fetch_icon_for_url(page_url: str, slug: str, ignore_ssl_errors: bool = False) -> Path:
    parsed = urlparse(page_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("The URL must use http or https.")

    html_bytes = fetch_url(page_url, ignore_ssl_errors=ignore_ssl_errors)
    parser = IconLinkParser()
    parser.feed(html_bytes.decode("utf-8", errors="ignore"))

    candidates: list[str] = []
    for href in parser.links:
        candidate = urljoin(page_url, href)
        if candidate not in candidates:
            candidates.append(candidate)
    fallback = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
    if fallback not in candidates:
        candidates.append(fallback)

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    target = ICON_DIR / f"{slug}.png"

    errors: list[str] = []
    for candidate in candidates:
        try:
            image_data = fetch_url(candidate, ignore_ssl_errors=ignore_ssl_errors)
            pixmap = QPixmap()
            if not pixmap.loadFromData(image_data):
                errors.append(f"{candidate}: unsupported format")
                continue
            if pixmap.isNull():
                errors.append(f"{candidate}: empty image")
                continue
            if not pixmap.save(str(target), "PNG"):
                errors.append(f"{candidate}: could not save PNG")
                continue
            return target
        except (OSError, URLError, ValueError) as exc:
            errors.append(f"{candidate}: {exc}")

    detail = "\n".join(errors[-5:])
    raise RuntimeError(f"Could not fetch a valid icon.\n{detail}")


def local_icon_target(slug: str) -> Path:
    return ICON_DIR / f"{slug}.png"


def icon_slug_for_desktop_filename(filename: str) -> str:
    return slugify(Path(filename.strip() or "webapp.desktop").stem)


def store_icon_file(source_path: str, slug: str) -> Path:
    source = Path(source_path).expanduser()
    if not source.exists():
        raise ValueError(f"Icon file does not exist: {source}")

    pixmap = QPixmap(str(source))
    if pixmap.isNull():
        icon = QIcon(str(source))
        pixmap = icon.pixmap(256, 256)
    if pixmap.isNull():
        raise ValueError(f"Unsupported icon format: {source}")

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    target = local_icon_target(slug)
    if not pixmap.save(str(target), "PNG"):
        raise RuntimeError(f"Could not save the icon to {target}")
    return target


@dataclass
class WebAppConfig:
    name: str = ""
    url: str = ""
    comment: str = ""
    categories: str = DEFAULT_CATEGORIES
    icon_path: str = ""
    chromium_path: str = field(default_factory=detect_chromium)
    desktop_filename: str = "webapp.desktop"
    desktop_path: str = ""
    user_data_dir: str = ""
    wm_class: str = ""
    wm_name: str = ""
    app_id: str = ""
    app_launch_url_for_shortcuts_menu_item: str = ""
    window_size: str = ""
    window_position: str = ""
    proxy_server: str = ""
    proxy_bypass_list: str = ""
    user_agent: str = ""
    enable_features: str = ""
    disable_features: str = ""
    lang: str = ""
    profile_directory: str = ""
    remote_debugging_port: str = ""
    vmodule: str = ""
    trace_startup_file: str = ""
    virtual_time_budget: str = ""
    proxy_pac_url: str = ""
    host_resolver_rules: str = ""
    autoplay_policy: str = ""
    use_gl: str = ""
    force_device_scale_factor: str = ""
    ozone_platform_hint: str = ""
    disk_cache_dir: str = ""
    disk_cache_size: str = ""
    extra_args: str = ""
    ignore_icon_ssl_errors: bool = False
    new_window: bool = False
    incognito: bool = False
    kiosk: bool = False
    start_maximized: bool = False
    start_fullscreen: bool = False
    ignore_certificate_errors: bool = False
    allow_insecure_localhost: bool = False
    guest: bool = False
    headless: bool = False
    disable_gpu: bool = False
    disable_extensions: bool = False
    no_first_run: bool = False
    auto_open_devtools_for_tabs: bool = False
    disable_dev_shm_usage: bool = False
    remote_debugging_pipe: bool = False
    trace_startup: bool = False
    enable_logging: bool = False
    disable_web_security: bool = False
    no_sandbox: bool = False
    disable_background_networking: bool = False
    disable_notifications: bool = False
    mute_audio: bool = False
    disable_popup_blocking: bool = False
    disable_software_rasterizer: bool = False
    disable_renderer_backgrounding: bool = False
    process_per_site: bool = False
    single_process: bool = False
    opened_from_existing: bool = False

    def ensure_filename(self) -> str:
        filename = self.desktop_filename.strip()
        if not filename.endswith(".desktop"):
            filename = f"{filename}.desktop"
        self.desktop_filename = filename
        return filename

    def effective_wm_class(self) -> str:
        explicit = self.wm_class.strip()
        if explicit:
            return slugify(explicit)

        filename = Path(self.ensure_filename()).stem
        derived = slugify(filename)
        if derived and derived != "webapp":
            return derived

        derived = slugify(self.name)
        if derived and derived != "webapp":
            return derived

        derived = slugify(urlparse(self.url.strip()).netloc)
        if derived and derived != "webapp":
            return derived

        return "appmeup-webapp"

    def build_exec_tokens(self) -> list[str]:
        resolved_chromium = resolve_executable(self.chromium_path)
        if not resolved_chromium:
            raise ValueError("No Chromium executable is configured.")
        if not self.url.strip():
            raise ValueError("The URL is required.")

        wm_class = self.effective_wm_class()
        tokens = [resolved_chromium, f"--app={self.url.strip()}"]
        if self.user_data_dir.strip():
            tokens.append(f"--user-data-dir={self.user_data_dir.strip()}")
        if wm_class:
            tokens.append(f"--class={wm_class}")
        if self.wm_name.strip():
            tokens.append(f"--name={self.wm_name.strip()}")
        if self.app_id.strip():
            tokens.append(f"--app-id={self.app_id.strip()}")
        if self.app_launch_url_for_shortcuts_menu_item.strip():
            tokens.append(f"--app-launch-url-for-shortcuts-menu-item={self.app_launch_url_for_shortcuts_menu_item.strip()}")
        if self.window_size.strip():
            tokens.append(f"--window-size={self.window_size.strip()}")
        if self.window_position.strip():
            tokens.append(f"--window-position={self.window_position.strip()}")
        if self.proxy_server.strip():
            tokens.append(f"--proxy-server={self.proxy_server.strip()}")
        if self.proxy_bypass_list.strip():
            tokens.append(f"--proxy-bypass-list={self.proxy_bypass_list.strip()}")
        if self.user_agent.strip():
            tokens.append(f"--user-agent={self.user_agent.strip()}")
        if self.enable_features.strip():
            tokens.append(f"--enable-features={self.enable_features.strip()}")
        if self.disable_features.strip():
            tokens.append(f"--disable-features={self.disable_features.strip()}")
        if self.lang.strip():
            tokens.append(f"--lang={self.lang.strip()}")
        if self.profile_directory.strip():
            tokens.append(f"--profile-directory={self.profile_directory.strip()}")
        if self.remote_debugging_port.strip():
            tokens.append(f"--remote-debugging-port={self.remote_debugging_port.strip()}")
        if self.vmodule.strip():
            tokens.append(f"--vmodule={self.vmodule.strip()}")
        if self.trace_startup_file.strip():
            tokens.append(f"--trace-startup-file={self.trace_startup_file.strip()}")
        if self.virtual_time_budget.strip():
            tokens.append(f"--virtual-time-budget={self.virtual_time_budget.strip()}")
        if self.proxy_pac_url.strip():
            tokens.append(f"--proxy-pac-url={self.proxy_pac_url.strip()}")
        if self.host_resolver_rules.strip():
            tokens.append(f"--host-resolver-rules={self.host_resolver_rules.strip()}")
        if self.autoplay_policy.strip():
            tokens.append(f"--autoplay-policy={self.autoplay_policy.strip()}")
        if self.use_gl.strip():
            tokens.append(f"--use-gl={self.use_gl.strip()}")
        if self.force_device_scale_factor.strip():
            tokens.append(f"--force-device-scale-factor={self.force_device_scale_factor.strip()}")
        if self.ozone_platform_hint.strip():
            tokens.append(f"--ozone-platform-hint={self.ozone_platform_hint.strip()}")
        if self.disk_cache_dir.strip():
            tokens.append(f"--disk-cache-dir={self.disk_cache_dir.strip()}")
        if self.disk_cache_size.strip():
            tokens.append(f"--disk-cache-size={self.disk_cache_size.strip()}")
        if self.ignore_certificate_errors:
            tokens.append("--ignore-certificate-errors")
        if self.allow_insecure_localhost:
            tokens.append("--allow-insecure-localhost")
        if self.new_window:
            tokens.append("--new-window")
        if self.incognito:
            tokens.append("--incognito")
        if self.kiosk:
            tokens.append("--kiosk")
        if self.start_maximized:
            tokens.append("--start-maximized")
        if self.start_fullscreen:
            tokens.append("--start-fullscreen")
        if self.guest:
            tokens.append("--guest")
        if self.headless:
            tokens.append("--headless")
        if self.disable_gpu:
            tokens.append("--disable-gpu")
        if self.disable_extensions:
            tokens.append("--disable-extensions")
        if self.no_first_run:
            tokens.append("--no-first-run")
        if self.auto_open_devtools_for_tabs:
            tokens.append("--auto-open-devtools-for-tabs")
        if self.disable_dev_shm_usage:
            tokens.append("--disable-dev-shm-usage")
        if self.remote_debugging_pipe:
            tokens.append("--remote-debugging-pipe")
        if self.trace_startup:
            tokens.append("--trace-startup")
        if self.enable_logging:
            tokens.append("--enable-logging")
        if self.disable_web_security:
            tokens.append("--disable-web-security")
        if self.no_sandbox:
            tokens.append("--no-sandbox")
        if self.disable_background_networking:
            tokens.append("--disable-background-networking")
        if self.disable_notifications:
            tokens.append("--disable-notifications")
        if self.mute_audio:
            tokens.append("--mute-audio")
        if self.disable_popup_blocking:
            tokens.append("--disable-popup-blocking")
        if self.disable_software_rasterizer:
            tokens.append("--disable-software-rasterizer")
        if self.disable_renderer_backgrounding:
            tokens.append("--disable-renderer-backgrounding")
        if self.process_per_site:
            tokens.append("--process-per-site")
        if self.single_process:
            tokens.append("--single-process")

        extra = self.extra_args.strip()
        if extra:
            try:
                tokens.extend(shlex.split(extra))
            except ValueError as exc:
                raise ValueError(f"Invalid extra flags: {exc}") from exc

        return tokens

    def to_desktop_entry(self) -> str:
        filename = self.ensure_filename()
        target_path = USER_APPLICATIONS_DIR / filename
        self.desktop_path = str(target_path)
        self.wm_class = self.effective_wm_class()
        exec_line = shell_join(self.build_exec_tokens())

        lines = [
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            f"Name={self.name.strip()}",
            f"Comment={self.comment.strip()}",
            f"Exec={exec_line}",
            f"Icon={self.icon_path.strip()}",
            f"Categories={serialize_categories(parse_categories(self.categories))}",
            "Terminal=false",
            "StartupNotify=true",
            f"StartupWMClass={self.wm_class}",
            f"{WEBAPP_MARKER_KEY}=true",
            f"{WEBAPP_VERSION_KEY}=1",
            f"{ICON_SSL_IGNORE_KEY}={'true' if self.ignore_icon_ssl_errors else 'false'}",
            "",
        ]
        return "\n".join(lines)


def parse_exec(exec_line: str) -> tuple[list[str], dict[str, str | bool], list[str]]:
    tokens = shlex.split(exec_line)
    options: dict[str, str | bool] = {}
    extra: list[str] = []

    known_value_prefixes = {
        "--app=": "app_url",
        "--user-data-dir=": "user_data_dir",
        "--class=": "wm_class",
        "--name=": "wm_name",
        "--app-id=": "app_id",
        "--app-launch-url-for-shortcuts-menu-item=": "app_launch_url_for_shortcuts_menu_item",
        "--window-size=": "window_size",
        "--window-position=": "window_position",
        "--proxy-server=": "proxy_server",
        "--proxy-bypass-list=": "proxy_bypass_list",
        "--user-agent=": "user_agent",
        "--enable-features=": "enable_features",
        "--disable-features=": "disable_features",
        "--lang=": "lang",
        "--profile-directory=": "profile_directory",
        "--remote-debugging-port=": "remote_debugging_port",
        "--vmodule=": "vmodule",
        "--trace-startup-file=": "trace_startup_file",
        "--virtual-time-budget=": "virtual_time_budget",
        "--proxy-pac-url=": "proxy_pac_url",
        "--host-resolver-rules=": "host_resolver_rules",
        "--autoplay-policy=": "autoplay_policy",
        "--use-gl=": "use_gl",
        "--force-device-scale-factor=": "force_device_scale_factor",
        "--ozone-platform-hint=": "ozone_platform_hint",
        "--disk-cache-dir=": "disk_cache_dir",
        "--disk-cache-size=": "disk_cache_size",
    }
    known_bool_flags = {
        "--ignore-certificate-errors": "ignore_certificate_errors",
        "--allow-insecure-localhost": "allow_insecure_localhost",
        "--new-window": "new_window",
        "--incognito": "incognito",
        "--kiosk": "kiosk",
        "--start-maximized": "start_maximized",
        "--start-fullscreen": "start_fullscreen",
        "--guest": "guest",
        "--headless": "headless",
        "--disable-gpu": "disable_gpu",
        "--disable-extensions": "disable_extensions",
        "--no-first-run": "no_first_run",
        "--auto-open-devtools-for-tabs": "auto_open_devtools_for_tabs",
        "--disable-dev-shm-usage": "disable_dev_shm_usage",
        "--remote-debugging-pipe": "remote_debugging_pipe",
        "--trace-startup": "trace_startup",
        "--enable-logging": "enable_logging",
        "--disable-web-security": "disable_web_security",
        "--no-sandbox": "no_sandbox",
        "--disable-background-networking": "disable_background_networking",
        "--disable-notifications": "disable_notifications",
        "--mute-audio": "mute_audio",
        "--disable-popup-blocking": "disable_popup_blocking",
        "--disable-software-rasterizer": "disable_software_rasterizer",
        "--disable-renderer-backgrounding": "disable_renderer_backgrounding",
        "--process-per-site": "process_per_site",
        "--single-process": "single_process",
    }

    for token in tokens[1:]:
        matched = False
        for prefix, key in known_value_prefixes.items():
            if token.startswith(prefix):
                options[key] = token[len(prefix) :]
                matched = True
                break
        if matched:
            continue
        if token in known_bool_flags:
            options[known_bool_flags[token]] = True
            continue
        extra.append(token)

    return tokens, options, extra


def load_desktop_file(path: Path) -> WebAppConfig:
    parser = configparser.ConfigParser(interpolation=None)
    with path.open("r", encoding="utf-8") as handle:
        parser.read_file(handle)

    if "Desktop Entry" not in parser:
        raise ValueError("The file does not contain a [Desktop Entry] section.")

    entry = parser["Desktop Entry"]
    exec_line = entry.get("Exec", "").strip()
    tokens, options, extra = parse_exec(exec_line)
    marker = parse_bool(entry.get(WEBAPP_MARKER_KEY), default=False)
    if not marker and not is_probable_webapp(tokens):
        raise ValueError("The .desktop file does not appear to be a Chromium web app.")

    config = WebAppConfig(
        name=entry.get("Name", ""),
        url=str(options.get("app_url", "")),
        comment=entry.get("Comment", ""),
        categories=entry.get("Categories", DEFAULT_CATEGORIES),
        icon_path=entry.get("Icon", ""),
        chromium_path=tokens[0] if tokens else detect_chromium(),
        desktop_filename=path.name,
        desktop_path=str(path),
        user_data_dir=str(options.get("user_data_dir", "")),
        wm_class=str(options.get("wm_class", entry.get("StartupWMClass", ""))),
        wm_name=str(options.get("wm_name", "")),
        app_id=str(options.get("app_id", "")),
        app_launch_url_for_shortcuts_menu_item=str(options.get("app_launch_url_for_shortcuts_menu_item", "")),
        window_size=str(options.get("window_size", "")),
        window_position=str(options.get("window_position", "")),
        proxy_server=str(options.get("proxy_server", "")),
        proxy_bypass_list=str(options.get("proxy_bypass_list", "")),
        user_agent=str(options.get("user_agent", "")),
        enable_features=str(options.get("enable_features", "")),
        disable_features=str(options.get("disable_features", "")),
        lang=str(options.get("lang", "")),
        profile_directory=str(options.get("profile_directory", "")),
        remote_debugging_port=str(options.get("remote_debugging_port", "")),
        vmodule=str(options.get("vmodule", "")),
        trace_startup_file=str(options.get("trace_startup_file", "")),
        virtual_time_budget=str(options.get("virtual_time_budget", "")),
        proxy_pac_url=str(options.get("proxy_pac_url", "")),
        host_resolver_rules=str(options.get("host_resolver_rules", "")),
        autoplay_policy=str(options.get("autoplay_policy", "")),
        use_gl=str(options.get("use_gl", "")),
        force_device_scale_factor=str(options.get("force_device_scale_factor", "")),
        ozone_platform_hint=str(options.get("ozone_platform_hint", "")),
        disk_cache_dir=str(options.get("disk_cache_dir", "")),
        disk_cache_size=str(options.get("disk_cache_size", "")),
        extra_args=shell_join(extra),
        ignore_icon_ssl_errors=parse_bool(entry.get(ICON_SSL_IGNORE_KEY), default=False),
        new_window=bool(options.get("new_window", False)),
        incognito=bool(options.get("incognito", False)),
        kiosk=bool(options.get("kiosk", False)),
        start_maximized=bool(options.get("start_maximized", False)),
        start_fullscreen=bool(options.get("start_fullscreen", False)),
        ignore_certificate_errors=bool(options.get("ignore_certificate_errors", False)),
        allow_insecure_localhost=bool(options.get("allow_insecure_localhost", False)),
        guest=bool(options.get("guest", False)),
        headless=bool(options.get("headless", False)),
        disable_gpu=bool(options.get("disable_gpu", False)),
        disable_extensions=bool(options.get("disable_extensions", False)),
        no_first_run=bool(options.get("no_first_run", False)),
        auto_open_devtools_for_tabs=bool(options.get("auto_open_devtools_for_tabs", False)),
        disable_dev_shm_usage=bool(options.get("disable_dev_shm_usage", False)),
        remote_debugging_pipe=bool(options.get("remote_debugging_pipe", False)),
        trace_startup=bool(options.get("trace_startup", False)),
        enable_logging=bool(options.get("enable_logging", False)),
        disable_web_security=bool(options.get("disable_web_security", False)),
        no_sandbox=bool(options.get("no_sandbox", False)),
        disable_background_networking=bool(options.get("disable_background_networking", False)),
        disable_notifications=bool(options.get("disable_notifications", False)),
        mute_audio=bool(options.get("mute_audio", False)),
        disable_popup_blocking=bool(options.get("disable_popup_blocking", False)),
        disable_software_rasterizer=bool(options.get("disable_software_rasterizer", False)),
        disable_renderer_backgrounding=bool(options.get("disable_renderer_backgrounding", False)),
        process_per_site=bool(options.get("process_per_site", False)),
        single_process=bool(options.get("single_process", False)),
        opened_from_existing=True,
    )
    return config


def collect_existing_webapps() -> list[WebAppConfig]:
    webapps: list[WebAppConfig] = []
    seen: set[Path] = set()

    for directory in DESKTOP_APPLICATION_DIRS:
        if not directory.exists():
            continue
        for desktop_file in sorted(directory.glob("*.desktop"), key=lambda path: path.name.lower()):
            resolved = desktop_file.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                parser = configparser.ConfigParser(interpolation=None)
                with desktop_file.open("r", encoding="utf-8") as handle:
                    parser.read_file(handle)
                entry = parser["Desktop Entry"]
                if not parse_bool(entry.get(WEBAPP_MARKER_KEY), default=False):
                    continue
                webapps.append(load_desktop_file(desktop_file))
            except (OSError, configparser.Error, UnicodeDecodeError, ValueError, KeyError):
                continue

    return sorted(webapps, key=lambda config: (config.name.lower(), config.desktop_filename.lower()))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(800, 500)
        self._dirty = False
        self._filename_auto_sync = True
        self.current_config = WebAppConfig()

        self._build_ui()
        self.load_config(self.current_config)
        self.refresh_webapps_list()
        self.statusBar().showMessage("Ready.")

    def _build_ui(self) -> None:
        self.setStatusBar(QStatusBar(self))

        file_menu = self.menuBar().addMenu("File")

        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_config)
        file_menu.addAction(new_action)

        open_action = QAction("Open .desktop…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_desktop_dialog)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_desktop)
        file_menu.addAction(save_action)

        central = QWidget(self)
        outer_layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_basic_tab(), "Web App Options")
        self.tabs.addTab(self._build_chromium_tab(), "Chromium Options")
        self.webapps_tab = self._build_webapps_tab()
        self.tabs.addTab(self.webapps_tab, "Installed Web Apps")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        outer_layout.addWidget(self.tabs)

        actions_layout = QHBoxLayout()
        self.target_path_label = QLabel()
        self.target_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        actions_layout.addWidget(self.target_path_label, stretch=1)

        self.save_button = QPushButton("Save .desktop")
        self.save_button.clicked.connect(self.save_desktop)
        actions_layout.addWidget(self.save_button)
        outer_layout.addLayout(actions_layout)

        self.setCentralWidget(central)

    def _build_webapps_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        actions_layout = QHBoxLayout()
        self.webapps_count_label = QLabel()
        actions_layout.addWidget(self.webapps_count_label, stretch=1)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_webapps_list)
        actions_layout.addWidget(refresh_button)
        layout.addLayout(actions_layout)

        self.webapps_list = QListWidget()
        self.webapps_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.webapps_list.setSpacing(8)
        self.webapps_list.itemDoubleClicked.connect(self.open_webapp_list_item)
        self.webapps_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.webapps_list.customContextMenuRequested.connect(self._show_webapp_context_menu)
        layout.addWidget(self.webapps_list)

        return container

    def _build_basic_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        form_group = QGroupBox("Application")
        form = QFormLayout(form_group)

        self.name_input = QLineEdit()
        self.name_input.textEdited.connect(self._on_name_changed)
        form.addRow("Title", self.name_input)

        self.url_input = QLineEdit()
        self.url_input.textEdited.connect(self.mark_dirty)
        self.url_input.editingFinished.connect(self._on_url_edit_finished)
        form.addRow("URL", self.url_input)

        self.comment_input = QLineEdit()
        self.comment_input.textEdited.connect(self.mark_dirty)
        form.addRow("Description", self.comment_input)

        categories_row = QWidget()
        categories_layout = QHBoxLayout(categories_row)
        categories_layout.setContentsMargins(0, 0, 0, 0)
        self.categories_select = QComboBox()
        self.categories_select.addItem("Select a category…")
        self.categories_select.addItems(collect_existing_categories())
        self.categories_select.currentIndexChanged.connect(self._on_category_selected)
        categories_layout.addWidget(self.categories_select)
        self.categories_input = QLineEdit()
        self.categories_input.setPlaceholderText("Network;WebBrowser;")
        self.categories_input.textEdited.connect(self.mark_dirty)
        categories_layout.addWidget(self.categories_input, stretch=1)
        form.addRow("Categories", categories_row)

        filename_row = QWidget()
        filename_layout = QHBoxLayout(filename_row)
        filename_layout.setContentsMargins(0, 0, 0, 0)
        self.filename_input = QLineEdit()
        self.filename_input.textEdited.connect(self._on_filename_changed)
        filename_layout.addWidget(self.filename_input)
        open_folder_button = QPushButton("Open Folder")
        open_folder_button.clicked.connect(self.open_desktop_folder)
        filename_layout.addWidget(open_folder_button)
        form.addRow(".desktop Filename", filename_row)

        chromium_row = QWidget()
        chromium_layout = QHBoxLayout(chromium_row)
        chromium_layout.setContentsMargins(0, 0, 0, 0)
        self.chromium_input = QLineEdit()
        self.chromium_input.textEdited.connect(self.mark_dirty)
        chromium_layout.addWidget(self.chromium_input)
        chromium_detect_button = QPushButton("Detect")
        chromium_detect_button.clicked.connect(self.detect_chromium_path)
        chromium_layout.addWidget(chromium_detect_button)
        form.addRow("Chromium Executable", chromium_row)

        icon_row = QWidget()
        icon_layout = QHBoxLayout(icon_row)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_input = QLineEdit()
        self.icon_input.textEdited.connect(self.mark_dirty)
        self.icon_input.textChanged.connect(self.update_icon_preview)
        icon_layout.addWidget(self.icon_input)
        browse_icon_button = QPushButton("Browse")
        browse_icon_button.clicked.connect(self.choose_icon_file)
        icon_layout.addWidget(browse_icon_button)
        fetch_icon_button = QPushButton("Fetch")
        fetch_icon_button.clicked.connect(self.fetch_icon)
        icon_layout.addWidget(fetch_icon_button)
        form.addRow("Icon", icon_row)

        self.ignore_icon_ssl_errors_check = self._check_box("Ignore SSL certificate errors when fetching icons")
        form.addRow("Icon SSL", self.ignore_icon_ssl_errors_check)

        self.icon_preview_label = QLabel("No icon")
        self.icon_preview_label.setAlignment(Qt.AlignCenter)
        self.icon_preview_label.setFixedSize(ICON_PREVIEW_SIZE + 16, ICON_PREVIEW_SIZE + 16)
        self.icon_preview_label.setStyleSheet("QLabel { border: 1px solid palette(mid); padding: 4px; }")
        form.addRow("Preview", self.icon_preview_label)

        layout.addWidget(form_group)

        return container

    def _build_chromium_tab(self) -> QWidget:
        container = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)

        identity_group = QGroupBox("Identity And Profile")
        identity_grid = QGridLayout(identity_group)
        self.user_data_dir_input = self._path_row_button("Browse", self.choose_user_data_dir)
        identity_grid.addWidget(QLabel("user-data-dir"), 0, 0)
        identity_grid.addWidget(self.user_data_dir_input["widget"], 0, 1)
        self.profile_directory_input = self._line_edit("Default")
        identity_grid.addWidget(QLabel("profile-directory"), 1, 0)
        identity_grid.addWidget(self.profile_directory_input, 1, 1)
        self.lang_input = self._line_edit("en-US")
        identity_grid.addWidget(QLabel("lang"), 2, 0)
        identity_grid.addWidget(self.lang_input, 2, 1)
        self.user_agent_input = self._line_edit()
        identity_grid.addWidget(QLabel("user-agent"), 3, 0)
        identity_grid.addWidget(self.user_agent_input, 3, 1)
        self.enable_features_input = self._line_edit()
        identity_grid.addWidget(QLabel("enable-features"), 4, 0)
        identity_grid.addWidget(self.enable_features_input, 4, 1)
        self.disable_features_input = self._line_edit()
        identity_grid.addWidget(QLabel("disable-features"), 5, 0)
        identity_grid.addWidget(self.disable_features_input, 5, 1)
        inner_layout.addWidget(identity_group)

        app_group = QGroupBox("App And Window")
        app_grid = QGridLayout(app_group)
        self.wm_class_input = self._line_edit()
        app_grid.addWidget(QLabel("class"), 0, 0)
        app_grid.addWidget(self.wm_class_input, 0, 1)
        self.wm_name_input = self._line_edit()
        app_grid.addWidget(QLabel("name"), 1, 0)
        app_grid.addWidget(self.wm_name_input, 1, 1)
        self.app_id_input = self._line_edit()
        app_grid.addWidget(QLabel("app-id"), 2, 0)
        app_grid.addWidget(self.app_id_input, 2, 1)
        self.app_launch_url_input = self._line_edit()
        app_grid.addWidget(QLabel("app-launch-url-for-shortcuts-menu-item"), 3, 0)
        app_grid.addWidget(self.app_launch_url_input, 3, 1)
        self.window_size_input = self._line_edit("1280,800")
        app_grid.addWidget(QLabel("window-size"), 4, 0)
        app_grid.addWidget(self.window_size_input, 4, 1)
        self.window_position_input = self._line_edit("50,50")
        app_grid.addWidget(QLabel("window-position"), 5, 0)
        app_grid.addWidget(self.window_position_input, 5, 1)
        inner_layout.addWidget(app_group)

        network_group = QGroupBox("Network")
        network_grid = QGridLayout(network_group)
        self.proxy_server_input = self._line_edit()
        network_grid.addWidget(QLabel("proxy-server"), 0, 0)
        network_grid.addWidget(self.proxy_server_input, 0, 1)
        self.proxy_bypass_input = self._line_edit()
        network_grid.addWidget(QLabel("proxy-bypass-list"), 1, 0)
        network_grid.addWidget(self.proxy_bypass_input, 1, 1)
        self.proxy_pac_url_input = self._line_edit()
        network_grid.addWidget(QLabel("proxy-pac-url"), 2, 0)
        network_grid.addWidget(self.proxy_pac_url_input, 2, 1)
        self.host_resolver_rules_input = self._line_edit()
        network_grid.addWidget(QLabel("host-resolver-rules"), 3, 0)
        network_grid.addWidget(self.host_resolver_rules_input, 3, 1)
        inner_layout.addWidget(network_group)

        debug_group = QGroupBox("Debug And Automation")
        debug_grid = QGridLayout(debug_group)
        self.remote_debugging_port_input = self._line_edit("9222")
        debug_grid.addWidget(QLabel("remote-debugging-port"), 0, 0)
        debug_grid.addWidget(self.remote_debugging_port_input, 0, 1)
        self.vmodule_input = self._line_edit()
        debug_grid.addWidget(QLabel("vmodule"), 1, 0)
        debug_grid.addWidget(self.vmodule_input, 1, 1)
        self.trace_startup_file_input = self._line_edit()
        debug_grid.addWidget(QLabel("trace-startup-file"), 2, 0)
        debug_grid.addWidget(self.trace_startup_file_input, 2, 1)
        self.virtual_time_budget_input = self._line_edit()
        debug_grid.addWidget(QLabel("virtual-time-budget"), 3, 0)
        debug_grid.addWidget(self.virtual_time_budget_input, 3, 1)
        inner_layout.addWidget(debug_group)

        rendering_group = QGroupBox("Rendering And Media")
        rendering_grid = QGridLayout(rendering_group)
        self.autoplay_policy_input = self._line_edit()
        rendering_grid.addWidget(QLabel("autoplay-policy"), 0, 0)
        rendering_grid.addWidget(self.autoplay_policy_input, 0, 1)
        self.use_gl_input = self._line_edit()
        rendering_grid.addWidget(QLabel("use-gl"), 1, 0)
        rendering_grid.addWidget(self.use_gl_input, 1, 1)
        self.force_device_scale_factor_input = self._line_edit("1.0")
        rendering_grid.addWidget(QLabel("force-device-scale-factor"), 2, 0)
        rendering_grid.addWidget(self.force_device_scale_factor_input, 2, 1)
        self.ozone_platform_hint_input = self._line_edit("auto")
        rendering_grid.addWidget(QLabel("ozone-platform-hint"), 3, 0)
        rendering_grid.addWidget(self.ozone_platform_hint_input, 3, 1)
        self.disk_cache_dir_input = self._line_edit()
        rendering_grid.addWidget(QLabel("disk-cache-dir"), 4, 0)
        rendering_grid.addWidget(self.disk_cache_dir_input, 4, 1)
        self.disk_cache_size_input = self._line_edit()
        rendering_grid.addWidget(QLabel("disk-cache-size"), 5, 0)
        rendering_grid.addWidget(self.disk_cache_size_input, 5, 1)
        inner_layout.addWidget(rendering_group)

        bool_group = QGroupBox("Boolean Flags")
        bool_layout = QVBoxLayout(bool_group)
        self.new_window_check = self._check_box("new-window")
        self.incognito_check = self._check_box("incognito")
        self.kiosk_check = self._check_box("kiosk")
        self.start_maximized_check = self._check_box("start-maximized")
        self.start_fullscreen_check = self._check_box("start-fullscreen")
        self.ignore_certificate_errors_check = self._check_box("ignore-certificate-errors")
        self.allow_insecure_localhost_check = self._check_box("allow-insecure-localhost")
        self.guest_check = self._check_box("guest")
        self.headless_check = self._check_box("headless")
        self.disable_gpu_check = self._check_box("disable-gpu")
        self.disable_extensions_check = self._check_box("disable-extensions")
        self.no_first_run_check = self._check_box("no-first-run")
        self.auto_open_devtools_check = self._check_box("auto-open-devtools-for-tabs")
        self.disable_dev_shm_usage_check = self._check_box("disable-dev-shm-usage")
        self.remote_debugging_pipe_check = self._check_box("remote-debugging-pipe")
        self.trace_startup_check = self._check_box("trace-startup")
        self.enable_logging_check = self._check_box("enable-logging")
        self.disable_web_security_check = self._check_box("disable-web-security")
        self.no_sandbox_check = self._check_box("no-sandbox")
        self.disable_background_networking_check = self._check_box("disable-background-networking")
        self.disable_notifications_check = self._check_box("disable-notifications")
        self.mute_audio_check = self._check_box("mute-audio")
        self.disable_popup_blocking_check = self._check_box("disable-popup-blocking")
        self.disable_software_rasterizer_check = self._check_box("disable-software-rasterizer")
        self.disable_renderer_backgrounding_check = self._check_box("disable-renderer-backgrounding")
        self.process_per_site_check = self._check_box("process-per-site")
        self.single_process_check = self._check_box("single-process")
        for checkbox in (
            self.ignore_certificate_errors_check,
            self.allow_insecure_localhost_check,
            self.new_window_check,
            self.incognito_check,
            self.kiosk_check,
            self.start_maximized_check,
            self.start_fullscreen_check,
            self.guest_check,
            self.headless_check,
            self.disable_gpu_check,
            self.disable_extensions_check,
            self.no_first_run_check,
            self.auto_open_devtools_check,
            self.disable_dev_shm_usage_check,
            self.remote_debugging_pipe_check,
            self.trace_startup_check,
            self.enable_logging_check,
            self.disable_web_security_check,
            self.no_sandbox_check,
            self.disable_background_networking_check,
            self.disable_notifications_check,
            self.mute_audio_check,
            self.disable_popup_blocking_check,
            self.disable_software_rasterizer_check,
            self.disable_renderer_backgrounding_check,
            self.process_per_site_check,
            self.single_process_check,
        ):
            bool_layout.addWidget(checkbox)
        inner_layout.addWidget(bool_group)

        extra_group = QGroupBox("Extra Flags")
        extra_layout = QVBoxLayout(extra_group)
        self.extra_args_input = QPlainTextEdit()
        self.extra_args_input.setPlaceholderText("--force-device-scale-factor=1.25 --ozone-platform-hint=auto")
        self.extra_args_input.textChanged.connect(self.mark_dirty)
        extra_layout.addWidget(self.extra_args_input)
        inner_layout.addWidget(extra_group)
        inner_layout.addStretch(1)

        scroll.setWidget(inner)
        wrapper_layout = QVBoxLayout(container)
        wrapper_layout.addWidget(scroll)
        return container

    def _path_row_button(self, button_text: str, callback) -> dict[str, QWidget]:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        line_edit = self._line_edit()
        button = QPushButton(button_text)
        button.clicked.connect(callback)
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return {"widget": widget, "line_edit": line_edit}

    def _line_edit(self, placeholder: str = "") -> QLineEdit:
        line_edit = QLineEdit()
        if placeholder:
            line_edit.setPlaceholderText(placeholder)
        line_edit.textEdited.connect(self.mark_dirty)
        return line_edit

    def _check_box(self, text: str) -> QCheckBox:
        checkbox = QCheckBox(text)
        checkbox.toggled.connect(self.mark_dirty)
        return checkbox

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) == self.webapps_tab:
            self.refresh_webapps_list()

    def refresh_webapps_list(self, *_args) -> None:
        self.webapps_list.clear()
        for config in collect_existing_webapps():
            item_widget = self._build_webapp_item_widget(config)
            item = QListWidgetItem()
            item.setData(Qt.UserRole, config.desktop_path)
            item.setToolTip(config.desktop_path)
            item.setSizeHint(item_widget.sizeHint())
            self.webapps_list.addItem(item)
            self.webapps_list.setItemWidget(item, item_widget)

        count = self.webapps_list.count()
        label = "webapp" if count == 1 else "webapps"
        self.webapps_count_label.setText(f"{count} {label} found")

    def open_webapp_list_item(self, item: QListWidgetItem) -> None:
        if not self._confirm_discard():
            return
        path = item.data(Qt.UserRole)
        if path and self.open_desktop(Path(path)):
            self.tabs.setCurrentIndex(0)

    def uninstall_webapp(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if not path:
            return

        desktop_path = Path(path)
        if not self._is_user_webapp(desktop_path):
            QMessageBox.information(
                self,
                APP_NAME,
                "Only user-installed web apps can be removed from here.",
            )
            return

        try:
            config = load_desktop_file(desktop_path)
        except Exception:
            config = WebAppConfig(desktop_path=str(desktop_path), desktop_filename=desktop_path.name)

        message = (
            f"Remove '{config.name or config.desktop_filename}'?\n\n"
            f"This will delete:\n"
            f"- {desktop_path}\n"
        )
        icon_path = Path(config.icon_path).expanduser() if config.icon_path.strip() else None
        if icon_path and icon_path.exists() and self._is_managed_icon_path(icon_path):
            message += f"- {icon_path}\n"

        answer = QMessageBox.question(
            self,
            APP_NAME,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        errors: list[str] = []
        try:
            if desktop_path.exists():
                desktop_path.unlink()
        except OSError as exc:
            errors.append(f"Could not remove {desktop_path}: {exc}")

        if icon_path and icon_path.exists() and self._is_managed_icon_path(icon_path):
            try:
                icon_path.unlink()
            except OSError as exc:
                errors.append(f"Could not remove {icon_path}: {exc}")

        refresh_results = run_refresh_commands()
        self.refresh_webapps_list()

        if errors:
            QMessageBox.warning(self, APP_NAME, "\n".join(errors + ["", *refresh_results]))
        else:
            QMessageBox.information(self, APP_NAME, "Web app removed.\n\n" + "\n".join(refresh_results))

    def _build_webapp_item_widget(self, config: WebAppConfig) -> QWidget:
        widget = QWidget()
        widget.setObjectName("WebAppItem")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 10, 12, 14)
        layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        icon = webapp_icon(config.icon_path)
        pixmap = icon.pixmap(48, 48)
        if pixmap.isNull():
            pixmap = app_icon().pixmap(48, 48)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_label = QLabel(config.name or config.desktop_filename)
        title_label.setStyleSheet("font-weight: 600;")
        title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_layout.addWidget(title_label)

        detail_label = QLabel(config.url or config.desktop_path)
        detail_color = detail_label.palette().color(QPalette.WindowText)
        detail_color.setAlpha(180)
        detail_label.setStyleSheet(
            "color: rgba(%d, %d, %d, %d);" % (
                detail_color.red(),
                detail_color.green(),
                detail_color.blue(),
                detail_color.alpha(),
            )
        )
        detail_label.setWordWrap(True)
        detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_layout.addWidget(detail_label)

        layout.addWidget(text_container, stretch=1)

        if self._is_user_webapp(Path(config.desktop_path)):
            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(lambda *_args, p=config.desktop_path: self.open_webapp_by_path(p))
            layout.addWidget(edit_button)

            uninstall_button = QPushButton("Uninstall")
            uninstall_button.clicked.connect(lambda *_args, p=config.desktop_path: self.uninstall_webapp_by_path(p))
            layout.addWidget(uninstall_button)

        return widget

    def _show_webapp_context_menu(self, pos) -> None:
        item = self.webapps_list.itemAt(pos)
        if item is None:
            return

        menu = QMenu(self)
        open_action = menu.addAction("Open")
        desktop_path = Path(str(item.data(Qt.UserRole) or ""))
        uninstall_action = menu.addAction("Uninstall") if self._is_user_webapp(desktop_path) else None
        action = menu.exec(self.webapps_list.mapToGlobal(pos))
        if action == open_action:
            self.open_webapp_list_item(item)
        elif action == uninstall_action:
            self.uninstall_webapp(item)

    def uninstall_webapp_by_path(self, path: str) -> None:
        for index in range(self.webapps_list.count()):
            item = self.webapps_list.item(index)
            if item and item.data(Qt.UserRole) == path:
                self.uninstall_webapp(item)
                return

    def open_webapp_by_path(self, path: str) -> None:
        for index in range(self.webapps_list.count()):
            item = self.webapps_list.item(index)
            if item and item.data(Qt.UserRole) == path:
                self.open_webapp_list_item(item)
                return

    def _is_managed_icon_path(self, path: Path) -> bool:
        try:
            return path.resolve().is_relative_to(ICON_DIR.resolve())
        except AttributeError:
            try:
                path.resolve().relative_to(ICON_DIR.resolve())
                return True
            except ValueError:
                return False
        except OSError:
            return False

    def _is_user_webapp(self, path: Path) -> bool:
        try:
            return path.resolve().is_relative_to(USER_APPLICATIONS_DIR.resolve())
        except AttributeError:
            try:
                path.resolve().relative_to(USER_APPLICATIONS_DIR.resolve())
                return True
            except ValueError:
                return False
        except OSError:
            return False

    def mark_dirty(self, *_args) -> None:
        self._dirty = True
        self._update_target_label()

    def _on_name_changed(self, text: str) -> None:
        self.mark_dirty()
        if self._filename_auto_sync:
            suggested = f"{slugify(text)}.desktop"
            with QSignalBlocker(self.filename_input):
                self.filename_input.setText(suggested)
        self._sync_derived_paths()

    def _on_filename_changed(self, *_args) -> None:
        self._filename_auto_sync = False
        self.mark_dirty()
        self._sync_derived_paths()

    def _sync_derived_paths(self) -> None:
        if not self.user_data_dir_input["line_edit"].text().strip():
            filename = self.filename_input.text().strip() or "webapp.desktop"
            with QSignalBlocker(self.user_data_dir_input["line_edit"]):
                self.user_data_dir_input["line_edit"].setText(default_user_data_dir(filename))
        self._update_target_label()

    def _on_url_edit_finished(self) -> None:
        self.mark_dirty()
        if not self.icon_input.text().strip() and self.url_input.text().strip():
            self.fetch_icon(silent=True)

    def _on_category_selected(self, index: int) -> None:
        if index <= 0:
            return
        updated = append_category_value(self.categories_input.text(), self.categories_select.itemText(index))
        self.categories_input.setText(updated)
        with QSignalBlocker(self.categories_select):
            self.categories_select.setCurrentIndex(0)
        self.mark_dirty()

    def _update_target_label(self) -> None:
        filename = self.filename_input.text().strip() or "webapp.desktop"
        if not filename.endswith(".desktop"):
            filename = f"{filename}.desktop"
        target = USER_APPLICATIONS_DIR / filename
        self.target_path_label.setText(f"Target: {target}")

    def update_icon_preview(self, icon_path: str) -> None:
        path = icon_path.strip()
        if not path:
            self.icon_preview_label.setPixmap(QPixmap())
            self.icon_preview_label.setText("No icon")
            return

        icon = QIcon(path)
        pixmap = icon.pixmap(ICON_PREVIEW_SIZE, ICON_PREVIEW_SIZE)
        if pixmap.isNull():
            pixmap = QPixmap(path)
        if pixmap.isNull():
            self.icon_preview_label.setPixmap(QPixmap())
            self.icon_preview_label.setText("Invalid icon")
            return

        scaled = pixmap.scaled(
            ICON_PREVIEW_SIZE,
            ICON_PREVIEW_SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.icon_preview_label.setText("")
        self.icon_preview_label.setPixmap(scaled)

    def load_config(self, config: WebAppConfig) -> None:
        self.current_config = config
        self._filename_auto_sync = not bool(config.opened_from_existing)
        blockers = [
            QSignalBlocker(self.name_input),
            QSignalBlocker(self.url_input),
            QSignalBlocker(self.comment_input),
            QSignalBlocker(self.categories_select),
            QSignalBlocker(self.categories_input),
            QSignalBlocker(self.filename_input),
            QSignalBlocker(self.chromium_input),
            QSignalBlocker(self.icon_input),
            QSignalBlocker(self.ignore_icon_ssl_errors_check),
            QSignalBlocker(self.user_data_dir_input["line_edit"]),
            QSignalBlocker(self.wm_class_input),
            QSignalBlocker(self.wm_name_input),
            QSignalBlocker(self.app_id_input),
            QSignalBlocker(self.app_launch_url_input),
            QSignalBlocker(self.window_size_input),
            QSignalBlocker(self.window_position_input),
            QSignalBlocker(self.proxy_server_input),
            QSignalBlocker(self.proxy_bypass_input),
            QSignalBlocker(self.user_agent_input),
            QSignalBlocker(self.enable_features_input),
            QSignalBlocker(self.disable_features_input),
            QSignalBlocker(self.lang_input),
            QSignalBlocker(self.profile_directory_input),
            QSignalBlocker(self.remote_debugging_port_input),
            QSignalBlocker(self.vmodule_input),
            QSignalBlocker(self.trace_startup_file_input),
            QSignalBlocker(self.virtual_time_budget_input),
            QSignalBlocker(self.proxy_pac_url_input),
            QSignalBlocker(self.host_resolver_rules_input),
            QSignalBlocker(self.autoplay_policy_input),
            QSignalBlocker(self.use_gl_input),
            QSignalBlocker(self.force_device_scale_factor_input),
            QSignalBlocker(self.ozone_platform_hint_input),
            QSignalBlocker(self.disk_cache_dir_input),
            QSignalBlocker(self.disk_cache_size_input),
            QSignalBlocker(self.extra_args_input),
            QSignalBlocker(self.new_window_check),
            QSignalBlocker(self.incognito_check),
            QSignalBlocker(self.kiosk_check),
            QSignalBlocker(self.start_maximized_check),
            QSignalBlocker(self.start_fullscreen_check),
            QSignalBlocker(self.ignore_certificate_errors_check),
            QSignalBlocker(self.allow_insecure_localhost_check),
            QSignalBlocker(self.guest_check),
            QSignalBlocker(self.headless_check),
            QSignalBlocker(self.disable_gpu_check),
            QSignalBlocker(self.disable_extensions_check),
            QSignalBlocker(self.no_first_run_check),
            QSignalBlocker(self.auto_open_devtools_check),
            QSignalBlocker(self.disable_dev_shm_usage_check),
            QSignalBlocker(self.remote_debugging_pipe_check),
            QSignalBlocker(self.trace_startup_check),
            QSignalBlocker(self.enable_logging_check),
            QSignalBlocker(self.disable_web_security_check),
            QSignalBlocker(self.no_sandbox_check),
            QSignalBlocker(self.disable_background_networking_check),
            QSignalBlocker(self.disable_notifications_check),
            QSignalBlocker(self.mute_audio_check),
            QSignalBlocker(self.disable_popup_blocking_check),
            QSignalBlocker(self.disable_software_rasterizer_check),
            QSignalBlocker(self.disable_renderer_backgrounding_check),
            QSignalBlocker(self.process_per_site_check),
            QSignalBlocker(self.single_process_check),
        ]
        try:
            self.name_input.setText(config.name)
            self.url_input.setText(config.url)
            self.comment_input.setText(config.comment)
            self.categories_select.setCurrentIndex(0)
            self.categories_input.setText(config.categories)
            self.filename_input.setText(config.desktop_filename)
            self.chromium_input.setText(config.chromium_path)
            self.icon_input.setText(config.icon_path)
            self.ignore_icon_ssl_errors_check.setChecked(config.ignore_icon_ssl_errors)
            self.user_data_dir_input["line_edit"].setText(
                config.user_data_dir or default_user_data_dir(config.desktop_filename)
            )
            self.wm_class_input.setText(config.wm_class)
            self.wm_name_input.setText(config.wm_name)
            self.app_id_input.setText(config.app_id)
            self.app_launch_url_input.setText(config.app_launch_url_for_shortcuts_menu_item)
            self.window_size_input.setText(config.window_size)
            self.window_position_input.setText(config.window_position)
            self.proxy_server_input.setText(config.proxy_server)
            self.proxy_bypass_input.setText(config.proxy_bypass_list)
            self.user_agent_input.setText(config.user_agent)
            self.enable_features_input.setText(config.enable_features)
            self.disable_features_input.setText(config.disable_features)
            self.lang_input.setText(config.lang)
            self.profile_directory_input.setText(config.profile_directory)
            self.remote_debugging_port_input.setText(config.remote_debugging_port)
            self.vmodule_input.setText(config.vmodule)
            self.trace_startup_file_input.setText(config.trace_startup_file)
            self.virtual_time_budget_input.setText(config.virtual_time_budget)
            self.proxy_pac_url_input.setText(config.proxy_pac_url)
            self.host_resolver_rules_input.setText(config.host_resolver_rules)
            self.autoplay_policy_input.setText(config.autoplay_policy)
            self.use_gl_input.setText(config.use_gl)
            self.force_device_scale_factor_input.setText(config.force_device_scale_factor)
            self.ozone_platform_hint_input.setText(config.ozone_platform_hint)
            self.disk_cache_dir_input.setText(config.disk_cache_dir)
            self.disk_cache_size_input.setText(config.disk_cache_size)
            self.extra_args_input.setPlainText(config.extra_args)
            self.new_window_check.setChecked(config.new_window)
            self.incognito_check.setChecked(config.incognito)
            self.kiosk_check.setChecked(config.kiosk)
            self.start_maximized_check.setChecked(config.start_maximized)
            self.start_fullscreen_check.setChecked(config.start_fullscreen)
            self.ignore_certificate_errors_check.setChecked(config.ignore_certificate_errors)
            self.allow_insecure_localhost_check.setChecked(config.allow_insecure_localhost)
            self.guest_check.setChecked(config.guest)
            self.headless_check.setChecked(config.headless)
            self.disable_gpu_check.setChecked(config.disable_gpu)
            self.disable_extensions_check.setChecked(config.disable_extensions)
            self.no_first_run_check.setChecked(config.no_first_run)
            self.auto_open_devtools_check.setChecked(config.auto_open_devtools_for_tabs)
            self.disable_dev_shm_usage_check.setChecked(config.disable_dev_shm_usage)
            self.remote_debugging_pipe_check.setChecked(config.remote_debugging_pipe)
            self.trace_startup_check.setChecked(config.trace_startup)
            self.enable_logging_check.setChecked(config.enable_logging)
            self.disable_web_security_check.setChecked(config.disable_web_security)
            self.no_sandbox_check.setChecked(config.no_sandbox)
            self.disable_background_networking_check.setChecked(config.disable_background_networking)
            self.disable_notifications_check.setChecked(config.disable_notifications)
            self.mute_audio_check.setChecked(config.mute_audio)
            self.disable_popup_blocking_check.setChecked(config.disable_popup_blocking)
            self.disable_software_rasterizer_check.setChecked(config.disable_software_rasterizer)
            self.disable_renderer_backgrounding_check.setChecked(config.disable_renderer_backgrounding)
            self.process_per_site_check.setChecked(config.process_per_site)
            self.single_process_check.setChecked(config.single_process)
        finally:
            blockers.clear()
        self._dirty = False
        self._update_target_label()
        self.update_icon_preview(config.icon_path)

    def gather_config(self) -> WebAppConfig:
        filename = self.filename_input.text().strip() or f"{slugify(self.name_input.text())}.desktop"
        if not filename.endswith(".desktop"):
            filename = f"{filename}.desktop"
        desktop_path = str(USER_APPLICATIONS_DIR / filename)
        user_data_dir = self.user_data_dir_input["line_edit"].text().strip() or default_user_data_dir(filename)
        return WebAppConfig(
            name=self.name_input.text().strip(),
            url=self.url_input.text().strip(),
            comment=self.comment_input.text().strip(),
            categories=serialize_categories(parse_categories(self.categories_input.text())),
            icon_path=self.icon_input.text().strip(),
            chromium_path=self.chromium_input.text().strip(),
            desktop_filename=filename,
            desktop_path=desktop_path,
            user_data_dir=user_data_dir,
            wm_class=self.wm_class_input.text().strip(),
            wm_name=self.wm_name_input.text().strip(),
            app_id=self.app_id_input.text().strip(),
            app_launch_url_for_shortcuts_menu_item=self.app_launch_url_input.text().strip(),
            window_size=self.window_size_input.text().strip(),
            window_position=self.window_position_input.text().strip(),
            proxy_server=self.proxy_server_input.text().strip(),
            proxy_bypass_list=self.proxy_bypass_input.text().strip(),
            user_agent=self.user_agent_input.text().strip(),
            enable_features=self.enable_features_input.text().strip(),
            disable_features=self.disable_features_input.text().strip(),
            lang=self.lang_input.text().strip(),
            profile_directory=self.profile_directory_input.text().strip(),
            remote_debugging_port=self.remote_debugging_port_input.text().strip(),
            vmodule=self.vmodule_input.text().strip(),
            trace_startup_file=self.trace_startup_file_input.text().strip(),
            virtual_time_budget=self.virtual_time_budget_input.text().strip(),
            proxy_pac_url=self.proxy_pac_url_input.text().strip(),
            host_resolver_rules=self.host_resolver_rules_input.text().strip(),
            autoplay_policy=self.autoplay_policy_input.text().strip(),
            use_gl=self.use_gl_input.text().strip(),
            force_device_scale_factor=self.force_device_scale_factor_input.text().strip(),
            ozone_platform_hint=self.ozone_platform_hint_input.text().strip(),
            disk_cache_dir=self.disk_cache_dir_input.text().strip(),
            disk_cache_size=self.disk_cache_size_input.text().strip(),
            extra_args=self.extra_args_input.toPlainText().strip(),
            ignore_icon_ssl_errors=self.ignore_icon_ssl_errors_check.isChecked(),
            new_window=self.new_window_check.isChecked(),
            incognito=self.incognito_check.isChecked(),
            kiosk=self.kiosk_check.isChecked(),
            start_maximized=self.start_maximized_check.isChecked(),
            start_fullscreen=self.start_fullscreen_check.isChecked(),
            ignore_certificate_errors=self.ignore_certificate_errors_check.isChecked(),
            allow_insecure_localhost=self.allow_insecure_localhost_check.isChecked(),
            guest=self.guest_check.isChecked(),
            headless=self.headless_check.isChecked(),
            disable_gpu=self.disable_gpu_check.isChecked(),
            disable_extensions=self.disable_extensions_check.isChecked(),
            no_first_run=self.no_first_run_check.isChecked(),
            auto_open_devtools_for_tabs=self.auto_open_devtools_check.isChecked(),
            disable_dev_shm_usage=self.disable_dev_shm_usage_check.isChecked(),
            remote_debugging_pipe=self.remote_debugging_pipe_check.isChecked(),
            trace_startup=self.trace_startup_check.isChecked(),
            enable_logging=self.enable_logging_check.isChecked(),
            disable_web_security=self.disable_web_security_check.isChecked(),
            no_sandbox=self.no_sandbox_check.isChecked(),
            disable_background_networking=self.disable_background_networking_check.isChecked(),
            disable_notifications=self.disable_notifications_check.isChecked(),
            mute_audio=self.mute_audio_check.isChecked(),
            disable_popup_blocking=self.disable_popup_blocking_check.isChecked(),
            disable_software_rasterizer=self.disable_software_rasterizer_check.isChecked(),
            disable_renderer_backgrounding=self.disable_renderer_backgrounding_check.isChecked(),
            process_per_site=self.process_per_site_check.isChecked(),
            single_process=self.single_process_check.isChecked(),
            opened_from_existing=bool(self.current_config.opened_from_existing),
        )

    def new_config(self, *_args) -> None:
        if not self._confirm_discard():
            return
        self.load_config(WebAppConfig(chromium_path=detect_chromium(), desktop_filename="webapp.desktop"))
        self.statusBar().showMessage("Form cleared.")

    def detect_chromium_path(self, *_args) -> None:
        path = detect_chromium()
        if path:
            self.chromium_input.setText(path)
            self.mark_dirty()
            self.statusBar().showMessage(f"Detected Chromium: {path}")
        else:
            QMessageBox.warning(self, APP_NAME, "Could not find Chromium in PATH.")

    def choose_icon_file(self, *_args) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Icon",
            str(Path.home()),
            "Images (*.png *.svg *.ico *.jpg *.jpeg *.webp)",
        )
        if path:
            filename = self.filename_input.text().strip() or f"{slugify(self.name_input.text())}.desktop"
            slug = icon_slug_for_desktop_filename(filename)
            try:
                icon_path = store_icon_file(path, slug)
            except Exception as exc:
                QMessageBox.warning(self, APP_NAME, str(exc))
                return
            self.icon_input.setText(str(icon_path))
            self.mark_dirty()
            self.statusBar().showMessage(f"Icon saved to {icon_path}")

    def choose_user_data_dir(self, *_args) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose user-data-dir", str(Path.home()))
        if path:
            self.user_data_dir_input["line_edit"].setText(path)
            self.mark_dirty()

    def fetch_icon(self, silent: bool = False) -> None:
        url = self.url_input.text().strip()
        if not url:
            if not silent:
                QMessageBox.warning(self, APP_NAME, "Enter a URL before fetching the icon.")
            return
        filename = self.filename_input.text().strip() or f"{slugify(self.name_input.text())}.desktop"
        slug = icon_slug_for_desktop_filename(filename)
        self.statusBar().showMessage("Downloading icon...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            icon_path = fetch_icon_for_url(
                url,
                slug,
                ignore_ssl_errors=self.ignore_icon_ssl_errors_check.isChecked(),
            )
            self.icon_input.setText(str(icon_path))
            self.mark_dirty()
            self.statusBar().showMessage(f"Icon saved to {icon_path}")
        except Exception as exc:
            self.statusBar().showMessage("Could not download the icon.")
            if not silent:
                QMessageBox.warning(self, APP_NAME, str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def open_desktop_dialog(self, *_args) -> None:
        if not self._confirm_discard():
            return
        start_dir = str(USER_APPLICATIONS_DIR if USER_APPLICATIONS_DIR.exists() else Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Open .desktop", start_dir, "Desktop files (*.desktop)")
        if path:
            self.open_desktop(Path(path))

    def open_desktop(self, path: Path) -> bool:
        try:
            config = load_desktop_file(path)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return False
        self.load_config(config)
        self.statusBar().showMessage(f"Loaded: {path}")
        return True

    def open_desktop_folder(self, *_args) -> None:
        filename = self.filename_input.text().strip() or "webapp.desktop"
        if not filename.endswith(".desktop"):
            filename = f"{filename}.desktop"
        target = USER_APPLICATIONS_DIR / filename
        try:
            reveal_in_file_manager(target)
            self.statusBar().showMessage(f"Opened folder: {target.parent}")
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))

    def save_desktop(self, *_args) -> None:
        config = self.gather_config()
        if not config.name:
            QMessageBox.warning(self, APP_NAME, "The title is required.")
            return
        if not config.chromium_path:
            QMessageBox.warning(self, APP_NAME, "Configure the Chromium executable.")
            return
        if not resolve_executable(config.chromium_path):
            QMessageBox.warning(self, APP_NAME, "The Chromium executable does not exist.")
            return
        if not config.icon_path:
            self.fetch_icon(silent=True)
            config = self.gather_config()
        elif Path(config.icon_path).expanduser().parent != ICON_DIR:
            slug = icon_slug_for_desktop_filename(config.desktop_filename)
            try:
                icon_path = store_icon_file(config.icon_path, slug)
            except Exception as exc:
                QMessageBox.warning(self, APP_NAME, str(exc))
                return
            self.icon_input.setText(str(icon_path))
            config.icon_path = str(icon_path)

        try:
            entry = config.to_desktop_entry()
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return

        USER_APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
        target = USER_APPLICATIONS_DIR / config.desktop_filename
        try:
            target.write_text(entry, encoding="utf-8")
            os.chmod(target, 0o755)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not save {target}.\n{exc}")
            return

        refresh_results = run_refresh_commands()
        self.current_config = config
        self.current_config.opened_from_existing = True
        self._dirty = False
        self._update_target_label()
        QMessageBox.information(
            self,
            APP_NAME,
            "File saved successfully.\n\n" + "\n".join(refresh_results),
        )
        self.refresh_webapps_list()
        self.statusBar().showMessage(f"Saved: {target}")

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self,
            APP_NAME,
            "There are unsaved changes. Do you want to discard them?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()


def main() -> int:
    QApplication.setApplicationName(APP_NAME)
    QApplication.setDesktopFileName(APP_ID)
    app = QApplication(sys.argv)
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = MainWindow()

    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1]).expanduser()
        if candidate.exists():
            window.open_desktop(candidate)

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
