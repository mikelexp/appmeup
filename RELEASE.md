# Cómo publicar una nueva versión

Tenés que hacer dos cosas: subir el binario a GitHub y actualizar el paquete de AUR.
Siempre se hace en ese orden (primero GitHub, después AUR).

## 1. GitHub Release

Esto lo hace GitHub Actions automáticamente. Solo necesitás:

```bash
# 1. Cambiá la versión en src/constants.py
#    (ej: "1.2" → "1.3")

# 2. Commiteá y etiquetá
git commit -am "bump to v1.3"
git tag v1.3

# 3. Subí todo
git push github main v1.3
```

En GitHub Actions arranca el build automático. Cuando termina, el Release ya está
publicado con el tarbal listo para descargar.

> **¿Cómo sé que terminó?** Andá a la pestaña "Actions" del repo en GitHub, o
> corre `gh run list --repo mikelexp/appmeup` y fijate que esté en verde.

---

## 2. AUR (appmeup-bin)

Una vez que el GitHub Release está publicado, actualizás el paquete de AUR.

### 2a. Conseguí el checksum del tarball

```bash
gh release download v1.3 --repo mikelexp/appmeup --pattern '*.tar.gz' --clobber
sha256sum appmeup-1.3-linux-x86_64.tar.gz
```

Te va a mostrar algo como:
```
f1063ada2bd960acb3e04e0997ff4dd5701b0d1ed07b81cc0f767b7765a442ea  appmeup-1.3-linux-x86_64.tar.gz
```
Esa cadena larga es el checksum. La vas a necesitar en el próximo paso.

### 2b. Actualizá el PKGBUILD

Abrí `PKGBUILD` y cambiá dos cosas:

- `pkgver=1.2` → `pkgver=1.3`
- `sha256sums=('...')` → pegá el checksum que sacaste antes

### 2c. Subí a AUR

```bash
# Entrá al repo de AUR (lo clonaste la primera vez)
cd /tmp/appmeup-bin

# Copiá el PKGBUILD actualizado
cp /ruta/a/tu/proyecto/AppMeUp/PKGBUILD .

# Verificá que todo funciona
makepkg -s

# Generá el archivo .SRCINFO (lo necesita AUR)
makepkg --printsrcinfo > .SRCINFO

# Subí
git add PKGBUILD .SRCINFO
git commit -m "bump to v1.3"
git push origin master
```

Listo. En unos minutos el paquete actualizado aparece en AUR y los usuarios
pueden instalarlo con `yay -S appmeup-bin`.

---

## En resumen

```
1. src/constants.py  → cambiar versión
2. git commit + tag + push
3. Esperar a que GitHub Actions termine
4. gh release download → sha256sum
5. PKGBUILD → cambiar versión y checksum
6. cd /tmp/appmeup-bin → makepkg → git push
```
