# auto_clock.spec
# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# 项目根目录
project_root = r"."
# 主脚本路径
main_script = os.path.join(project_root, "entry.py")
ico = os.path.join(project_root, "icon.ico")

# 依赖的额外文件
extra_files = []
config_dir = os.path.join(project_root, "config.json")
ico_dir = os.path.join(project_root, "icon.ico")
resource_path = os.path.join(project_root, "ui", "resource")

if os.path.exists(config_dir):
    extra_files.append((str(config_dir), "."))
if os.path.exists(ico_dir):
    extra_files.append((str(ico_dir), "."))
if os.path.exists(resource_path):
    extra_files.append((str(resource_path), os.path.join(".", "ui", "resource")))

a = Analysis(
    [str(main_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=extra_files,
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

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="auto_clock",  # exe 文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ico,
    uac_admin=True
)