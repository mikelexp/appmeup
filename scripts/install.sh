#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"

APP_ID="mikelexp.appmeup"
APP_BIN_NAME="appmeup"

INSTALL_BIN="${HOME}/.local/bin"
INSTALL_LIB="${HOME}/.local/lib/${APP_ID}"
INSTALL_APPS="${HOME}/.local/share/applications"
INSTALL_ICONS="${HOME}/.local/share/icons/hicolor/512x512/apps"

STANDALONE_DIR="${DIST_DIR}/appmeup.dist"
STANDALONE_BIN="${STANDALONE_DIR}/appmeup.bin"
ONEFILE_BIN="${DIST_DIR}/appmeup.bin"

# Detect build type
if [[ -d "${STANDALONE_DIR}" && -f "${STANDALONE_BIN}" ]]; then
    MODE="standalone"
elif [[ -f "${ONEFILE_BIN}" ]]; then
    MODE="onefile"
else
    echo "Error: no build found in ${DIST_DIR}." >&2
    echo "Run scripts/build-standalone.sh or scripts/build-onefile.sh first." >&2
    exit 1
fi

echo "Installing App Me Up (${MODE})..."

mkdir -p "${INSTALL_BIN}" "${INSTALL_APPS}" "${INSTALL_ICONS}"

if [[ "${MODE}" == "standalone" ]]; then
    rm -rf "${INSTALL_LIB}"
    cp -r "${STANDALONE_DIR}" "${INSTALL_LIB}"
    chmod +x "${INSTALL_LIB}/appmeup.bin"
    ln -sf "${INSTALL_LIB}/appmeup.bin" "${INSTALL_BIN}/${APP_BIN_NAME}"
else
    install -m 755 "${ONEFILE_BIN}" "${INSTALL_BIN}/${APP_BIN_NAME}"
fi

install -m 644 "${ROOT_DIR}/icon.png" "${INSTALL_ICONS}/${APP_ID}.png"

# Write .desktop entry for the app itself
cat > "${INSTALL_APPS}/${APP_ID}.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=App Me Up
Comment=Create and edit Chromium web apps from .desktop files
Exec=${INSTALL_BIN}/${APP_BIN_NAME}
Icon=${APP_ID}
Categories=Network;WebBrowser;Utility;
Terminal=false
StartupNotify=true
EOF

chmod 644 "${INSTALL_APPS}/${APP_ID}.desktop"

# Refresh desktop databases
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "${INSTALL_APPS}"
fi
if command -v xdg-desktop-menu &>/dev/null; then
    xdg-desktop-menu forceupdate
fi

echo "Done."
echo "  Binary : ${INSTALL_BIN}/${APP_BIN_NAME}"
echo "  Desktop: ${INSTALL_APPS}/${APP_ID}.desktop"
echo "  Icon   : ${INSTALL_ICONS}/${APP_ID}.png"
