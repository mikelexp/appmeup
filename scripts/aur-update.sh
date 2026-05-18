#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

APP_VERSION="$(python3 -c "import sys; sys.path.insert(0, '${ROOT_DIR}'); from src.constants import APP_VERSION; print(APP_VERSION)")"
REPO_NAME="appmeup-bin"
AUR_SSH="ssh://aur@aur.archlinux.org/${REPO_NAME}.git"
WORK_DIR="$(mktemp -d /tmp/aur-update-XXXXX)"

echo "=== Updating AUR package ${REPO_NAME} to version ${APP_VERSION} ==="

cd "${ROOT_DIR}"
gh release download "v${APP_VERSION}" --repo mikelexp/appmeup --pattern '*.tar.gz' --clobber

HASH="$(sha256sum appmeup-${APP_VERSION}-linux-x86_64.tar.gz | cut -d' ' -f1)"
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
rm -f "${ROOT_DIR}/appmeup-${APP_VERSION}-linux-x86_64.tar.gz"

echo "=== Done ==="
