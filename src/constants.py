from __future__ import annotations

from pathlib import Path

from xdg.BaseDirectory import xdg_data_dirs


APP_ID = "mikelexp.appmeup"
APP_NAME = "AppMeUp!"
APP_VERSION = "1.1"
APP_DESCRIPTION = "A desktop app for creating and editing Chrome/Chromium-based web apps in Linux."
USER_APPLICATIONS_DIR = Path.home() / ".local/share/applications"
DESKTOP_APPLICATION_DIRS = [Path(directory) / "applications" for directory in xdg_data_dirs]
ICON_DIR = Path.home() / ".local/share/icons/appmeup"
ICON_THEME_DIR = Path.home() / ".local/share/icons/hicolor"
PROFILE_DIR = Path.home() / ".local/share/appmeup/profiles"
DEFAULT_CATEGORIES = ""
WEBAPP_MARKER_KEY = "X-AppMeUp-WebApp"
WEBAPP_VERSION_KEY = "X-AppMeUp-Version"
ICON_SSL_IGNORE_KEY = "X-AppMeUp-IgnoreIconSSLErrors"
ICON_PREVIEW_SIZE = 64

BROWSER_NAME_FROM_BINARY: dict[str, str] = {
    "google-chrome-stable": "Google Chrome (Stable)",
    "google-chrome": "Google Chrome",
    "chrome": "Chrome",
    "chromium-browser": "Chromium (Browser)",
    "chromium": "Chromium",
    "brave-browser": "Brave (Browser)",
    "brave": "Brave",
    "vivaldi-stable": "Vivaldi Stable",
    "vivaldi": "Vivaldi",
}

BROWSER_FLAG_HIDDEN: dict[str, set[str]] = {
    "Google Chrome": set(),
    "Google Chrome (Stable)": set(),
    "Chrome": set(),
    "Chromium": set(),
    "Chromium (Browser)": set(),
    "Brave": {"window-size", "window-position", "app-id", "app-launch-url-for-shortcuts-menu-item", "guest"},
    "Brave (Browser)": {"window-size", "window-position", "app-id", "app-launch-url-for-shortcuts-menu-item", "guest"},
    "Vivaldi": {"window-size", "window-position", "app-id", "app-launch-url-for-shortcuts-menu-item", "guest"},
    "Vivaldi Stable": {"window-size", "window-position", "app-id", "app-launch-url-for-shortcuts-menu-item", "guest"},
}

CHROMIUM_SWITCH_TOOLTIPS: dict[str, str] = {
    "app-id": "Fixed app identifier.",
    "app-launch-url-for-shortcuts-menu-item": "URL used when opening shortcuts.",
    "class": "Window class for the system.",
    "guest": "Opens in a temporary guest profile.",
    "incognito": "Starts in incognito mode.",
    "kiosk": "Launches in kiosk mode.",
    "name": "Window or app name.",
    "new-window": "Forces a new window.",
    "no-first-run": "Skips the first-run flow.",
    "start-fullscreen": "Opens in fullscreen.",
    "start-maximized": "Opens maximized.",
    "window-position": "Initial X,Y position.",
    "window-size": "Initial width,height size.",
    "disable-features": "Turns off specific features.",
    "enable-features": "Turns on specific features.",
    "lang": "Interface language.",
    "profile-directory": "Uses a specific profile.",
    "user-data-dir": "User data directory.",
    "user-agent": "Overrides the user agent.",
    "autoplay-policy": "Controls media autoplay behavior.",
    "disable-dev-shm-usage": "Avoids shared /dev/shm usage.",
    "disable-extensions": "Disables loaded extensions.",
    "disable-gpu": "Disables GPU acceleration.",
    "disable-renderer-backgrounding": "Keeps background tabs active.",
    "disable-software-rasterizer": "Avoids software rasterization.",
    "disk-cache-dir": "Disk cache folder.",
    "disk-cache-size": "Maximum cache size.",
    "force-device-scale-factor": "Forces the UI scale.",
    "headless": "Runs without a visible UI.",
    "mute-audio": "Mutes all audio.",
    "ozone-platform-hint": "Hints the graphics platform.",
    "process-per-site": "Uses one process per site.",
    "single-process": "Runs everything in one process.",
    "use-gl": "Chooses the GL implementation.",
    "virtual-time-budget": "Virtual time for automation.",
    "allow-insecure-localhost": "Allows insecure local HTTPS.",
    "disable-background-networking": "Reduces background network traffic.",
    "disable-notifications": "Blocks web notifications.",
    "disable-popup-blocking": "Allows pop-ups.",
    "disable-web-security": "Disables same-origin restrictions.",
    "host-resolver-rules": "Rules for resolving hosts.",
    "ignore-certificate-errors": "Ignores TLS or SSL errors.",
    "no-sandbox": "Disables the sandbox.",
    "proxy-bypass-list": "Hosts that bypass the proxy.",
    "proxy-pac-url": "PAC file URL.",
    "proxy-server": "Manual proxy for traffic.",
    "auto-open-devtools-for-tabs": "Opens DevTools for each tab.",
    "enable-logging": "Enables diagnostic logging.",
    "remote-debugging-port": "Port for remote DevTools.",
    "remote-debugging-pipe": "Uses a pipe for debugging.",
    "trace-startup": "Records a startup trace.",
    "trace-startup-file": "File to save the trace.",
    "vmodule": "Verbose logging by module.",
}
