#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  python3 -m venv "${ROOT_DIR}/.venv"
fi

"${ROOT_DIR}/.venv/bin/pip" install -r "${ROOT_DIR}/requirements.txt"
"${ROOT_DIR}/.venv/bin/pip" install -r "${ROOT_DIR}/requirements-build.txt"

echo "Build dependencies installed into ${ROOT_DIR}/.venv"
