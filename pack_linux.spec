# auto_clock_linux.spec
# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# 项目根目录
project_root = r"."
# 主脚本路径
main_script = os.path.join(project_root, "entry.py")

# 依赖的额外文件
extra_files = []
config_dir = os.path.join(project_root, "config.json")
resource_path = os.path.join(project_root, "ui", "resource")

if os.path.exists(config_dir):
    extra_files.append((str(config_dir), "."))
if os.path.exists(resource_path):
    extra_files.append((str(resource_path), os.path.join(".", "ui", "resource")))

a = Analysis(
    [str(main_script)],
    pathex=[str(project_root)],
    binaries=[],
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

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="auto_clock",  # 可执行文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Linux下可以使用UPX压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Linux下使用控制台模式
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
