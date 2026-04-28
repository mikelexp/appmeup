PYTHON := .venv/bin/python
SCRIPTS := scripts

.PHONY: help run install-deps build-standalone build-onefile clean clean-build install

help:
	@echo "Targets:"
	@echo "  run              Run the app"
	@echo "  install-deps     Create venv and install dependencies"
	@echo "  build-standalone Build standalone binary"
	@echo "  build-onefile    Build onefile binary"
	@echo "  clean            Remove venv, build, and dist"
	@echo "  clean-build      Remove build artifacts only"
	@echo "  install          Install the built app system-wide"

run: $(PYTHON)
	$(PYTHON) appmeup.py

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

$(PYTHON):
	$(MAKE) install-deps
