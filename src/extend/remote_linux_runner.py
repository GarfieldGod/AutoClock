import json
import posixpath
from dataclasses import dataclass
from typing import Optional, Tuple

from src.extend.ssh_client import SshClient


@dataclass
class RemoteLinuxLayout:
    app_root: str = "~/.local/share/auto-clock"

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

    def ensure_installed_from_url(self, version: str, url: str) -> Tuple[bool, str | None]:
        if self.remote_has_version(version):
            return True, None

        remote_dir = self.ensure_version_dir(version)
        runner_path = self._layout.runner_path_version(version)

        script = (
            "set -e; "
            f"mkdir -p {remote_dir}; "
            "tmp=\"$(mktemp)\"; "
            "if command -v curl >/dev/null 2>&1; then "
            f"curl -L -o \"$tmp\" '{url}'; "
            "elif command -v wget >/dev/null 2>&1; then "
            f"wget -O \"$tmp\" '{url}'; "
            "else echo 'curl/wget not found' 1>&2; exit 2; fi; "
            f"tar -xzf \"$tmp\" -C {remote_dir}; "
            "rm -f \"$tmp\"; "
            f"chmod +x {runner_path}; "
            f"test -x {runner_path}"
        )
        code, out, err = self._ssh.exec(script)
        if code == 0:
            return True, None
        msg = (err or out or "").strip() or f"install linux-runner failed with code {code}"
        return False, msg

    def set_current(self, version: str) -> Tuple[int, str, str]:
        runner = self._layout.runner_path_version(version)
        cmd = f"{runner} set_current --version={version}"
        return self._ssh.exec(cmd)

    def run_task(self, task_id: str, headless: bool = False) -> Tuple[int, str, str]:
        cmd = f"{self._layout.runner_path_current} --task_id={task_id}"
        if headless:
            cmd += " --headless"
        return self._ssh.exec(cmd)

    def cron_create(self, task: dict) -> Tuple[int, str, str]:
        tmp_dir = posixpath.join(self._layout.app_root, "servers", ".tmp")
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
