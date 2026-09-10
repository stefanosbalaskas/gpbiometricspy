from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# Evaluation-only onefile comparison. Keep the same frozen entry point, package
# data and hidden-import contract as the certified onedir build so packaging
# mode is the only intentional variable.
ROOT = Path(SPECPATH).resolve().parents[1]
ENTRY = ROOT / "studio" / "frozen.py"


datas = []
for package in ("studio", "gpbiometricspy", "shiny", "htmltools", "shinychat"):
    datas.extend(collect_data_files(package))

hiddenimports = sorted(
    set(
        collect_submodules("studio.modules")
        + collect_submodules("shiny")
        + collect_submodules("uvicorn")
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
    excludes=["pytest", "playwright", "ruff", "twine", "build"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="gpbiometricspy-studio-onefile",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
