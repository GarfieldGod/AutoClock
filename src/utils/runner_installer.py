import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from src.utils.const import WebPath
from src.utils.download_helper import DownloadHelper


class RunnerInstaller:
    @staticmethod
    def _notify_progress(progress_callback, phase: str, percent: int, message: str):
        try:
            if callable(progress_callback):
                progress_callback(phase, max(0, min(100, int(percent))), str(message or ""))
        except Exception:
            pass

    @staticmethod
    def _runner_name() -> str:
        return "auto-clock-runner.exe" if os.name == "nt" else "auto-clock-runner"

    @staticmethod
    def _runner_target_dir(base_dir: str | Path) -> Path:
        return Path(base_dir).resolve()

    @staticmethod
    def _runner_target_path(base_dir: str | Path) -> Path:
        return RunnerInstaller._runner_target_dir(base_dir) / RunnerInstaller._runner_name()

    @staticmethod
    def _normalize_output_version(text: str) -> str:
        lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
        return lines[-1] if lines else ""

    @staticmethod
    def _read_runner_version(runner_path: Path) -> str:
        try:
            kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": 15,
            }
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            completed = subprocess.run(
                [str(runner_path), "--version"],
                **kwargs,
            )
            if completed.returncode != 0:
                return ""
            output = completed.stdout or completed.stderr or ""
            return RunnerInstaller._normalize_output_version(output)
        except Exception:
            return ""

    @staticmethod
    def is_local_runner_ready(base_dir: str | Path, version: str) -> bool:
        version = str(version or "").strip()
        if not version:
            return False

        try:
            target_path = RunnerInstaller._runner_target_path(base_dir)
            if not target_path.exists():
                return False
            local_runner_version = RunnerInstaller._read_runner_version(target_path)
            return local_runner_version == version
        except Exception:
            return False

    @staticmethod
    def _download_file(url: str, target: Path, progress_callback=None):
        def _on_percent(percent: int):
            RunnerInstaller._notify_progress(progress_callback, "downloading", percent, "Downloading runner package...")

        DownloadHelper.download_file(url=url, target=target, timeout=30, progress_callback=_on_percent)
        RunnerInstaller._notify_progress(progress_callback, "downloading", 100, "Download completed")

    @staticmethod
    def _extract_archive_to_dir(archive_path: Path, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        runner_name = RunnerInstaller._runner_name()

        with tempfile.TemporaryDirectory() as extract_td:
            extract_dir = Path(extract_td)
            if archive_path.suffix == ".zip" or str(archive_path).endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(extract_dir)
            else:
                with tarfile.open(archive_path, "r:gz") as tf:
                    tf.extractall(extract_dir)

            candidates = list(extract_dir.rglob(runner_name))
            if not candidates:
                raise Exception(f"runner executable not found after extract: {runner_name}")

            src_runner = candidates[0]
            runner_path = out_dir / runner_name
            tmp_runner_path = out_dir / f".{runner_name}.tmp"

            if tmp_runner_path.exists():
                tmp_runner_path.unlink()

            shutil.copy2(src_runner, tmp_runner_path)
            if runner_path.exists():
                runner_path.unlink()
            tmp_runner_path.replace(runner_path)

        if os.name != "nt":
            try:
                mode = os.stat(runner_path).st_mode
                os.chmod(runner_path, mode | 0o111)
            except Exception:
                pass

    @staticmethod
    def _install_from_release(version: str, target_dir: Path, progress_callback=None):
        if os.name == "nt":
            urls = [WebPath.LocalWindowsRunnerDownloadUrlTemplate.format(version=version)]
            ext = ".zip"
        else:
            urls = [
                WebPath.LocalLinuxRunnerDownloadUrlTemplate.format(version=version),
                WebPath.LinuxRunnerDownloadUrlTemplate.format(version=version),
            ]
            ext = ".tar.gz"

        target_dir.mkdir(parents=True, exist_ok=True)

        last_error = None
        with tempfile.TemporaryDirectory() as td:
            for idx, url in enumerate(urls):
                archive_path = Path(td) / f"runner_{idx}{ext}"
                try:
                    RunnerInstaller._notify_progress(progress_callback, "downloading", 1, f"Downloading runner ({idx + 1}/{len(urls)})")
                    RunnerInstaller._download_file(url, archive_path, progress_callback=progress_callback)
                    RunnerInstaller._notify_progress(progress_callback, "extracting", 85, "Extracting runner...")
                    RunnerInstaller._extract_archive_to_dir(archive_path, target_dir)
                    RunnerInstaller._notify_progress(progress_callback, "extracting", 95, "Runner extracted")
                    return
                except Exception as e:
                    last_error = e
                    continue

        raise Exception(str(last_error) if last_error else "download runner failed")

    @staticmethod
    def ensure_local_runner(base_dir: str | Path, version: str, progress_callback=None) -> tuple[bool, str | None, str | None]:
        version = str(version or "").strip()
        if not version:
            return False, None, "version is empty"

        target_dir = RunnerInstaller._runner_target_dir(base_dir)
        target_path = RunnerInstaller._runner_target_path(base_dir)

        try:
            RunnerInstaller._notify_progress(progress_callback, "checking", 2, "Checking local runner...")
            if target_path.exists():
                local_runner_version = RunnerInstaller._read_runner_version(target_path)
                if local_runner_version == version:
                    RunnerInstaller._notify_progress(progress_callback, "done", 100, "Runner is up to date")
                    return True, str(target_path), None

            RunnerInstaller._install_from_release(version=version, target_dir=target_dir, progress_callback=progress_callback)

            RunnerInstaller._notify_progress(progress_callback, "verifying", 97, "Verifying runner version...")
            if not target_path.exists():
                return False, None, f"runner executable not found: {target_path}"

            installed_version = RunnerInstaller._read_runner_version(target_path)
            if installed_version and installed_version != version:
                return False, None, f"runner version mismatch, expected {version}, got {installed_version}"
            if not installed_version:
                RunnerInstaller._notify_progress(progress_callback, "verifying", 99, "Runner file is ready")

            RunnerInstaller._notify_progress(progress_callback, "done", 100, "Runner is ready")
            return True, str(target_path), None
        except Exception as e:
            return False, None, str(e)
