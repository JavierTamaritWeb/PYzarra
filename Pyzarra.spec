# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para macOS (.app)

Uso:
    uv run pyinstaller --noconfirm Pyzarra.spec

Resultado:
    dist/Pyzarra.app
"""

from pathlib import Path

APP_NAME = "Pyzarra"
BUNDLE_ID = "es.javiertamarit.pyzarra"
VERSION = "4.9.0"

ROOT = Path(SPECPATH)
WEB_DIR = ROOT / "src" / "pyzarra" / "web"
ICON = ROOT / "assets" / "icon.icns"   # opcional, ver README

a = Analysis(
    ["src/pyzarra/main.py"],

    pathex=["src"],

    # ---- ARCHIVOS QUE HAY QUE METER DENTRO DEL .app ----
    # Formato: (origen, destino_dentro_del_bundle)
    datas=[
        (str(WEB_DIR), "pyzarra/web"),
    ],

    # ---- IMPORTS QUE PyInstaller NO DETECTA SOLO ----
    hiddenimports=[
        "webview.platforms.cocoa",
        "objc",
        "Foundation",
        "AppKit",
        "WebKit",
        "Quartz",
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    # ---- QUITAR PESO: motores de otros sistemas ----
    excludes=[
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "webview.platforms.gtk",
        "webview.platforms.qt",
        "tkinter",
        "test",
        "unittest",
    ],

    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX rompe firmas en macOS. Dejar False.
    console=False,          # sin ventana de terminal
    disable_windowed_traceback=False,
    argv_emulation=True,    # permite arrastrar archivos sobre el icono
    target_arch=None,       # None = arquitectura de tu Mac.
                            # "universal2" = Intel + Apple Silicon
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=str(ICON) if ICON.exists() else None,
    bundle_identifier=BUNDLE_ID,
    version=VERSION,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,          # pantallas Retina
        "NSRequiresAquaSystemAppearance": False,  # respeta modo oscuro
        "LSMinimumSystemVersion": "11.0",
        "LSApplicationCategoryType": "public.app-category.productivity",
        "NSHumanReadableCopyright": "© 2026 Javier Tamarit",
    },
)
