import os
import re
from pathlib import Path

from PyQt5.QtCore import QSize, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog

from src.utils.const import AppPath, Key
from src.utils.utils import Utils
from src.utils.log import Log
from src.utils.update import VersionCheckThread
from ui.template.ui_main_window import MainWindow
from ui.template.ui_page import Container, PageContent
from src.extend.ssh_client import SshClient, SshConfig
from src.store.settings_store import SettingsStore
from src.store.data_store import LocalDataStore, RemoteDataStore, IDataStore
from src.extend.remote_plan_service import RemotePlanService


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
        self._settings = SettingsStore()
        self._settings.load()
        self._update_threads = []

        self._local_data_root = AppPath.DataRoot
        self._local_data_json = AppPath.DataJson
        self._local_tasks_json = AppPath.TasksJson
        self._local_runner_result_json = AppPath.RunnerResultJson

        self.load_data_json()
        self._check_update_on_startup()

        self._remote_connected = False
        self._remote_host = None
        self._remote_home_dir = None
        self._remote_data_root_abs = None
        self._remote_ssh_cfg: SshConfig | None = None

        self._remote_plan_service: RemotePlanService | None = None

        self._data_store: IDataStore = LocalDataStore()

        self.write_timer = QTimer(self)
        self.write_timer.setInterval(1000)
        self.write_timer.timeout.connect(self.write_data_json)

        self._ssh_status_timer = QTimer(self)
        self._ssh_status_timer.setInterval(3000)
        self._ssh_status_timer.timeout.connect(self.refresh_ssh_status)
        self._ssh_status_timer.start()

        self.refresh_ssh_status()

    def _check_update_on_startup(self):
        try:
            pref = self.get_save_data(Key.CheckUpdateOnStartup, "每次启动都检查")
            if pref != "每次启动都检查":
                return
            self.check_app_update(manual=False)
        except Exception:
            pass

    def check_app_update(self, manual: bool = True):
        try:
            thread = VersionCheckThread()
            self._update_threads.append(thread)
            thread.check_finished.connect(lambda ok, ver: self._on_update_check_done(ok, ver, manual))
            thread.finished.connect(lambda t=thread: self._update_threads.remove(t) if t in self._update_threads else None)
            thread.finished.connect(thread.deleteLater)
            thread.start()
        except Exception as e:
            if manual:
                from src.ui.ui_message import MessageBox
                MessageBox(f"检查更新失败：{e}")

    def _on_update_check_done(self, ok, ver, manual: bool = False):
        try:
            if ok and ver and ver.get("local") and ver.get("remote"):
                from src.ui.ui_message import MessageBox
                import webbrowser
                from src.utils.const import WebPath
                is_update = MessageBox(
                    f"检测到新版本:\n\n"
                    f"本地: {ver.get('local')}  最新: {ver.get('remote')}\n\n"
                    f"是否前往下载？",
                    need_check=True, message_only=False)
                if is_update.exec_() == QDialog.Accepted:
                    webbrowser.open_new(WebPath.AppProjectPath)
            elif manual and ver and ver.get("local") and ver.get("remote"):
                from src.ui.ui_message import MessageBox
                MessageBox(f"当前已经是最新版本：{ver.get('local')}")
            elif manual:
                from src.ui.ui_message import MessageBox
                MessageBox("版本检测失败，无法获取版本信息")
        except Exception:
            pass

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

        try:
            cfg = SshConfig(
                host=host,
                username=username,
                password=None if use_pkey else password,
                pkey_path=pkey_path if use_pkey else None,
                timeout_sec=10,
            )
            remote_app_root_override = _safe_str(self.get_save_data(Key.SshRemoteAppRoot, "")).strip()
            store = RemoteDataStore(
                ssh_cfg=cfg,
                host=host,
                local_data_root=self._local_data_root,
                remote_app_root_override=remote_app_root_override,
            )
            ok2, err2 = store.bootstrap()
            if not ok2:
                return False, err2
            if not store.cache_data_root:
                return False, "远端缓存目录初始化失败"
            if not store.remote_app_root_abs or not store.remote_data_root_abs:
                return False, "远端目录初始化失败"

            AppPath.DataRoot = str(store.cache_data_root)
            AppPath.DataJson = str(Path(store.cache_data_root) / "data.json")
            AppPath.TasksJson = str(Path(store.cache_data_root) / "tasks.json")
            AppPath.RunnerResultJson = str(Path(store.cache_data_root) / "runner_result.json")

            AppPath.update_remote(store.remote_app_root_abs)

            self._remote_connected = True
            self._remote_host = host
            self._remote_home_dir = store.remote_home_dir
            self._remote_data_root_abs = store.remote_data_root_abs
            self._remote_ssh_cfg = cfg
            self._data_store = store

            self._remote_plan_service = RemotePlanService(lambda: self._remote_ssh_cfg)
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
            self._remote_plan_service = None
            self.refresh_ssh_status()
            return False, str(e)

    def disconnect_remote_and_reload(self):
        self._remote_connected = False
        self._remote_host = None
        self._remote_home_dir = None
        self._remote_data_root_abs = None
        self._remote_ssh_cfg = None

        self._remote_plan_service = None

        self._data_store = LocalDataStore()

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
            try:
                self._settings.save()
            except Exception:
                pass

            # 再落盘当前数据（本地或远端）；远端时剔除 ssh_* 避免污染
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
                self._data_store.sync_file(local_path=AppPath.DataJson, remote_filename="data.json")
        except Exception as e:
            print(e)
        self.write_timer.stop()

    def sync_remote_tasks_json(self) -> bool:
        return self._data_store.sync_file(local_path=AppPath.TasksJson, remote_filename="tasks.json")

    @property
    def data_store(self) -> IDataStore:
        return self._data_store

    @property
    def remote_plan_service(self) -> RemotePlanService | None:
        return self._remote_plan_service

    def write_tasks_list(self, tasks) -> bool:
        return self._data_store.write_tasks(tasks)

    def read_tasks_list(self):
        return self._data_store.read_tasks()

    def get_save_data(self, key, default=None):
        try:
            if key in self._ssh_keys():
                return self._settings.get(key, default)
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
                self._settings.set(key, value)
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
