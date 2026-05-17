# Release process

## New version

1. Edit `src/constants.py` and bump `APP_VERSION` (e.g. `"1.2"` → `"1.3"`)
2. Commit: `git commit -am "bump to v1.3"`
3. Tag: `git tag v1.3`
4. Push: `git push github main v1.3`

GitHub Actions builds the binary and creates the Release automatically.

---

## AUR (appmeup-bin)

After the GitHub release is published:

1. Download the new tarball and compute its SHA256:
   ```
   gh release download v1.3 --repo mikelexp/appmeup --pattern '*.tar.gz' --clobber
   sha256sum appmeup-*-linux-x86_64.tar.gz
   ```

2. Update `PKGBUILD`:
   - `pkgver=1.3`
   - `sha256sums=('...new hash...')`

3. Commit and push to the AUR repo:
   ```
   cd /tmp/appmeup-bin
   cp /path/to/appmeup/PKGBUILD .
   makepkg -s
   makepkg --printsrcinfo > .SRCINFO
   git add PKGBUILD .SRCINFO
   git commit -m "bump to v1.3"
   git push origin master
   ```
