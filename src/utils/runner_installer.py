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
    def _runner_target_path(base_dir: str | Path) -> Path:
        return Path(base_dir).resolve() / RunnerInstaller._runner_name()

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
    def _extract_runner_from_zip(zip_path: Path, out_path: Path):
        with zipfile.ZipFile(zip_path, "r") as zf:
            candidate = None
            expected = RunnerInstaller._runner_name().lower()
            for name in zf.namelist():
                low = str(name).lower().replace("\\", "/")
                if low.endswith("/" + expected) or low.endswith(expected):
                    candidate = name
                    break
            if candidate is None:
                raise Exception(f"runner executable not found in zip: {zip_path}")

            with zf.open(candidate, "r") as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

    @staticmethod
    def _extract_runner_from_targz(tar_path: Path, out_path: Path):
        with tarfile.open(tar_path, "r:gz") as tf:
            candidate = None
            expected = RunnerInstaller._runner_name().lower()
            for member in tf.getmembers():
                low = str(member.name).lower().replace("\\", "/")
                if low.endswith("/" + expected) or low.endswith(expected):
                    candidate = member
                    break
            if candidate is None:
                raise Exception(f"runner executable not found in tar.gz: {tar_path}")

            src = tf.extractfile(candidate)
            if src is None:
                raise Exception("failed to read runner executable from tar.gz")
            with src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

    @staticmethod
    def _install_from_release(version: str, target_path: Path):
        if os.name == "nt":
            url = WebPath.LocalWindowsRunnerDownloadUrlTemplate.format(version=version)
            ext = ".zip"
        else:
            url = WebPath.LocalLinuxRunnerDownloadUrlTemplate.format(version=version)
            ext = ".tar.gz"

        target_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as td:
            archive_path = Path(td) / f"runner{ext}"
            RunnerInstaller._download_file(url, archive_path)

            temp_runner = Path(td) / RunnerInstaller._runner_name()
            if os.name == "nt":
                RunnerInstaller._extract_runner_from_zip(archive_path, temp_runner)
            else:
                RunnerInstaller._extract_runner_from_targz(archive_path, temp_runner)

            shutil.copy2(temp_runner, target_path)

        if os.name != "nt":
            try:
                mode = os.stat(target_path).st_mode
                os.chmod(target_path, mode | 0o111)
            except Exception:
                pass

    @staticmethod
    def ensure_local_runner(base_dir: str | Path, version: str) -> tuple[bool, str | None, str | None]:
        version = str(version or "").strip()
        if not version:
            return False, None, "version is empty"

        target_path = RunnerInstaller._runner_target_path(base_dir)

        try:
            if target_path.exists():
                local_runner_version = RunnerInstaller._read_runner_version(target_path)
                if local_runner_version == version:
                    return True, str(target_path), None

            RunnerInstaller._install_from_release(version=version, target_path=target_path)

            installed_version = RunnerInstaller._read_runner_version(target_path)
            if installed_version != version:
                return False, None, f"runner version mismatch, expected {version}, got {installed_version}"

            return True, str(target_path), None
        except Exception as e:
            return False, None, str(e)
