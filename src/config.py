from __future__ import annotations

import configparser
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from src.constants import (
    DEFAULT_CATEGORIES,
    DESKTOP_APPLICATION_DIRS,
    ICON_SSL_IGNORE_KEY,
    USER_APPLICATIONS_DIR,
    WEBAPP_MARKER_KEY,
    WEBAPP_VERSION_KEY,
)
from src.utils import default_user_data_dir, is_probable_webapp, parse_bool, slugify
from src.browser import detect_chromium, resolve_executable
from src.categories import parse_categories, serialize_categories

FLAG_DEFINITIONS: list[dict] = [
    {"attr": "user_data_dir", "flag": "--user-data-dir=", "type": "value"},
    {"attr": "wm_class", "flag": "--class=", "type": "value", "derive": "effective_wm_class"},
    {"attr": "wm_name", "flag": "--name=", "type": "value"},
    {"attr": "url", "flag": "--app=", "type": "value"},
    {"attr": "app_id", "flag": "--app-id=", "type": "value"},
    {"attr": "app_launch_url_for_shortcuts_menu_item", "flag": "--app-launch-url-for-shortcuts-menu-item=", "type": "value"},
    {"attr": "window_size", "flag": "--window-size=", "type": "value"},
    {"attr": "window_position", "flag": "--window-position=", "type": "value"},
    {"attr": "proxy_server", "flag": "--proxy-server=", "type": "value"},
    {"attr": "proxy_bypass_list", "flag": "--proxy-bypass-list=", "type": "value"},
    {"attr": "user_agent", "flag": "--user-agent=", "type": "value"},
    {"attr": "enable_features", "flag": "--enable-features=", "type": "value"},
    {"attr": "disable_features", "flag": "--disable-features=", "type": "value"},
    {"attr": "lang", "flag": "--lang=", "type": "value"},
    {"attr": "profile_directory", "flag": "--profile-directory=", "type": "value"},
    {"attr": "remote_debugging_port", "flag": "--remote-debugging-port=", "type": "value"},
    {"attr": "vmodule", "flag": "--vmodule=", "type": "value"},
    {"attr": "trace_startup_file", "flag": "--trace-startup-file=", "type": "value"},
    {"attr": "virtual_time_budget", "flag": "--virtual-time-budget=", "type": "value"},
    {"attr": "proxy_pac_url", "flag": "--proxy-pac-url=", "type": "value"},
    {"attr": "host_resolver_rules", "flag": "--host-resolver-rules=", "type": "value"},
    {"attr": "autoplay_policy", "flag": "--autoplay-policy=", "type": "value"},
    {"attr": "use_gl", "flag": "--use-gl=", "type": "value"},
    {"attr": "force_device_scale_factor", "flag": "--force-device-scale-factor=", "type": "value"},
    {"attr": "ozone_platform_hint", "flag": "--ozone-platform-hint=", "type": "value"},
    {"attr": "disk_cache_dir", "flag": "--disk-cache-dir=", "type": "value"},
    {"attr": "disk_cache_size", "flag": "--disk-cache-size=", "type": "value"},
    {"attr": "ignore_certificate_errors", "flag": "--ignore-certificate-errors", "type": "bool"},
    {"attr": "allow_insecure_localhost", "flag": "--allow-insecure-localhost", "type": "bool"},
    {"attr": "new_window", "flag": "--new-window", "type": "bool"},
    {"attr": "incognito", "flag": "--incognito", "type": "bool"},
    {"attr": "kiosk", "flag": "--kiosk", "type": "bool"},
    {"attr": "start_maximized", "flag": "--start-maximized", "type": "bool"},
    {"attr": "start_fullscreen", "flag": "--start-fullscreen", "type": "bool"},
    {"attr": "guest", "flag": "--guest", "type": "bool"},
    {"attr": "headless", "flag": "--headless", "type": "bool"},
    {"attr": "disable_gpu", "flag": "--disable-gpu", "type": "bool"},
    {"attr": "disable_extensions", "flag": "--disable-extensions", "type": "bool"},
    {"attr": "no_first_run", "flag": "--no-first-run", "type": "bool"},
    {"attr": "auto_open_devtools_for_tabs", "flag": "--auto-open-devtools-for-tabs", "type": "bool"},
    {"attr": "disable_dev_shm_usage", "flag": "--disable-dev-shm-usage", "type": "bool"},
    {"attr": "remote_debugging_pipe", "flag": "--remote-debugging-pipe", "type": "bool"},
    {"attr": "trace_startup", "flag": "--trace-startup", "type": "bool"},
    {"attr": "enable_logging", "flag": "--enable-logging", "type": "bool"},
    {"attr": "disable_web_security", "flag": "--disable-web-security", "type": "bool"},
    {"attr": "no_sandbox", "flag": "--no-sandbox", "type": "bool"},
    {"attr": "disable_background_networking", "flag": "--disable-background-networking", "type": "bool"},
    {"attr": "disable_notifications", "flag": "--disable-notifications", "type": "bool"},
    {"attr": "mute_audio", "flag": "--mute-audio", "type": "bool"},
    {"attr": "disable_popup_blocking", "flag": "--disable-popup-blocking", "type": "bool"},
    {"attr": "disable_software_rasterizer", "flag": "--disable-software-rasterizer", "type": "bool"},
    {"attr": "disable_renderer_backgrounding", "flag": "--disable-renderer-backgrounding", "type": "bool"},
    {"attr": "process_per_site", "flag": "--process-per-site", "type": "bool"},
    {"attr": "single_process", "flag": "--single-process", "type": "bool"},
]

