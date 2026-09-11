import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# Release-window evaluation build. Keep the existing console=True native spec as
# the diagnosable engineering baseline; this spec proves the GUI subsystem only.
ROOT = Path(SPECPATH).resolve().parents[1]
ENTRY = ROOT / "studio" / "native_windowed.py"


def windows_identity_resources():
    if sys.platform != "win32":
        return None, None
    identity_dir = os.environ.get("GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR")
    if not identity_dir:
        raise RuntimeError("GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR is required for Windows packaging")
    root = Path(identity_dir).resolve()
    version = root / "version-info.txt"
    icon = root / "gpbiometricspy-studio.ico"
    if not version.is_file() or not icon.is_file():
        raise RuntimeError(f"Generated Windows identity resources are incomplete below {root}")
    return str(version), str(icon)


VERSION_RESOURCE, ICON_RESOURCE = windows_identity_resources()

datas = []
for package in ("studio", "gpbiometricspy", "shiny", "htmltools", "shinychat", "webview"):
    datas.extend(collect_data_files(package))

hiddenimports = sorted(
    set(
        collect_submodules("studio.modules")
        + collect_submodules("shiny")
        + collect_submodules("uvicorn")
        + collect_submodules("webview")
    )
)


a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT), str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "playwright", "ruff", "twine", "build", "cefpython3", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gpbiometricspy-studio-native",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    version=VERSION_RESOURCE,
    icon=ICON_RESOURCE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="gpbiometricspy-studio-native",
)
