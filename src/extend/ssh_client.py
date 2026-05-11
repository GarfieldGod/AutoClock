import posixpath
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import paramiko


@dataclass
class SshConfig:
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    pkey_path: Optional[str] = None
    timeout_sec: int = 20


class SshClient:
    def __init__(self, config: SshConfig):
        self._config = config
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def connect(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        pkey = None
        if self._config.pkey_path:
            pkey = paramiko.RSAKey.from_private_key_file(self._config.pkey_path)

        client.connect(
            hostname=self._config.host,
            port=self._config.port,
            username=self._config.username,
            password=self._config.password,
            pkey=pkey,
            timeout=self._config.timeout_sec,
        )

        self._client = client
        self._sftp = None

    def close(self):
        if self._sftp is not None:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def exec(self, command: str, timeout_sec: Optional[int] = None) -> Tuple[int, str, str]:
        if self._client is None:
            raise RuntimeError("SSH client not connected")

        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout_sec or self._config.timeout_sec)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        code = stdout.channel.recv_exit_status()
        return code, out, err

    def sftp(self) -> paramiko.SFTPClient:
        if self._client is None:
            raise RuntimeError("SSH client not connected")
        if self._sftp is None:
            self._sftp = self._client.open_sftp()
        return self._sftp

    def ensure_dir(self, remote_dir: str):
        sftp = self.sftp()
        remote_dir = remote_dir.rstrip("/")
        if not remote_dir:
            return

        parts = remote_dir.split("/")
        path = ""
        for part in parts:
            if not part:
                continue
            path = f"{path}/{part}" if path else f"/{part}"
            try:
                sftp.stat(path)
            except FileNotFoundError:
                sftp.mkdir(path)

    def exists(self, remote_path: str) -> bool:
        sftp = self.sftp()
        try:
            sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def upload_file(self, local_path: str, remote_path: str):
        sftp = self.sftp()
        remote_dir = posixpath.dirname(remote_path)
        self.ensure_dir(remote_dir)
        sftp.put(local_path, remote_path)

    def upload_dir(self, local_dir: str, remote_dir: str):
        import os

        remote_dir = remote_dir.rstrip("/")
        self.ensure_dir(remote_dir)

        for root, dirs, files in os.walk(local_dir):
            rel = os.path.relpath(root, local_dir).replace("\\", "/")
            target_root = remote_dir if rel == "." else f"{remote_dir}/{rel}"
            self.ensure_dir(target_root)

            for d in dirs:
                self.ensure_dir(f"{target_root}/{d}")
            for f in files:
                self.upload_file(os.path.join(root, f), f"{target_root}/{f}")

    def wait_file(self, remote_path: str, timeout_sec: int = 60, poll_interval_sec: float = 0.5) -> bool:
        start = time.time()
        while time.time() - start < timeout_sec:
            if self.exists(remote_path):
                return True
            time.sleep(poll_interval_sec)
        return False
