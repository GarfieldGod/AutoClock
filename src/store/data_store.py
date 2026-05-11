import os
from pathlib import Path
from typing import Protocol

from src.extend.ssh_client import SshClient, SshConfig
from src.utils.utils import Utils
from src.utils.const import AppPath, Key


class IDataStore(Protocol):
    def read_config(self) -> dict: ...
    def write_config(self, config: dict) -> bool: ...

    def read_tasks(self): ...
    def write_tasks(self, tasks) -> bool: ...

    def read_runner_result(self) -> dict: ...
    def write_runner_result(self, payload: dict) -> bool: ...

    def sync_file(self, local_path: str, remote_filename: str) -> bool: ...


class LocalDataStore:
    def __init__(self):
        pass

    def read_config(self) -> dict:
        data = Utils.read_dict_from_json(AppPath.DataJson)
        return data if isinstance(data, dict) else {}

    def write_config(self, config: dict) -> bool:
        try:
            Utils.write_dict_to_file(AppPath.DataJson, config if isinstance(config, dict) else {})
            return True
        except Exception:
            return False

    def read_tasks(self):
        data = Utils.read_dict_from_json(AppPath.TasksJson)
        return data if isinstance(data, list) else ([] if data is None else data)

    def write_tasks(self, tasks) -> bool:
        try:
            Utils.write_dict_to_file(AppPath.TasksJson, tasks)
            return True
        except Exception:
            return False

    def read_runner_result(self) -> dict:
        data = Utils.read_dict_from_json(AppPath.RunnerResultJson)
        return data if isinstance(data, dict) else {}

    def write_runner_result(self, payload: dict) -> bool:
        try:
            Utils.write_dict_to_file(AppPath.RunnerResultJson, payload if isinstance(payload, dict) else {})
            return True
        except Exception:
            return False

    def sync_file(self, local_path: str, remote_filename: str) -> bool:
        return True


