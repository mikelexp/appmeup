# Cómo publicar una nueva versión

Son dos pasos: GitHub Release (automático) y AUR (manual).

---

## 1. GitHub Release

Esto lo hace GitHub Actions automáticamente. Solo necesitás:

```bash
# 1. Cambiá la versión con make/just (ej: 1.2.1 → 1.3.0)
make set-version VERSION=1.3.0
# o
just set-version 1.3.0

# Si solo querés verla
make version
# o
just version

# 2. Commiteá y etiquetá
git commit -am "bump to v1.3"
git tag v1.3

# 3. Subí todo
git push github main v1.3
```

En GitHub Actions arranca el build automático. Cuando termina, el Release ya está
publicado con el tarball listo para descargar.

> **¿Cómo sé que terminó?** Andá a la pestaña "Actions" del repo en GitHub, o
> corre `gh run list --repo mikelexp/appmeup` y fijate que esté en verde.

---

## 2. AUR (appmeup)

Una vez que el GitHub Release está publicado, actualizás el paquete de AUR
automáticamente con un solo comando:

```bash
make aur-update
# o
just aur-update
```

El script (`scripts/aur-update.sh`) hace todo solo:
1. Lee la versión de `src/constants.py`
2. Descarga el tarball del código fuente de la tag
3. Calcula el SHA256
4. Clona el repo AUR desde cero
5. Actualiza `PKGBUILD` (versión, checksum, resetea pkgrel)
6. Corre `makepkg -s` para verificar
7. Genera `.SRCINFO`
8. Commitea y pushea a AUR

---

## En resumen

```
1. `make set-version` / `just set-version` → cambia `src/constants.py` y `PKGBUILD`
2. git commit + tag + push
3. Esperar a que GitHub Actions termine el build
4. make aur-update
```
