import json
import posixpath
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from src.extend.ssh_client import SshClient
from src.utils.download_helper import DownloadHelper


@dataclass
class RemoteLinuxLayout:
    app_root: str = "${HOME}/.local/share/auto-clock"

    @property
    def servers_root(self) -> str:
        return posixpath.join(self.app_root, "servers")

    def version_dir(self, version: str) -> str:
        return posixpath.join(self.servers_root, version)

    @property
    def current_dir(self) -> str:
        return posixpath.join(self.servers_root, "current")

    @property
    def runner_path_current(self) -> str:
        return posixpath.join(self.current_dir, "auto-clock-runner")

    def runner_path_version(self, version: str) -> str:
        return posixpath.join(self.version_dir(version), "auto-clock-runner")


class RemoteLinuxRunner:
    def __init__(self, ssh: SshClient, layout: Optional[RemoteLinuxLayout] = None):
        self._ssh = ssh
        self._layout = layout or RemoteLinuxLayout()

    @property
    def layout(self) -> RemoteLinuxLayout:
        return self._layout

    def ensure_version_dir(self, version: str) -> str:
        remote_dir = self._layout.version_dir(version)
        self._ssh.exec(f"mkdir -p {remote_dir}")
        return remote_dir

    def remote_has_version(self, version: str) -> bool:
        code, _, _ = self._ssh.exec(f"test -x {self._layout.runner_path_version(version)}")
        return code == 0

    def current_runner_exists(self) -> bool:
        code, _, _ = self._ssh.exec(f"test -x {self._layout.runner_path_current}")
        return code == 0

    def ensure_installed_from_url(self, version: str, url: str, progress_callback=None) -> Tuple[bool, str | None]:
        if self.remote_has_version(version):
            return True, None

        remote_dir = self.ensure_version_dir(version)
        runner_path = self._layout.runner_path_version(version)

        tmp_path = Path(tempfile.mktemp(suffix=".tar.gz"))
        try:
            DownloadHelper.download_file(url=url, target=tmp_path, timeout=120, progress_callback=progress_callback)
        except Exception as e:
            return False, f"本地下载 runner 失败: {e}"

        remote_tmp = f"/tmp/auto-clock-runner-{version}.tar.gz"
        try:
            self._ssh.upload_file(str(tmp_path), remote_tmp)
        except Exception as e:
            return False, f"上传 runner 到远端失败: {e}"
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass

        script = (
            "set -e; "
            f"mkdir -p {remote_dir}; "
            f"tar -xzf {remote_tmp} -C {remote_dir}; "
            f"rm -f {remote_tmp}; "
            f"chmod +x {runner_path}; "
            f"test -x {runner_path}"
        )
        code, out, err = self._ssh.exec(script)
        if code == 0:
            return True, None
        msg = (err or out or "").strip() or f"远端解压 runner 失败, code={code}"
        return False, msg

    def set_current(self, version: str) -> Tuple[int, str, str]:
        version_dir = self._layout.version_dir(version)
        current_dir = self._layout.current_dir
        runner_current = self._layout.runner_path_current
        script = (
            f"rm -rf {current_dir} && mkdir -p {self._layout.servers_root} && "
            f"ln -sfn {version_dir} {current_dir} && "
            f"chmod +x {runner_current} && "
            f"test -x {runner_current}"
        )
        return self._ssh.exec(script)

    def run_task(self, task_id: str, headless: bool = False) -> Tuple[int, str, str]:
        cmd = f"{self._layout.runner_path_current} --task_id={task_id}"
        if headless:
            cmd += " --headless"
        return self._ssh.exec(cmd)

    def cron_create(self, task: dict) -> Tuple[int, str, str]:
        app_root = self._layout.app_root
        if app_root.startswith("~") or "${HOME}" in app_root:
            code, out, err = self._ssh.exec("echo $HOME")
            home_dir = (out or "").strip()
            if code != 0 or not home_dir.startswith("/"):
                msg = (err or out or "").strip() or "failed to resolve remote $HOME"
                return 2, "", msg

            if app_root.startswith("~"):
                app_root = home_dir + app_root[1:]
            app_root = app_root.replace("${HOME}", home_dir)

        if not str(app_root).startswith("/"):
            return 2, "", f"remote app_root must be absolute: {app_root}"

        tmp_dir = posixpath.join(app_root, "servers", ".tmp")
        self._ssh.exec(f"mkdir -p {tmp_dir}")
        remote_task_path = posixpath.join(tmp_dir, f"task_{task.get('task_id', 'unknown')}.json")

        # Write via echo to avoid Windows newline issues with sftp text; task json is short.
        payload = json.dumps(task, ensure_ascii=False)
        # Use python on remote? Not guaranteed. So use sftp upload of a temporary file.
        import tempfile
        import os

        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
            f.write(payload)
            local_tmp = f.name
        try:
            self._ssh.upload_file(local_tmp, remote_task_path)
        finally:
            try:
                os.unlink(local_tmp)
            except Exception:
                pass

        cmd = f"{self._layout.runner_path_current} cron_create --task_json_path={remote_task_path}"
        return self._ssh.exec(cmd)

    def cron_delete(self, task_name: str) -> Tuple[int, str, str]:
        cmd = f"{self._layout.runner_path_current} cron_delete --task_name={task_name}"
        return self._ssh.exec(cmd)
