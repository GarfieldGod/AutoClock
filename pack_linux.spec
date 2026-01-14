# auto_clock_linux.spec
# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
import sysconfig
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# 项目根目录
project_root = r"."
# 主脚本路径
main_script = os.path.join(project_root, "entry.py")
runner_script = os.path.join(project_root, "src", "runner", "runner_main.py")

extra_binaries = []

# 依赖的额外文件
extra_files = []
config_dir = os.path.join(project_root, "config.json")
resource_path = os.path.join(project_root, "ui", "resource")

if os.path.exists(config_dir):
    extra_files.append((str(config_dir), "."))
if os.path.exists(resource_path):
    extra_files.append((str(resource_path), os.path.join(".", "ui", "resource")))

a_ui = Analysis(
    [str(main_script)],
    pathex=[str(project_root)],
    binaries=extra_binaries,
    datas=extra_files,
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

a_runner = Analysis(
    [str(runner_script)],
    pathex=[str(project_root)],
    binaries=extra_binaries,
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz_ui = PYZ(a_ui.pure, a_ui.zipped_data, cipher=None)
pyz_runner = PYZ(a_runner.pure, a_runner.zipped_data, cipher=None)

exe_ui = EXE(
    pyz_ui,
    a_ui.scripts,
    [],
    [],
    [],
    [],
    name="auto_clock",
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
)

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
)

coll = COLLECT(
    exe_ui,
    exe_runner,
    a_ui.binaries,
    a_ui.zipfiles,
    a_ui.datas,
    a_runner.binaries,
    a_runner.zipfiles,
    a_runner.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="auto_clock"
)
