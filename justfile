python := '.venv/bin/python'
scripts := 'scripts'

default:
    @just --list

run: _ensure-python
    {{python}} appmeup.py

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

_ensure-python:
    @if [ ! -f '{{python}}' ]; then just install-deps; fi
