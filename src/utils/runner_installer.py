import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from src.utils.const import WebPath


class RunnerInstaller:
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
            completed = subprocess.run(
                [str(runner_path), "--version"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if completed.returncode != 0:
                return ""
            output = completed.stdout or completed.stderr or ""
            return RunnerInstaller._normalize_output_version(output)
        except Exception:
            return ""

    @staticmethod
    def _download_file(url: str, target: Path):
        with urllib.request.urlopen(url, timeout=30) as resp:
            target.write_bytes(resp.read())

    @staticmethod
    def _extract_archive_to_dir(archive_path: Path, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        if archive_path.suffix == ".zip" or str(archive_path).endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(out_dir)
        else:
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(out_dir)

        runner_name = RunnerInstaller._runner_name()
        runner_path = out_dir / runner_name
        if not runner_path.exists():
            raise Exception(f"runner executable not found after extract: {runner_path}")
        if os.name != "nt":
            try:
                mode = os.stat(runner_path).st_mode
                os.chmod(runner_path, mode | 0o111)
            except Exception:
                pass

    @staticmethod
    def _install_from_release(version: str, target_dir: Path):
        if os.name == "nt":
            url = WebPath.LocalWindowsRunnerDownloadUrlTemplate.format(version=version)
            ext = ".zip"
        else:
            url = WebPath.LocalLinuxRunnerDownloadUrlTemplate.format(version=version)
            ext = ".tar.gz"

        target_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as td:
            archive_path = Path(td) / f"runner{ext}"
            RunnerInstaller._download_file(url, archive_path)
            RunnerInstaller._extract_archive_to_dir(archive_path, target_dir)

    @staticmethod
    def ensure_local_runner(base_dir: str | Path, version: str) -> tuple[bool, str | None, str | None]:
        version = str(version or "").strip()
        if not version:
            return False, None, "version is empty"

        target_dir = RunnerInstaller._runner_target_dir(base_dir)
        target_path = RunnerInstaller._runner_target_path(base_dir)

        try:
            if target_path.exists():
                local_runner_version = RunnerInstaller._read_runner_version(target_path)
                if local_runner_version == version:
                    return True, str(target_path), None

            RunnerInstaller._install_from_release(version=version, target_dir=target_dir)

            installed_version = RunnerInstaller._read_runner_version(target_path)
            if installed_version != version:
                return False, None, f"runner version mismatch, expected {version}, got {installed_version}"

            return True, str(target_path), None
        except Exception as e:
            return False, None, str(e)
