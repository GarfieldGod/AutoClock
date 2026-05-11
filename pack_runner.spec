# auto_clock_runner.spec
# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

project_root = r"."
runner_script = os.path.join(project_root, "src", "runner", "runner_main.py")
config_dir = os.path.join(project_root, "config.json")
ico = os.path.join(project_root, "icon.ico")

extra_files = []
if os.path.exists(config_dir):
    extra_files.append((str(config_dir), "."))

a_runner = Analysis(
    [str(runner_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=extra_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz_runner = PYZ(a_runner.pure, a_runner.zipped_data, cipher=None)

exe_runner = EXE(
    pyz_runner,
    a_runner.scripts,
    [],
    [],
    [],
    [],
    name="auto-clock-runner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    exclude_binaries=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ico,
)

coll = COLLECT(
    exe_runner,
    a_runner.binaries,
    a_runner.zipfiles,
    a_runner.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="auto-clock-runner",
)
