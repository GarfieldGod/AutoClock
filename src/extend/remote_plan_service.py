from __future__ import annotations

from typing import Callable

from src.extend.remote_linux_runner import RemoteLinuxRunner, RemoteLinuxLayout
from src.extend.ssh_client import SshClient, SshConfig
from src.utils.const import WebPath, Key
from src.utils.utils import Utils


class RemotePlanService:
    def __init__(
        self,
        ssh_cfg_getter: Callable[[], SshConfig | None],
        remote_app_root_getter: Callable[[], str | None] | None = None,
    ):
        self._ssh_cfg_getter = ssh_cfg_getter
        self._remote_app_root_getter = remote_app_root_getter
        self._ready_key: tuple[str, str, str] | None = None

    @staticmethod
    def _normalize_error(*parts, default: str) -> str:
        for part in parts:
            text = str(part or "").strip()
            if text:
                return text
        return default

    def _create_remote_runner(self, ssh: SshClient) -> RemoteLinuxRunner:
        app_root = ""
        if self._remote_app_root_getter is not None:
            app_root = str(self._remote_app_root_getter() or "").strip()
        if app_root.startswith("/"):
            return RemoteLinuxRunner(ssh, layout=RemoteLinuxLayout(app_root=app_root))
        return RemoteLinuxRunner(ssh)

    @staticmethod
    def _cache_key(cfg: SshConfig, remote: RemoteLinuxRunner, version: str) -> tuple[str, str, str]:
        host = str(getattr(cfg, "host", "") or "").strip()
        app_root = str(remote.layout.app_root or "").strip()
        return host, app_root, version

    @staticmethod
    def _runner_current_exists(remote: RemoteLinuxRunner) -> bool:
        return remote.current_runner_exists()

    @staticmethod
    def _exception_text(e: Exception) -> str:
        text = str(e or "").strip()
        if text:
            if "timeout" in text.lower():
                return "SSH/网络超时，请检查远端连通性或代理设置"
            return text
        return f"{type(e).__name__}"

    def _ensure_runner_ready(self, cfg: SshConfig, remote: RemoteLinuxRunner) -> tuple[bool, str | None]:
        version = Utils.get_app_version_from_config_json(default="")
        if not version:
            return False, "无法获取版本号"

        key = self._cache_key(cfg, remote, version)
        if self._ready_key == key and self._runner_current_exists(remote):
            return True, None

        if self._runner_current_exists(remote):
            self._ready_key = key
            return True, None

        if remote.remote_has_version(version):
            code, out, err2 = remote.set_current(version)
            if code == 0 and self._runner_current_exists(remote):
                self._ready_key = key
                return True, None
            if code != 0:
                return False, self._normalize_error(err2, out, default="远端 set_current 失败")

        url = WebPath.LinuxRunnerDownloadUrlTemplate.format(version=version)
        ok2, err = remote.ensure_installed_from_url(version=version, url=url)
        if not ok2:
            self._ready_key = None
            return False, self._normalize_error(err, default="远端安装 linux-runner 失败")

        code, out, err2 = remote.set_current(version)
        if code != 0:
            self._ready_key = None
            return False, self._normalize_error(err2, out, default="远端 set_current 失败")

        self._ready_key = key

        return True, None

    def cron_create(self, task: dict) -> tuple[bool, str | None]:
        try:
            cfg = self._ssh_cfg_getter()
            if not cfg:
                return False, "SSH配置缺失"

            with SshClient(cfg) as ssh:
                remote = self._create_remote_runner(ssh)
                ok2, err = self._ensure_runner_ready(cfg, remote)
                if not ok2:
                    return False, self._normalize_error(err, default="远端runner初始化失败")

                code, out, err2 = remote.cron_create(task)
                if code != 0:
                    return False, self._normalize_error(err2, out, default="远端创建 crontab 失败")

            return True, None
        except Exception as e:
            return False, self._normalize_error(self._exception_text(e), default="远端创建计划任务异常")

    def cron_delete(self, task_names) -> tuple[bool, str | None]:
        try:
            cfg = self._ssh_cfg_getter()
            if not cfg:
                return False, "SSH配置缺失"

            if task_names is None:
                return False, "task_names为空"

            if isinstance(task_names, str):
                task_names = [task_names]

            with SshClient(cfg) as ssh:
                remote = self._create_remote_runner(ssh)
                ok2, err = self._ensure_runner_ready(cfg, remote)
                if not ok2:
                    return False, self._normalize_error(err, default="远端runner初始化失败")

                for name in task_names:
                    if not name:
                        continue
                    code, out, err2 = remote.cron_delete(name)
                    if code != 0:
                        return False, self._normalize_error(err2, out, default="远端删除 crontab 失败")

            return True, None
        except Exception as e:
            return False, self._normalize_error(self._exception_text(e), default="远端删除计划任务异常")

    @staticmethod
    def task_names_from_plan(task: dict):
        plan_name = task.get(Key.SystemPlanName)
        if task.get(Key.TriggerType) == Key.Multiple and isinstance(plan_name, dict):
            return [plan_name.get(k) for k in plan_name]
        return plan_name
