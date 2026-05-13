import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from src.utils.log import Log
from src.utils.utils import Utils
from src.utils.const import AppPath, WebPath
from src.utils.download_helper import DownloadHelper


def check_update():
    if not os.path.exists(AppPath.ConfigJson):
        Log.info(f"App Config File {AppPath.ConfigJson} doesn't exist")
        return False, {}
    Log.info(AppPath.ConfigJson)
    config_dict = Utils.read_dict_from_json(AppPath.ConfigJson)
    if not config_dict: return False

    local_ver = config_dict[0].get("version")
    Log.info(f"Current local version: {local_ver}")
    if not local_ver: 
        return False, {}
    try:
        github_ok = DownloadHelper.supports_github(timeout=2)
        if github_ok:
            try:
                response = requests.get(WebPath.AppConfigPathGitHub, timeout=2)
            except Exception as e:
                Log.info(f"GitHub version check failed, fallback to Gitee: {e}")
                response = requests.get(WebPath.AppConfigPathGitee, timeout=3)
        else:
            Log.info("Direct GitHub access unavailable, checking via Gitee")
            response = requests.get(WebPath.AppConfigPathGitee, timeout=3)

        if not response: 
            return False, {}
        remote_info = response.json()
        if not remote_info: 
            return False, {}
        remote_ver = remote_info[0].get("version")
        Log.info(f"Current newest version: {remote_ver}")
        version = {"local": local_ver, "remote": remote_ver}

        if compare_version(remote_ver, local_ver) > 0:
            return True, version
        else:
            return False, version
    except Exception as e:
        Log.info(f"Version check failed: {e}")
        # 返回空字典而不是None，以避免类型错误
        return False, {}


def compare_version(ver1, ver2):
    v1 = list(map(int, ver1.split(".")))
    v2 = list(map(int, ver2.split(".")))
    max_len = max(len(v1), len(v2))
    v1 += [0] * (max_len - len(v1))
    v2 += [0] * (max_len - len(v2))
    return 1 if v1 > v2 else (-1 if v1 < v2 else 0)


class VersionCheckThread(QThread):
    check_finished = pyqtSignal(bool, dict)

    def __init__(self):
        super().__init__()

    def run(self):
        Log.info("Running version check in background...")
        ok, ver = check_update()
        self.check_finished.emit(ok, ver)


def _notify_update_progress(progress_callback, percent: int, message: str):
    try:
        if callable(progress_callback):
            progress_callback(max(0, min(100, int(percent))), str(message or ""))
    except Exception:
        pass


def _app_download_url(version: str) -> str:
    version = str(version or "").strip()
    if os.name == "nt":
        return WebPath.AppWindowsDownloadUrlTemplate.format(version=version)
    return WebPath.AppLinuxDownloadUrlTemplate.format(version=version)


def _find_app_executable(root: Path) -> Path | None:
    if os.name == "nt":
        candidates = [
            p for p in root.rglob("*.exe")
            if "runner" not in p.name.lower() and ("auto" in p.name.lower() or "clock" in p.name.lower())
        ]
    else:
        candidates = [
            p for p in root.rglob("*")
            if p.is_file() and os.access(p, os.X_OK) and "runner" not in p.name.lower() and ("auto" in p.name.lower() or "clock" in p.name.lower())
        ]

    if not candidates:
        return None

    candidates.sort(key=lambda p: (len(str(p)), str(p)))
    return candidates[0]


def auto_download_and_install(version: str, progress_callback=None) -> tuple[bool, str, str]:
    if not getattr(sys, "frozen", False):
        return False, "Auto-install is not supported in development environment. Please download manually.", ""

    version = str(version or "").strip()
    if not version:
        return False, "Version number is empty.", ""

    platform_name = "windows" if os.name == "nt" else "linux"
    updater_dir = Path(AppPath.UpdaterRoot)
    updater_dir.mkdir(parents=True, exist_ok=True)
    target_dir = updater_dir / f"auto-clock-{version}-{platform_name}"

    archive_ext = ".zip" if os.name == "nt" else ".tar.gz"
    download_url = _app_download_url(version)

    _notify_update_progress(progress_callback, 3, "Preparing download...")
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        archive_path = temp_dir / f"auto-clock-{version}{archive_ext}"

        def _on_download_percent(percent: int):
            mapped = 8 + int(max(0, min(100, int(percent))) * 0.70)
            _notify_update_progress(progress_callback, mapped, "Downloading update package...")

        DownloadHelper.download_file(
            url=download_url,
            target=archive_path,
            timeout=40,
            progress_callback=_on_download_percent,
        )

        _notify_update_progress(progress_callback, 80, "Extracting update package...")
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        if archive_path.suffix == ".zip" or str(archive_path).endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
        else:
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(extract_dir)

        roots = list(extract_dir.iterdir())
        source_root = extract_dir
        if len(roots) == 1 and roots[0].is_dir():
            source_root = roots[0]

        _notify_update_progress(progress_callback, 88, "Installing to local directory...")
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        shutil.copytree(source_root, target_dir, dirs_exist_ok=True)

        # 清理 auto-updater 目录下除当前版本外的其他旧版本目录
        for dir in updater_dir.iterdir():
            if dir.is_dir() and dir != target_dir:
                shutil.rmtree(dir, ignore_errors=True)

    _notify_update_progress(progress_callback, 95, "Locating new version executable...")
    launch_path = _find_app_executable(target_dir)
    if not launch_path:
        return False, f"Installation complete but executable not found: {target_dir}", ""

    _notify_update_progress(progress_callback, 100, "Update installation completed.")
    return True, f"Installed to: {target_dir}", str(launch_path)


class AppUpdateInstallThread(QThread):
    progress_changed = pyqtSignal(int, str)
    install_finished = pyqtSignal(bool, str, str)

    def __init__(self, version: str):
        super().__init__()
        self.version = str(version or "").strip()

    def run(self):
        try:
            ok, message, launch_path = auto_download_and_install(
                version=self.version,
                progress_callback=lambda p, m: self.progress_changed.emit(int(p), str(m or "")),
            )
            self.install_finished.emit(bool(ok), str(message or ""), str(launch_path or ""))
        except Exception as e:
            self.install_finished.emit(False, str(e), "")