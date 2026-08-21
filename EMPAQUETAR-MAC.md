# Empaquetar para macOS (.app)

---

## Paso 1 — Instalar PyInstaller

```bash
uv add --dev pyinstaller
```

---

## Paso 2 — Construir

```bash
chmod +x build-mac.sh
./build-mac.sh
```

Resultado: **`dist/Pyzarra.app`**

Doble clic y funciona.

---

## Si prefieres a mano

```bash
uv run pyinstaller --noconfirm Pyzarra.spec
codesign --force --deep --sign - dist/Pyzarra.app
```

⚠️ **El `codesign` NO es opcional en Apple Silicon (M1/M2/M3/M4).**
Sin él, macOS mata la app al abrirla.

---

## Icono (opcional)

macOS necesita formato `.icns`, no `.png`.

Convertir un PNG de 1024x1024:

```bash
mkdir -p assets icon.iconset

sips -z 16 16     mi-logo.png --out icon.iconset/icon_16x16.png
sips -z 32 32     mi-logo.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     mi-logo.png --out icon.iconset/icon_32x32.png
sips -z 64 64     mi-logo.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   mi-logo.png --out icon.iconset/icon_128x128.png
sips -z 256 256   mi-logo.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   mi-logo.png --out icon.iconset/icon_256x256.png
sips -z 512 512   mi-logo.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   mi-logo.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 mi-logo.png --out icon.iconset/icon_512x512@2x.png

iconutil -c icns icon.iconset -o assets/icon.icns
rm -rf icon.iconset
```

El `.spec` lo detecta solo si existe en `assets/icon.icns`.

---

## Antes de publicar: quitar el modo debug

En `src/pyzarra/main.py`, cambia:

```python
webview.start(debug=True)    # ANTES
webview.start(debug=False)   # DESPUES
```

Con `debug=True` el usuario puede abrir "Inspeccionar elemento" con el botón derecho.

---

## Universal (Intel + Apple Silicon)

En `Pyzarra.spec`, dentro de `EXE(...)`:

```python
target_arch="universal2",
```

⚠️ Solo funciona si **todas** tus librerías tienen build universal.
Si falla, déjalo en `None` (compila solo para tu Mac).

---

## Problemas típicos

| Síntoma | Causa | Solución |
|---|---|---|
| Ventana en blanco | La web no se copió | Revisa `datas=` en el `.spec` |
| "La app está dañada" | Falta firma | Ejecuta el `codesign` |
| Se cierra al instante | Error de Python | Ver comando de abajo |
| No encuentra `index.html` | Ruta absoluta en HTML | Usa rutas relativas |

**Ver el error real** (abre la app desde terminal y muestra los mensajes):
```bash
./dist/Pyzarra.app/Contents/MacOS/Pyzarra
```

---

## Distribuir a otras personas

| Situación | Qué necesitas |
|---|---|
| Solo tú | Nada más. Ya está. |
| Amigos / equipo | Ellos: botón derecho → Abrir → Abrir (1ª vez) |
| Público general | Cuenta Apple Developer (99 €/año) + notarización |

---

## ⚠️ Importante

El `.app` **solo funciona en macOS**.
Para Windows hay que compilar **desde un Windows** — PyInstaller no hace cruzado.
