import json
import posixpath
from dataclasses import dataclass
from typing import Optional, Tuple

from src.extend.ssh_client import SshClient


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

    def ensure_installed_from_url(self, version: str, url: str) -> Tuple[bool, str | None]:
        if self.remote_has_version(version):
            return True, None

        remote_dir = self.ensure_version_dir(version)
        runner_path = self._layout.runner_path_version(version)

        script = (
            "set -e; "
            f"mkdir -p {remote_dir}; "
            "tmp=\"$(mktemp)\"; "
            "cleanup() { rm -f \"$tmp\"; }; trap cleanup EXIT; "
            "if command -v curl >/dev/null 2>&1; then "
            f"curl -fL --connect-timeout 10 --max-time 120 --retry 3 --retry-delay 1 -o \"$tmp\" '{url}'; "
            "elif command -v wget >/dev/null 2>&1; then "
            f"wget --timeout=120 --tries=3 -O \"$tmp\" '{url}'; "
            "else echo 'curl/wget not found' 1>&2; exit 2; fi; "
            "tar -tzf \"$tmp\" >/dev/null 2>&1 || (echo 'downloaded file is not a valid tar.gz' 1>&2; exit 3); "
            f"tar -xzf \"$tmp\" -C {remote_dir}; "
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