_VALUE_FLAGS = {d["flag"]: d["attr"] for d in FLAG_DEFINITIONS if d["type"] == "value"}
_BOOL_FLAGS = {d["flag"]: d["attr"] for d in FLAG_DEFINITIONS if d["type"] == "bool"}
_ATTR_TO_FLAG = {d["attr"]: d for d in FLAG_DEFINITIONS}


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
            raise ValueError("No Chrome/Chromium executable is configured.")
        if not self.url.strip():
            raise ValueError("The URL is required.")

        wm_class = self.effective_wm_class()
        tokens = [resolved_chromium, f"--app={self.url.strip()}"]
        for definition in FLAG_DEFINITIONS:
            attr = definition["attr"]
            flag = definition["flag"]
            if definition.get("derive"):
                value = getattr(self, definition["derive"])()
            else:
                value = getattr(self, attr)
            if isinstance(value, str):
                value = value.strip()
                if value:
                    if "=" in flag:
                        tokens.append(f"{flag}{value}")
                    else:
                        tokens.append(flag)
            elif value:
                tokens.append(flag)

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
        exec_line = shlex.join(self.build_exec_tokens())

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

    for token in tokens[1:]:
        matched = False
        for prefix, attr in _VALUE_FLAGS.items():
            if token.startswith(prefix):
                options[attr] = token[len(prefix):]
                matched = True
                break
        if matched:
            continue
        if token in _BOOL_FLAGS:
            options[_BOOL_FLAGS[token]] = True
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

    data: dict = {
        "name": entry.get("Name", ""),
        "comment": entry.get("Comment", ""),
        "categories": entry.get("Categories", DEFAULT_CATEGORIES),
        "icon_path": entry.get("Icon", ""),
        "chromium_path": tokens[0] if tokens else detect_chromium(),
        "desktop_filename": path.name,
        "desktop_path": str(path),
        "extra_args": shlex.join(extra),
        "ignore_icon_ssl_errors": parse_bool(entry.get(ICON_SSL_IGNORE_KEY), default=False),
        "opened_from_existing": True,
    }

    for definition in FLAG_DEFINITIONS:
        attr = definition["attr"]
        if definition.get("derive") and attr != "wm_class":
            continue
        raw = options.get(attr, "")
        if definition["type"] == "bool":
            data[attr] = bool(raw)
        else:
            data[attr] = str(raw)

    return WebAppConfig(**data)


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
