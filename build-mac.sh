#!/usr/bin/env bash
#
# Construye Pyzarra.app para macOS
#
# Uso:  ./build-mac.sh
#
set -euo pipefail

APP_NAME="Pyzarra"

echo "==> 1/4  Limpiando builds anteriores"
rm -rf build dist

echo "==> 2/4  Sincronizando dependencias"
uv sync --all-extras

echo "==> 3/4  Compilando con PyInstaller"
uv run pyinstaller --noconfirm "${APP_NAME}.spec"

echo "==> 4/4  Firma local ad-hoc"
# Sin esto, macOS puede bloquear la app en Apple Silicon.
codesign --force --deep --sign - "dist/${APP_NAME}.app"

echo ""
echo "LISTO -> dist/${APP_NAME}.app"
echo ""
echo "Probar:      open dist/${APP_NAME}.app"
echo "Ver errores: ./dist/${APP_NAME}.app/Contents/MacOS/${APP_NAME}"
