# AppMeUp! — Agent Guide

## Stack
- **Python 3.13**, PySide6 (Qt for Python), pyxdg
- Entrypoint: `appmeup.py` → `src/` package (flat, no sub-packages beyond `src/ui/`)
- Build: **Nuitka** via `build_nuitka.py` (standalone or `--onefile`)

## Commands
```sh
make version            # prints APP_VERSION
make set-version VERSION=x.y.z  # updates src/constants.py and PKGBUILD
make install-deps        # creates .venv, installs requirements.txt + requirements-build.txt
make run                 # runs via .venv/bin/python
make build-standalone    # Nuitka standalone binary -> dist/appmeup.dist/
make build-onefile       # Nuitka single binary -> dist/appmeup.bin
make install             # copies built binary to ~/.local/bin/ + .desktop + icon
make uninstall           # reverses install
make uninstall-purge     # also removes ~/.local/state/appmeup, icons, profiles
make clean               # rm -rf .venv build dist
```
`just` is also available as an alternative (`just version`, `just set-version x.y.z`, same build/install targets).

## Key struct
- **Version:** `src/constants.py:APP_VERSION` — single source of truth
- **Settings:** `~/.local/state/appmeup/settings.json` → window geometry, last browser
- **Logs:** `~/.local/state/appmeup/appmeup.log`; pass `--verbose` for stderr output
- **Desktop files:** saved to `~/.local/share/applications/`, icons to `~/.local/share/icons/appmeup/`
- **WebAppConfig dataclass** (`src/config.py`) — central model; serialized to/from `.desktop` files

## Release flow
1. Run `make set-version VERSION=x.y.z` (or `just set-version x.y.z`) to update `src/constants.py` and `PKGBUILD`
2. `git commit -am "bump to vX.Y" && git tag vX.Y && git push github main vX.Y`
3. GitHub Actions (`.github/workflows/release.yml`) builds onefile binary and creates Release
4. `make aur-update` (or `just aur-update`) pushes to AUR manually after Release is live

Release notes:
- A new binary release requires a new version tag; use `make set-version` rather than reusing an existing tag.
- The GitHub workflow builds the release tarball on Ubuntu; validate the resulting binary against Arch runtime libraries before publishing AUR changes.
- `make aur-update` validates the official tarball with `makepkg -s` and regenerates `.SRCINFO`. AUR publishing requires the configured SSH key; AUR maintenance can temporarily make both clone and push unavailable.

## Constraints
- No test framework, no linter, no typechecker configured
- CI only builds — no automated verification
- Linux-only (Linux desktop app, XDG paths, Chromium browser integration)
- Qt should follow the system theme. Configure the platform before creating `QApplication`; preserve user-set `QT_STYLE_OVERRIDE`, `QT_QPA_PLATFORMTHEME`, and `QT_PLUGIN_PATH` values. When the system KDE platform plugin is available, use it for Plasma integration without overriding the user's widget style. In XFCE, select GTK3 only when `platformthemes/libqgtk3.so` is actually available; otherwise use Qt's default style instead of forcing a missing plugin.
- Keep the bundled PySide6/Nuitka plugin directory first in `QT_PLUGIN_PATH`. Do not prepend the full system Qt plugin tree, since incompatible system XCB, Wayland, or style plugins can break startup.
- A message listing `xcb` under "Available platform plugins" only proves discovery, not initialization. For failures, run `QT_DEBUG_PLUGINS=1 appmeup --verbose` and inspect the bundled `libqxcb.so` with `ldd`/`lddtree`.
- The Arch `PKGBUILD` must declare external X11/XCB runtime dependencies so `yay -S appmeup-bin` needs no manual dependency installation: `libxcb`, `libxkbcommon-x11`, `xcb-util-cursor`, `xcb-util-image`, `xcb-util-keysyms`, `xcb-util-renderutil`, and `xcb-util-wm`. Do not add the full `qt6-base` package when Qt is bundled by Nuitka.
- Icon fetch uses GitHub releases API for update checks
- `is_aur_install()` heuristic: binary in `/usr/bin` or `/usr/local/bin` → skips built-in updater

## Qt verification
```sh
.venv/bin/python -m compileall -q appmeup.py src
QT_QPA_PLATFORM=offscreen .venv/bin/python -c 'from PySide6.QtWidgets import QApplication; app=QApplication([]); print(app.style().objectName())'
makepkg --printsrcinfo
```
