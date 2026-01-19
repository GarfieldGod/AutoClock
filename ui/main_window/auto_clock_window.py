import os
import re
from pathlib import Path

from PyQt5.QtCore import QSize, QTimer, QThread, pyqtSignal

from src.utils.const import AppPath, Key
from src.utils.utils import Utils
from src.utils.log import Log
from ui.template.ui_main_window import MainWindow
from ui.template.ui_page import Container, PageContent
from src.extend.ssh_client import SshClient, SshConfig


class AutoClockWindow(MainWindow):
    save_data = None

    def __init__(self):
        super().__init__(
            title_text="Auto Clock",
            title_desc="--automatically execute the tasks",
            show_max_button=False,
            window_size=QSize(800, 600),
            icon_path=os.path.join(os.path.join(os.path.join(AppPath.UiResourcePath, "image")), "app_icon.png"),
            icon_size=QSize(90, 120)
        )

        self.save_data = {}
        self._local_save_data: dict = {}
        self._local_data_root = AppPath.DataRoot
        self._local_data_json = AppPath.DataJson
        self._local_tasks_json = AppPath.TasksJson
        self._local_runner_result_json = AppPath.RunnerResultJson

        self._remote_connected = False
        self._remote_host = None
        self._remote_home_dir = None
        self._remote_data_root_abs = None
        self._remote_ssh_cfg: SshConfig | None = None

        self._load_local_data_json()
        self.save_data = dict(self._local_save_data)

        self.write_timer = QTimer(self)
        self.write_timer.setInterval(1000)
        self.write_timer.timeout.connect(self.write_data_json)

        self._ssh_status_timer = QTimer(self)
        self._ssh_status_timer.setInterval(3000)
        self._ssh_status_timer.timeout.connect(self.refresh_ssh_status)
        self._ssh_status_timer.start()

        self.refresh_ssh_status()

    def refresh_ssh_status(self):
        enabled = _truthy(self.get_save_data(Key.SshEnabled, False))
        host = _safe_str(self.get_save_data(Key.SshHost, "")).strip()

        if not enabled or not _is_non_empty(host):
            self._remote_connected = False
            self._remote_host = None
            _update_title_bar_status(self, is_local=True, ok=True, host=None)
            return

        ok = bool(self._remote_connected) and (self._remote_host == host)
        if ok:
            _update_title_bar_status(self, is_local=False, ok=True, host=host)
        else:
            # 未手动连接成功时，按未连接状态展示（避免出现失败红灯）
            _update_title_bar_status(self, is_local=True, ok=True, host=None)

    def is_remote_connected(self) -> bool:
        return bool(self._remote_connected)

    def connect_remote_and_reload(self) -> tuple[bool, str | None]:
        enabled = _truthy(self.get_save_data(Key.SshEnabled, False))
        host = _safe_str(self.get_save_data(Key.SshHost, "")).strip()
        username = _safe_str(self.get_save_data(Key.SshUsername, "")).strip()
        password = _safe_str(self.get_save_data(Key.SshPassword, ""))
        use_pkey = _truthy(self.get_save_data(Key.SshUsePrivateKey, False))
        pkey_path = _safe_str(self.get_save_data(Key.SshPrivateKeyPath, "")).strip()

        if not enabled:
            return False, "未启用SSH"
        if not _is_non_empty(host):
            return False, "未填写IP"
        if not _is_non_empty(username):
            return False, "未填写账户名"
        if use_pkey and not _is_non_empty(pkey_path):
            return False, "启用私钥但未选择私钥文件"

        cache_root = Path(self._local_data_root).parent / "remote_cache" / Utils.replace_signs(host)
        cache_data_root = cache_root / "data"
        cache_data_root.mkdir(parents=True, exist_ok=True)

        # 注意：SFTP 不会展开 ~，必须使用绝对路径。
        try:
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

            cfg = SshConfig(
                host=host,
                username=username,
                password=None if use_pkey else password,
                pkey_path=pkey_path if use_pkey else None,
                timeout_sec=10,
            )
            with SshClient(cfg) as ssh:
                code, out, err = ssh.exec("echo ok", timeout_sec=5)
                if code != 0 or "ok" not in out:
                    return False, (err or out or "SSH连接失败").strip()

                # 获取远端 HOME，用于拼接绝对路径给 SFTP
                code, home_out, home_err = ssh.exec("echo $HOME", timeout_sec=5)
                home_dir = (home_out or "").strip()
                if code != 0 or not home_dir.startswith("/"):
                    return False, (home_err or home_out or "无法获取远端 HOME 目录").strip()

                remote_app_root_override = _safe_str(self.get_save_data(Key.SshRemoteAppRoot, "")).strip()
                if remote_app_root_override:
                    if not remote_app_root_override.startswith("/"):
                        return False, f"远端AppRoot必须为绝对路径(以/开头)：{remote_app_root_override}"
                    remote_app_root_abs = remote_app_root_override.rstrip("/")
                else:
                    script = "sh -lc 'base=\"${XDG_DATA_HOME:-$HOME/.local/share}\"; echo \"${base}/auto-clock\"'"
                    code, out, err = ssh.exec(script, timeout_sec=5)
                    remote_app_root_abs = (out or "").strip().rstrip("/")
                    if code != 0 or not remote_app_root_abs.startswith("/"):
                        msg = (err or out or "").strip() or "无法解析远端 AppRoot"
                        return False, msg

                remote_data_root_abs = f"{remote_app_root_abs}/data"

                sftp = ssh.sftp()
                downloaded_data_json = False
                for name in ["data.json", "tasks.json", "runner_result.json"]:
                    try:
                        local_target = cache_data_root / name
                        sftp.get(f"{remote_data_root_abs}/{name}", str(local_target))
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
                        base_data.update(data_any)

                if Key.UserName not in base_data:
                    base_data[Key.UserName] = ""
                if Key.UserPassword not in base_data:
                    base_data[Key.UserPassword] = ""
                if Key.DriverPath not in base_data:
                    base_data[Key.DriverPath] = ""
                if Key.CaptchaRetryTimes not in base_data:
                    base_data[Key.CaptchaRetryTimes] = 5
                if Key.CaptchaToleranceAngle not in base_data:
                    base_data[Key.CaptchaToleranceAngle] = 5
                if Key.AlwaysRetry not in base_data:
                    base_data[Key.AlwaysRetry] = False
                if Key.ShowWebPage not in base_data:
                    base_data[Key.ShowWebPage] = False
                if Key.NotificationEmail not in base_data:
                    base_data[Key.NotificationEmail] = ""
                if Key.SendEmailWhenSuccess not in base_data:
                    base_data[Key.SendEmailWhenSuccess] = False
                if Key.SendEmailWhenFailed not in base_data:
                    base_data[Key.SendEmailWhenFailed] = False
                if Key.LinuxDisplay not in base_data:
                    base_data[Key.LinuxDisplay] = ":0"
                if Key.CheckLinuxCredentialsOnPlanCreate not in base_data:
                    base_data[Key.CheckLinuxCredentialsOnPlanCreate] = True

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
                        ssh.upload_file(str(local_path), f"{remote_data_root_abs}/{remote_name}")
                    except Exception as e:
                        return False, f"初始化远端文件失败：{remote_name}，错误：{e}"

            cache_data_json = cache_data_root / "data.json"
            if not cache_data_json.exists():
                return False, "远端 data.json 不存在或无法下载"

            data = Utils.read_dict_from_json(str(cache_data_json))
            if not isinstance(data, dict):
                return False, "远端数据加载失败：data.json 无法解析"

            AppPath.DataRoot = str(cache_data_root)
            AppPath.DataJson = str(cache_data_root / "data.json")
            AppPath.TasksJson = str(cache_data_root / "tasks.json")
            AppPath.RunnerResultJson = str(cache_data_root / "runner_result.json")

            AppPath.update_remote(remote_app_root_abs)

            self._remote_connected = True
            self._remote_host = host
            self._remote_home_dir = home_dir
            self._remote_data_root_abs = remote_data_root_abs
            self._remote_ssh_cfg = cfg
            self.load_data_json()
            self._reload_pages()
            self.refresh_ssh_status()
            return True, None
        except Exception as e:
            self._remote_connected = False
            self._remote_host = None
            self._remote_home_dir = None
            self._remote_data_root_abs = None
            self._remote_ssh_cfg = None
            self.refresh_ssh_status()
            return False, str(e)

    def disconnect_remote_and_reload(self):
        self._remote_connected = False
        self._remote_host = None
        self._remote_home_dir = None
        self._remote_data_root_abs = None
        self._remote_ssh_cfg = None

        AppPath.clear_remote()

        AppPath.DataRoot = self._local_data_root
        AppPath.DataJson = self._local_data_json
        AppPath.TasksJson = self._local_tasks_json
        AppPath.RunnerResultJson = self._local_runner_result_json

        self.load_data_json()
        self._reload_pages()
        self.refresh_ssh_status()

    def ensure_remote_driver(self) -> tuple[bool, str | None]:
        try:
            if not self.is_remote_connected():
                return False, "SSH未连接"
            if not self._remote_ssh_cfg:
                return False, "SSH配置缺失"
            if not AppPath.RemoteDriversRoot:
                return False, "远端DriversRoot未初始化"

            if not AppPath.RemoteAppRoot:
                return False, "远端AppRoot未初始化"

            runner_path = f"{AppPath.RemoteAppRoot}/servers/current/auto-clock-runner"
            cmd = f"{runner_path} driver_install --driver_root={AppPath.RemoteDriversRoot}"

            with SshClient(self._remote_ssh_cfg) as ssh:
                code, out, err = ssh.exec(cmd)
                if code != 0:
                    msg = (err or out or "").strip() or "远端下载driver失败"
                    return False, msg

                raw = (out or "").strip()
                lines = [ln.strip() for ln in raw.splitlines() if (ln or "").strip()]

                # 兼容 runner stdout 混入日志：优先提取 .wdm 目录下的 msedgedriver 绝对路径
                remote_driver_path = None
                prefer = re.compile(r"^/.*?/\.wdm/drivers/.*?/msedgedriver$")
                for ln in lines:
                    if prefer.match(ln):
                        remote_driver_path = ln
                        break

                if not remote_driver_path:
                    # 次选：任何以 / 开头且以 msedgedriver 结尾的路径
                    for ln in lines:
                        if ln.startswith("/") and ln.endswith("/msedgedriver"):
                            remote_driver_path = ln
                            break

                if not remote_driver_path:
                    # 再次：在行内搜 /.../msedgedriver
                    any_path = re.compile(r"(/[^\s'\"]+/msedgedriver)")
                    for ln in lines:
                        m = any_path.search(ln)
                        if m:
                            remote_driver_path = m.group(1)
                            break

                if not remote_driver_path:
                    tail = lines[-1] if lines else ""
                    return False, f"远端driver路径解析失败：{tail}"

            self.set_save_data(Key.DriverPath, remote_driver_path)
            self.write_data_json()
            return True, remote_driver_path
        except Exception as e:
            return False, str(e)

    def _reload_pages(self):
        try:
            for i in range(self.content.count()):
                w = self.content.widget(i)
                if isinstance(w, AutoClockPageContent):
                    w.set_save_data(self.set_save_data, self.get_save_data)
            self._refresh_dynamic_widgets()
        except Exception:
            pass

    def _refresh_dynamic_widgets(self):
        try:
            # System Plan List 的数据来自 tasks.json，需要显式刷新
            for w in self.findChildren(object):
                try:
                    if w.__class__.__name__ == "TaskListContainer" and hasattr(w, "update_plan_list"):
                        w.update_plan_list()
                except Exception:
                    pass
        except Exception:
            pass

    def load_data_json(self):
        try:
            self.save_data = {}
            if not os.path.exists(AppPath.DataJson):
                return False

            data = Utils.read_dict_from_json(AppPath.DataJson)
            if isinstance(data, dict):
                if self.is_remote_connected():
                    for k in self._ssh_keys():
                        try:
                            data.pop(k, None)
                        except Exception:
                            pass
                self.save_data.update(data)
        except Exception as e:
            print(e)

    def _load_local_data_json(self):
        try:
            self._local_save_data = {}
            if not os.path.exists(self._local_data_json):
                return False

            data = Utils.read_dict_from_json(self._local_data_json)
            if isinstance(data, dict):
                self._local_save_data.update(data)
            return True
        except Exception:
            self._local_save_data = {}
            return False

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

    def write_data_json(self):
        print("write_data_json")
        try:
            # 1) 先落盘本地配置（包含 ssh_*）
            try:
                local_existing = {}
                if os.path.exists(self._local_data_json):
                    existing = Utils.read_dict_from_json(self._local_data_json)
                    if isinstance(existing, dict):
                        local_existing = existing
                local_merged = {}
                local_merged.update(local_existing)
                if isinstance(self._local_save_data, dict):
                    local_merged.update(self._local_save_data)
                Utils.write_dict_to_file(self._local_data_json, local_merged)
            except Exception as e:
                Log.error(f"write local data.json failed: {e}")

            # 2) 再落盘当前数据（本地或远端）；远端时剔除 ssh_* 避免污染
            file_data = {}
            if os.path.exists(AppPath.DataJson):
                existing = Utils.read_dict_from_json(AppPath.DataJson)
                if isinstance(existing, dict):
                    file_data = existing

            merged = {}
            merged.update(file_data)
            if isinstance(self.save_data, dict):
                merged.update(self.save_data)
            if self.is_remote_connected():
                for k in self._ssh_keys():
                    merged.pop(k, None)

            Utils.write_dict_to_file(AppPath.DataJson, merged)

            # 自动同步：连接远端时，把本地 remote_cache/data.json 写回远端 data 目录
            if self.is_remote_connected():
                self._sync_remote_file(local_path=AppPath.DataJson, remote_filename="data.json")
        except Exception as e:
            print(e)
        self.write_timer.stop()

    def _sync_remote_file(self, local_path: str, remote_filename: str) -> bool:
        try:
            if not self.is_remote_connected():
                return False
            if not self._remote_ssh_cfg or not self._remote_data_root_abs:
                return False
            if not os.path.exists(local_path):
                return False

            remote_path = f"{self._remote_data_root_abs}/{remote_filename}"
            with SshClient(self._remote_ssh_cfg) as ssh:
                ssh.upload_file(local_path, remote_path)
            return True
        except Exception as e:
            Log.error(f"sync remote file failed: {remote_filename}, error: {e}")
            return False

    def sync_remote_tasks_json(self) -> bool:
        return self._sync_remote_file(local_path=AppPath.TasksJson, remote_filename="tasks.json")

    def get_save_data(self, key, default=None):
        try:
            if key in self._ssh_keys():
                if not isinstance(self._local_save_data, dict):
                    return default
                return self._local_save_data.get(key, default)
            if not isinstance(self.save_data, dict):
                return default
            return self.save_data.get(key, default)
        except Exception as e:
            print(e)
            return default

    def on_window_close(self):
        self.write_data_json()
        self.close()

    def set_save_data(self, key, value):
        try:
            if key in self._ssh_keys():
                self._local_save_data[key] = value
            else:
                self.save_data[key] = value

            self.write_timer.stop()
            self.write_timer.start()
        except Exception as e:
            print(e)

    def add_page(self, navigation, page):
        super().add_page(navigation, page)

        if self.save_data is not None and isinstance(page, AutoClockPageContent):
            page.set_save_data(self.set_save_data, self.get_save_data)


