#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Prefer the distro Qt stack so Plasma can provide the user's configured style.
if /usr/bin/python -c 'import PySide6, xdg' >/dev/null 2>&1; then
    exec /usr/bin/python "${ROOT_DIR}/appmeup.py" "$@"
fi

exec "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/appmeup.py" "$@"
