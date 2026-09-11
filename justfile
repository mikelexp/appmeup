python := '.venv/bin/python'
scripts := 'scripts'

default:
    @just --list

version:
    python3 -c "import sys; sys.path.insert(0, '.'); from src.constants import APP_VERSION; print(APP_VERSION)"

set-version VERSION:
    @python3 -c 'from pathlib import Path; import re, sys; version = sys.argv[1]; path = Path("src/constants.py"); text = path.read_text(); text, count = re.subn(r"^APP_VERSION = \".*\"$", f"APP_VERSION = \"{version}\"", text, flags=re.M); path.write_text(text) if count else (_ for _ in ()).throw(SystemExit("src/constants.py pattern not found")); path = Path("PKGBUILD"); text = path.read_text(); text, count = re.subn(r"^pkgver=.*$", f"pkgver={version}", text, flags=re.M); path.write_text(text) if count else (_ for _ in ()).throw(SystemExit("PKGBUILD pkgver pattern not found")); text = path.read_text(); text, count = re.subn(r"^pkgrel=.*$", "pkgrel=1", text, flags=re.M); path.write_text(text) if count else (_ for _ in ()).throw(SystemExit("PKGBUILD pkgrel pattern not found")); print(f"Set version to {version} in src/constants.py and PKGBUILD")' "{{VERSION}}"

run: _ensure-python
    bash {{scripts}}/run.sh

install-deps:
    bash {{scripts}}/install-build-deps.sh

build-standalone: _ensure-python
    bash {{scripts}}/build-standalone.sh

build-onefile: _ensure-python
    bash {{scripts}}/build-onefile.sh

clean:
    rm -rf .venv build dist

clean-build:
    bash {{scripts}}/clean-build.sh

install:
    bash {{scripts}}/install.sh

uninstall:
    bash {{scripts}}/uninstall.sh

uninstall-purge:
    bash {{scripts}}/uninstall.sh --purge

aur-update:
    bash {{scripts}}/aur-update.sh

_ensure-python:
    @if [ ! -f '{{python}}' ]; then just install-deps; fi
