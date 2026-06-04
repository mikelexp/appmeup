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

## Constraints
- No test framework, no linter, no typechecker configured
- CI only builds — no automated verification
- Linux-only (Linux desktop app, XDG paths, Chromium browser integration)
- Qt should follow the system theme. Do not force Breeze or another custom style; avoid hardcoded widget styles unless they are strictly necessary. The app may set `QT_QPA_PLATFORMTHEME=gtk3` at startup when no theme override is present so Qt inherits the desktop theme instead of falling back to `Fusion`.
- Icon fetch uses GitHub releases API for update checks
- `is_aur_install()` heuristic: binary in `/usr/bin` or `/usr/local/bin` → skips built-in updater
