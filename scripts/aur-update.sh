#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

APP_VERSION="$(python3 -c "import sys; sys.path.insert(0, '${ROOT_DIR}'); from src.constants import APP_VERSION; print(APP_VERSION)")"
REPO_NAME="appmeup"
AUR_SSH="ssh://aur@aur.archlinux.org/${REPO_NAME}.git"
WORK_DIR="$(mktemp -d /tmp/aur-update-XXXXX)"

echo "=== Updating AUR package ${REPO_NAME} to version ${APP_VERSION} ==="

cd "${ROOT_DIR}"
SOURCE_ARCHIVE="appmeup-${APP_VERSION}.tar.gz"
curl --fail --location --output "${SOURCE_ARCHIVE}" \
    "https://github.com/mikelexp/appmeup/archive/refs/tags/v${APP_VERSION}.tar.gz"
HASH="$(sha256sum "${SOURCE_ARCHIVE}" | cut -d' ' -f1)"
echo "SHA256: ${HASH}"

echo "Cloning AUR repo..."
git clone "${AUR_SSH}" "${WORK_DIR}"

cp "${ROOT_DIR}/PKGBUILD" "${WORK_DIR}/"

cd "${WORK_DIR}"
sed -i "s/^pkgver=.*/pkgver=${APP_VERSION}/" PKGBUILD
sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
sed -i "s/^sha256sums=('[^']*')/sha256sums=('${HASH}')/" PKGBUILD

makepkg -s
makepkg --printsrcinfo > .SRCINFO

git add PKGBUILD .SRCINFO
git commit -m "bump to v${APP_VERSION}"
git push origin master

rm -rf "${WORK_DIR}"
rm -f "${ROOT_DIR}/${SOURCE_ARCHIVE}"

echo "=== Done ==="
