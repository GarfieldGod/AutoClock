import os
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
        self._local_data_root = AppPath.DataRoot
        self._local_data_json = AppPath.DataJson
        self._local_tasks_json = AppPath.TasksJson
        self._local_runner_result_json = AppPath.RunnerResultJson

        self._remote_connected = False
        self._remote_host = None
        self._remote_home_dir = None
        self._remote_data_root_abs = None
        self._remote_ssh_cfg: SshConfig | None = None
        self.load_data_json()

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

                remote_root_abs = f"{home_dir}/.local/share/auto-clock/data"

                sftp = ssh.sftp()
                for name in ["data.json", "tasks.json", "runner_result.json"]:
                    try:
                        local_target = cache_data_root / name
                        sftp.get(f"{remote_root_abs}/{name}", str(local_target))
                        if local_target.exists() and local_target.stat().st_size == 0:
                            return False, f"下载远端文件为空：{name}，本地缓存：{local_target}"
                    except FileNotFoundError:
                        pass
                    except Exception as e:
                        return False, f"下载远端文件失败：{name}，错误：{e}"

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

            self._remote_connected = True
            self._remote_host = host
            self._remote_home_dir = home_dir
            self._remote_data_root_abs = remote_root_abs
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

        AppPath.DataRoot = self._local_data_root
        AppPath.DataJson = self._local_data_json
        AppPath.TasksJson = self._local_tasks_json
        AppPath.RunnerResultJson = self._local_runner_result_json

        self.load_data_json()
        self._reload_pages()
        self.refresh_ssh_status()

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
            if not os.path.exists(AppPath.DataJson):
                self.save_data = {}
                return False

            data = Utils.read_dict_from_json(AppPath.DataJson)
            if isinstance(data, dict):
                self.save_data.update(data)
        except Exception as e:
            print(e)

    def write_data_json(self):
        print("write_data_json")
        try:
            file_data = {}
            if os.path.exists(AppPath.DataJson):
                existing = Utils.read_dict_from_json(AppPath.DataJson)
                if isinstance(existing, dict):
                    file_data = existing

            merged = {}
            merged.update(file_data)
            if isinstance(self.save_data, dict):
                merged.update(self.save_data)

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
