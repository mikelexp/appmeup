#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="/usr/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "System Python was not found at ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]] || ! "${ROOT_DIR}/.venv/bin/python" -c 'import pathlib, PySide6, xdg; assert str(pathlib.Path(PySide6.__file__).resolve()).startswith("/usr/")' >/dev/null 2>&1; then
  rm -rf "${ROOT_DIR}/.venv"
  "${PYTHON_BIN}" -m venv --system-site-packages "${ROOT_DIR}/.venv"
fi

if ! "${ROOT_DIR}/.venv/bin/python" -c 'import pathlib, PySide6, xdg; assert str(pathlib.Path(PySide6.__file__).resolve()).startswith("/usr/")' >/dev/null 2>&1; then
  echo "System PySide6 and pyxdg are required; install them with the distribution package manager." >&2
  exit 1
fi

"${ROOT_DIR}/.venv/bin/pip" install -r "${ROOT_DIR}/requirements-build.txt"

echo "Build dependencies installed into ${ROOT_DIR}/.venv"
