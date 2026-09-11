PYTHON := .venv/bin/python
SCRIPTS := scripts

.PHONY: help run install-deps build-standalone build-onefile clean clean-build install uninstall version set-version

help:
	@echo "Targets:"
	@echo "  run              Run the app"
	@echo "  install-deps     Create venv and install dependencies"
	@echo "  build-standalone Build standalone binary"
	@echo "  build-onefile    Build onefile binary"
	@echo "  version          Print the current app version"
	@echo "  set-version      Set APP_VERSION in src/constants.py (use VERSION=...)"
	@echo "  clean            Remove venv, build, and dist"
	@echo "  clean-build      Remove build artifacts only"
	@echo "  install          Install the built app system-wide"
	@echo "  uninstall        Remove the installed app"
	@echo "  uninstall-purge  Remove app + all data (settings, icons, profiles)"
	@echo "  aur-update       Build and push AUR package for current version"

run: $(PYTHON)
	bash $(SCRIPTS)/run.sh

install-deps:
	@bash $(SCRIPTS)/install-build-deps.sh

build-standalone: $(PYTHON)
	@bash $(SCRIPTS)/build-standalone.sh

build-onefile: $(PYTHON)
	@bash $(SCRIPTS)/build-onefile.sh

clean:
	rm -rf .venv build dist

clean-build:
	@bash $(SCRIPTS)/clean-build.sh

install:
	@bash $(SCRIPTS)/install.sh

uninstall:
	@bash $(SCRIPTS)/uninstall.sh

uninstall-purge:
	@bash $(SCRIPTS)/uninstall.sh --purge

aur-update:
	@bash $(SCRIPTS)/aur-update.sh

version:
	@python3 -c "import sys; sys.path.insert(0, '.'); from src.constants import APP_VERSION; print(APP_VERSION)"

set-version:
	@test -n "$(VERSION)" || (echo "Usage: make set-version VERSION=x.y.z"; exit 1)
	@python3 -c 'from pathlib import Path; import re, sys; version = sys.argv[1]; path = Path("src/constants.py"); text = path.read_text(); text, count = re.subn(r"^APP_VERSION = \".*\"$$", f"APP_VERSION = \"{version}\"", text, flags=re.M); path.write_text(text) if count else (_ for _ in ()).throw(SystemExit("src/constants.py pattern not found")); path = Path("PKGBUILD"); text = path.read_text(); text, count = re.subn(r"^pkgver=.*$$", f"pkgver={version}", text, flags=re.M); path.write_text(text) if count else (_ for _ in ()).throw(SystemExit("PKGBUILD pkgver pattern not found")); text = path.read_text(); text, count = re.subn(r"^pkgrel=.*$$", "pkgrel=1", text, flags=re.M); path.write_text(text) if count else (_ for _ in ()).throw(SystemExit("PKGBUILD pkgrel pattern not found")); print(f"Set version to {version} in src/constants.py and PKGBUILD")' "$(VERSION)"

$(PYTHON):
	$(MAKE) install-deps