class RemoteDataStore:
    def __init__(
        self,
        ssh_cfg: SshConfig,
        host: str,
        local_data_root: str,
        remote_app_root_override: str | None,
    ):
        self._ssh_cfg = ssh_cfg
        self._host = str(host or "").strip()
        self._local_data_root = str(local_data_root)
        self._remote_app_root_override = str(remote_app_root_override or "").strip()

        self.remote_home_dir: str | None = None
        self.remote_app_root_abs: str | None = None
        self.remote_data_root_abs: str | None = None
        self.cache_data_root: str | None = None

    @staticmethod
    def _default_config() -> dict:
        return {
            Key.UserName: "",
            Key.UserPassword: "",
            Key.DriverPath: "",
            Key.CaptchaRetryTimes: 5,
            Key.CaptchaToleranceAngle: 5,
            Key.AlwaysRetry: False,
            Key.ShowWebPage: False,
            Key.NotificationEmail: "",
            Key.SendEmailWhenSuccess: False,
            Key.SendEmailWhenFailed: False,
            Key.LinuxDisplay: ":0",
            Key.CheckLinuxCredentialsOnPlanCreate: True,
        }

    @staticmethod
    def _ssh_keys() -> set[str]:
        return {
            Key.SshEnabled,
            Key.SshHost,
            Key.SshUsername,
            Key.SshPassword,
            Key.SshUsePrivateKey,
            Key.SshPrivateKeyPath,
            Key.SshServerPlatform,
            Key.SshRemoteAppRoot,
        }

    @staticmethod
    def _strip_ssh_keys(data: dict) -> dict:
        if not isinstance(data, dict):
            return {}
        cleaned = dict(data)
        for k in RemoteDataStore._ssh_keys():
            cleaned.pop(k, None)
        return cleaned

    def bootstrap(self) -> tuple[bool, str | None]:
        try:
            cache_root = Path(self._local_data_root).parent / "remote_cache" / Utils.replace_signs(self._host)
            cache_data_root = cache_root / "data"
            cache_data_root.mkdir(parents=True, exist_ok=True)
            self.cache_data_root = str(cache_data_root)

            def _ensure_json_file(local_target: Path, default_obj, expected_type) -> tuple[bool, bool, str | None]:
                try:
                    need_upload = False
                    if not local_target.exists() or local_target.stat().st_size == 0:
                        Utils.write_dict_to_file(str(local_target), default_obj)
                        return True, True, None

                    data_any = Utils.read_dict_from_json(str(local_target))
                    if not isinstance(data_any, expected_type):
                        Utils.write_dict_to_file(str(local_target), default_obj)
                        need_upload = True
                    return True, need_upload, None
                except Exception as e:
                    return False, False, str(e)

            with SshClient(self._ssh_cfg) as ssh:
                code, home_out, home_err = ssh.exec("echo $HOME", timeout_sec=5)
                home_dir = (home_out or "").strip()
                if code != 0 or not home_dir.startswith("/"):
                    return False, (home_err or home_out or "无法获取远端 HOME 目录").strip()
                self.remote_home_dir = home_dir

                if self._remote_app_root_override:
                    if not self._remote_app_root_override.startswith("/"):
                        return False, f"远端AppRoot必须为绝对路径(以/开头)：{self._remote_app_root_override}"
                    remote_app_root_abs = self._remote_app_root_override.rstrip("/")
                else:
                    script = "sh -lc 'base=\"${XDG_DATA_HOME:-$HOME/.local/share}\"; echo \"${base}/auto-clock\"'"
                    code, out, err = ssh.exec(script, timeout_sec=5)
                    remote_app_root_abs = (out or "").strip().rstrip("/")
                    if code != 0 or not remote_app_root_abs.startswith("/"):
                        msg = (err or out or "").strip() or "无法解析远端 AppRoot"
                        return False, msg

                self.remote_app_root_abs = remote_app_root_abs
                self.remote_data_root_abs = f"{remote_app_root_abs}/data"

                sftp = ssh.sftp()
                downloaded_data_json = False
                for name in ["data.json", "tasks.json", "runner_result.json"]:
                    try:
                        local_target = cache_data_root / name
                        sftp.get(f"{self.remote_data_root_abs}/{name}", str(local_target))
                        if name == "data.json":
                            downloaded_data_json = True
                        if local_target.exists() and local_target.stat().st_size == 0:
                            return False, f"下载远端文件为空：{name}，本地缓存：{local_target}"
                    except FileNotFoundError:
                        try:
                            local_target = cache_data_root / name
                            if local_target.exists():
                                local_target.unlink()
                        except Exception:
                            pass
                    except Exception as e:
                        return False, f"下载远端文件失败：{name}，错误：{e}"

                base_data = {}
                cache_data_json = cache_data_root / "data.json"
                if downloaded_data_json and cache_data_json.exists() and cache_data_json.stat().st_size > 0:
                    data_any = Utils.read_dict_from_json(str(cache_data_json))
                    if isinstance(data_any, dict):
                        base_data.update(self._strip_ssh_keys(data_any))

                defaults = self._default_config()
                for k, v in defaults.items():
                    if k not in base_data:
                        base_data[k] = v

                init_targets: list[tuple[str, Path]] = []

                ok3, need_up, err3 = _ensure_json_file(cache_data_root / "data.json", base_data, dict)
                if not ok3:
                    return False, f"初始化本地缓存文件失败：data.json，错误：{err3}"
                if need_up:
                    init_targets.append(("data.json", cache_data_root / "data.json"))

                ok3, need_up, err3 = _ensure_json_file(cache_data_root / "tasks.json", [], list)
                if not ok3:
                    return False, f"初始化本地缓存文件失败：tasks.json，错误：{err3}"
                if need_up:
                    init_targets.append(("tasks.json", cache_data_root / "tasks.json"))

                ok3, need_up, err3 = _ensure_json_file(cache_data_root / "runner_result.json", {}, dict)
                if not ok3:
                    return False, f"初始化本地缓存文件失败：runner_result.json，错误：{err3}"
                if need_up:
                    init_targets.append(("runner_result.json", cache_data_root / "runner_result.json"))

                for remote_name, local_path in init_targets:
                    try:
                        ssh.upload_file(str(local_path), f"{self.remote_data_root_abs}/{remote_name}")
                    except Exception as e:
                        return False, f"初始化远端文件失败：{remote_name}，错误：{e}"

            return True, None
        except Exception as e:
            return False, str(e)

    def read_config(self) -> dict:
        data = Utils.read_dict_from_json(AppPath.DataJson)
        return data if isinstance(data, dict) else {}

    def write_config(self, config: dict) -> bool:
        try:
            Utils.write_dict_to_file(AppPath.DataJson, self._strip_ssh_keys(config if isinstance(config, dict) else {}))
            self.sync_file(AppPath.DataJson, "data.json")
            return True
        except Exception:
            return False

    def read_tasks(self):
        data = Utils.read_dict_from_json(AppPath.TasksJson)
        return data if isinstance(data, list) else ([] if data is None else data)

    def write_tasks(self, tasks) -> bool:
        try:
            Utils.write_dict_to_file(AppPath.TasksJson, tasks)
            self.sync_file(AppPath.TasksJson, "tasks.json")
            return True
        except Exception:
            return False

    def read_runner_result(self) -> dict:
        data = Utils.read_dict_from_json(AppPath.RunnerResultJson)
        return data if isinstance(data, dict) else {}

    def write_runner_result(self, payload: dict) -> bool:
        try:
            Utils.write_dict_to_file(AppPath.RunnerResultJson, payload if isinstance(payload, dict) else {})
            self.sync_file(AppPath.RunnerResultJson, "runner_result.json")
            return True
        except Exception:
            return False

    def sync_file(self, local_path: str, remote_filename: str) -> bool:
        try:
            if not self.remote_data_root_abs:
                return False
            if not os.path.exists(local_path):
                return False
            remote_path = f"{self.remote_data_root_abs}/{remote_filename}"
            with SshClient(self._ssh_cfg) as ssh:
                ssh.upload_file(local_path, remote_path)
            return True
        except Exception:
            return False
