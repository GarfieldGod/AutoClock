from __future__ import annotations

from typing import Callable

from src.extend.remote_linux_runner import RemoteLinuxRunner
from src.extend.ssh_client import SshClient, SshConfig
from src.utils.const import WebPath, Key
from src.utils.utils import Utils


class RemotePlanService:
    def __init__(self, ssh_cfg_getter: Callable[[], SshConfig | None]):
        self._ssh_cfg_getter = ssh_cfg_getter

    def _ensure_runner_ready(self, remote: RemoteLinuxRunner) -> tuple[bool, str | None]:
        version = Utils.get_app_version_from_config_json(default="")
        if not version:
            return False, "无法获取版本号"

        url = WebPath.LinuxRunnerDownloadUrlTemplate.format(version=version)
        ok2, err = remote.ensure_installed_from_url(version=version, url=url)
        if not ok2:
            return False, err or "远端安装 linux-runner 失败"

        code, out, err2 = remote.set_current(version)
        if code != 0:
            return False, (err2 or out or "").strip() or "远端 set_current 失败"

        return True, None

    def cron_create(self, task: dict) -> tuple[bool, str | None]:
        cfg = self._ssh_cfg_getter()
        if not cfg:
            return False, "SSH配置缺失"

        with SshClient(cfg) as ssh:
            remote = RemoteLinuxRunner(ssh)
            ok2, err = self._ensure_runner_ready(remote)
            if not ok2:
                return False, err

            code, out, err2 = remote.cron_create(task)
            if code != 0:
                return False, (err2 or out or "").strip() or "远端创建 crontab 失败"

        return True, None

    def cron_delete(self, task_names) -> tuple[bool, str | None]:
        cfg = self._ssh_cfg_getter()
        if not cfg:
            return False, "SSH配置缺失"

        if task_names is None:
            return False, "task_names为空"

        if isinstance(task_names, str):
            task_names = [task_names]

        with SshClient(cfg) as ssh:
            remote = RemoteLinuxRunner(ssh)
            ok2, err = self._ensure_runner_ready(remote)
            if not ok2:
                return False, err

            for name in task_names:
                if not name:
                    continue
                code, out, err2 = remote.cron_delete(name)
                if code != 0:
                    return False, (err2 or out or "").strip() or "远端删除 crontab 失败"

        return True, None

    @staticmethod
    def task_names_from_plan(task: dict):
        plan_name = task.get(Key.SystemPlanName)
        if task.get(Key.TriggerType) == Key.Multiple and isinstance(plan_name, dict):
            return [plan_name.get(k) for k in plan_name]
        return plan_name
