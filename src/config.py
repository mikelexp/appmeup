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
from src.utils import default_user_data_dir, is_probable_webapp, parse_bool, shell_join, slugify
from src.browser import detect_chromium, resolve_executable
from src.categories import parse_categories, serialize_categories


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
                options[key] = token[len(prefix):]
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
