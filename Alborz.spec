# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules
from pathlib import Path

datas = []

# HTML templates
web_templates = Path("Alborz/web/templates")
if web_templates.exists():
    datas.append((str(web_templates), "Alborz/web/templates"))

# Static (icons, fonts)
web_static = Path("Alborz/web/static")
if web_static.exists():
    datas.append((str(web_static), "Alborz/web/static"))

hiddenimports = []
for pkg in [
    "PIL", "PIL.Image", "PIL.ExifTags", "PIL.TiffImagePlugin",
    "exifread", "piexif",
    "mutagen",
    "uvicorn", "uvicorn.logging", "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "fastapi", "starlette",
    "jinja2",
    "anyio",
    "httptools",
    "multipart",
    "reportlab", "reportlab.pdfbase", "reportlab.pdfbase.ttfonts",
    "requests",
]:
    try:
        _, _, hi = collect_all(pkg)
        hiddenimports += hi
    except Exception:
        pass

hiddenimports += collect_submodules("mutagen")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "numpy", "pandas",
        "IPython", "jupyter", "notebook", "pytest",
        "PyQt5", "PySide2", "wx",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Alborz",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="Alborz/web/static/icon.ico" if Path("Alborz/web/static/icon.ico").exists() else None,
)