class _SshProbeThread(QThread):
    result = pyqtSignal(bool)

    def __init__(self, host: str, username: str, password: str | None, use_pkey: bool, pkey_path: str | None):
        super().__init__()
        self._host = host
        self._username = username
        self._password = password
        self._use_pkey = use_pkey
        self._pkey_path = pkey_path

    def run(self):
        ok = False
        try:
            cfg = SshConfig(
                host=self._host,
                username=self._username,
                password=None if self._use_pkey else self._password,
                pkey_path=self._pkey_path if self._use_pkey else None,
                timeout_sec=5,
            )
            with SshClient(cfg) as ssh:
                code, out, _ = ssh.exec("echo ok", timeout_sec=5)
                ok = code == 0 and "ok" in out
        except Exception:
            ok = False
        self.result.emit(ok)


def _update_title_bar_status(window: AutoClockWindow, is_local: bool, ok: bool, host: str | None):
    try:
        if hasattr(window, "title_bar") and hasattr(window.title_bar, "set_connection_status"):
            window.title_bar.set_connection_status(is_local=is_local, ok=ok, host=host)
    except Exception:
        pass


def _safe_str(v):
    return "" if v is None else str(v)


def _truthy(v):
    return bool(v) is True


def _is_non_empty(s: str | None) -> bool:
    return bool(s and str(s).strip())


class AutoClockPageContent(PageContent):
    set_data_func = None
    get_data_func = None
    input_save_widget = []

    def __init__(self, y, x):
        super().__init__(y, x)

    def set_save_data(self, set_func, get_func):
        self.set_data_func = set_func
        self.get_data_func = get_func

        for widget in self.input_save_widget:
            widget.set_value(self.get_data_func(widget.key, widget.default))
            widget.value_changed_func(self.set_data_func)

class AutoClockContainer(Container):
    def __init__(self, x, y):
        super().__init__(x, y)
