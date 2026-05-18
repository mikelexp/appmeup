# Cómo publicar una nueva versión

```bash
# 1. Cambiá la versión en src/constants.py (ej: "1.2" → "1.3")
# 2. Commiteá y etiquetá
git commit -am "bump to v1.3"
git tag v1.3

# 3. Subí todo
git push github main v1.3
```

### Qué pasa automáticamente

| Workflow | Qué hace |
|---|---|
| `Release` | Compila con Nuitka y crea el Release en GitHub |
| `Update AUR` | Al publicarse el release, actualiza `appmeup-bin` en AUR |

Solo funciona si configuraste el secret `AUR_SSH_KEY` en el repositorio de
GitHub (tu clave SSH privada de AUR).
