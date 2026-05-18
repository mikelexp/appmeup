#!/usr/bin/env bash
set -euo pipefail

APP_ID="mikelexp.appmeup"
APP_BIN_NAME="appmeup"

INSTALL_BIN="${HOME}/.local/bin"
INSTALL_LIB="${HOME}/.local/lib/${APP_ID}"
INSTALL_APPS="${HOME}/.local/share/applications"
INSTALL_ICONS="${HOME}/.local/share/icons/hicolor/512x512/apps"

echo "Uninstalling AppMeUp!..."

rm -f "${INSTALL_BIN}/${APP_BIN_NAME}"
rm -f "${INSTALL_APPS}/${APP_ID}.desktop"
rm -f "${INSTALL_ICONS}/${APP_ID}.png"
rm -rf "${INSTALL_LIB}"

# Refresh caches
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "${INSTALL_APPS}"
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor"
fi
if command -v xdg-desktop-menu &>/dev/null; then
    xdg-desktop-menu forceupdate
fi

echo "Done."
