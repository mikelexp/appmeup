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
- A new release requires a new version tag; use `make set-version` rather than reusing an existing tag.
- The GitHub workflow builds portable Nuitka binaries for non-distro installs.
- The Arch AUR package is a source package using `python-pyside6`, so it inherits each user's system Qt/Plasma theme instead of bundling Qt.
- `make aur-update` validates the source package with `makepkg -s` and regenerates `.SRCINFO`. AUR publishing requires the configured SSH key; AUR maintenance can temporarily make both clone and push unavailable.

## Constraints
- No test framework, no linter, no typechecker configured
- CI only builds — no automated verification
- Linux-only (Linux desktop app, XDG paths, Chromium browser integration)
- Qt should follow the system theme. Configure the platform before creating `QApplication`; preserve user-set `QT_STYLE_OVERRIDE`, `QT_QPA_PLATFORMTHEME`, and `QT_PLUGIN_PATH` values. Never set `QT_STYLE_OVERRIDE` or inject plugins from another Qt installation. On Plasma, request `QT_QPA_PLATFORMTHEME=kde` only when the running Qt provides the KDE platform plugin; otherwise use Qt's safe default.
- The Arch package must use the system `python-pyside6` runtime. Do not use the Nuitka binary for the Arch package, because its bundled Qt cannot safely load arbitrary user/system Qt styles.
- `just run` and `make run` prefer `/usr/bin/python` when system PySide6 and pyxdg are available, so local runs use the system Qt/Plasma theme; the virtualenv remains for portable Nuitka builds.
- A message listing `xcb` under "Available platform plugins" only proves discovery, not initialization. For failures, run `QT_DEBUG_PLUGINS=1 appmeup --verbose` and inspect the bundled `libqxcb.so` with `ldd`/`lddtree`.
- The Arch `PKGBUILD` must depend on `python`, `python-pyside6`, and `python-pyxdg`; `python-pyside6` supplies the matching Qt runtime and desktop plugins.
- Icon fetch uses GitHub releases API for update checks
- `is_aur_install()` heuristic: binary in `/usr/bin` or `/usr/local/bin` → skips built-in updater

## Qt verification
```sh
.venv/bin/python -m compileall -q appmeup.py src
QT_QPA_PLATFORM=offscreen .venv/bin/python -c 'from PySide6.QtWidgets import QApplication; app=QApplication([]); print(app.style().objectName())'
makepkg --printsrcinfo
```
