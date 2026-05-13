import os
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from PyQt5.QtCore import QSize, QTimer, QThread, QEventLoop, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QMessageBox,
                             QProgressDialog, QPushButton, QVBoxLayout, QApplication)

from src.utils.const import AppPath, Key, WebPath
from src.utils.utils import Utils
from src.utils.log import Log
from src.utils.update import VersionCheckThread, AppUpdateInstallThread
from ui.template.ui_main_window import MainWindow
from ui.template.ui_page import Container, PageContent
from src.extend.ssh_client import SshClient, SshConfig
from src.store.settings_store import SettingsStore
from src.store.data_store import LocalDataStore, RemoteDataStore, IDataStore
from src.extend.remote_plan_service import RemotePlanService
from src.extend.remote_linux_runner import RemoteLinuxRunner, RemoteLinuxLayout


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
        self._update_install_thread: AppUpdateInstallThread | None = None
        self._update_progress_dialog: QProgressDialog | None = None
        self._update_cancelled = False
        self._pending_update_bat: Path | None = None

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
        self._check_update_on_startup()

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

    def closeEvent(self, event):
        if self._pending_update_bat is not None and self._pending_update_bat.exists():
            if sys.platform == "win32":
                subprocess.Popen(
                    [str(self._pending_update_bat)],
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                subprocess.Popen(
                    [str(self._pending_update_bat)],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        event.accept()

    def _check_update_on_startup(self):
        try:
            pref = self.get_save_data(Key.CheckUpdateOnStartup, "on_startup")
            if pref != "on_startup":
                return
            self.check_app_update(manual=False)
        except Exception:
            pass

    def check_app_update(self, manual: bool = True):
        if self._update_threads:
            return
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
                MessageBox(f"Check update failed: {e}")

    def _on_update_check_done(self, ok, ver, manual: bool = False):
        try:
            if ok and ver and ver.get("local") and ver.get("remote"):
                self._show_update_actions(ver)
            elif manual and ver and ver.get("local") and ver.get("remote"):
                from src.ui.ui_message import MessageBox
                MessageBox(f"You are on the latest version: {ver.get('local')}")
            elif manual:
                from src.ui.ui_message import MessageBox
                MessageBox("Version check failed, unable to retrieve version info.")
        except Exception:
            pass

    @staticmethod
    def _release_page(version: str) -> str:
        from src.utils.const import WebPath
        return WebPath.AppReleasePageTemplate.format(version=str(version or "").strip())

    @staticmethod
    def _manual_download_url(version: str) -> str:
        from src.utils.const import WebPath
        version = str(version or "").strip()
        if os.name == "nt":
            return WebPath.AppWindowsDownloadUrlTemplate.format(version=version)
        return WebPath.AppLinuxDownloadUrlTemplate.format(version=version)

    def _show_update_actions(self, ver: dict):
        local_ver = str(ver.get("local") or "")
        remote_ver = str(ver.get("remote") or "")

        dialog = QDialog(self)
        dialog.setWindowTitle("Update Available")
        dialog.setFixedSize(400, 200)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setStyleSheet("QDialog { background-color: #ffffff; }")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 22, 28, 18)
        layout.setSpacing(0)

        icon_label = QLabel("\u2b06")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 30px;")
        layout.addWidget(icon_label)
        layout.addSpacing(8)

        subtitle = QLabel("A new version is available")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            "font-family: 'Microsoft YaHei', 'SimHei', sans-serif;"
            "font-size: 14px; font-weight: bold; color: #1a1a1a;"
        )
        layout.addWidget(subtitle)
        layout.addSpacing(6)

        info = QLabel(
            f"Current:  {local_ver}\n"
            f"Latest:   {remote_ver}"
        )
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet(
            "font-family: 'Microsoft YaHei', 'SimHei', sans-serif;"
            "font-size: 12px; color: #6b7280;"
        )
        layout.addWidget(info)
        layout.addSpacing(16)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(90, 34)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #6b7280;
                border: 1px solid #d1d5db; border-radius: 6px;
                font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #f3f4f6; color: #374151; }
            QPushButton:pressed { background: #e5e7eb; }
        """)

        manual_btn = QPushButton("Manual")
        manual_btn.setFixedSize(90, 34)
        manual_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #2563eb;
                border: 1px solid #2563eb; border-radius: 6px;
                font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #eff6ff; }
            QPushButton:pressed { background: #dbeafe; }
        """)

        auto_btn = QPushButton("Auto")
        auto_btn.setFixedSize(90, 34)
        auto_btn.setStyleSheet("""
            QPushButton {
                background: #2563eb; color: white;
                border: none; border-radius: 6px;
                font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:pressed { background: #1e40af; }
        """)

        auto_btn.clicked.connect(dialog.accept)
        manual_btn.clicked.connect(lambda: dialog.done(2))
        cancel_btn.clicked.connect(dialog.reject)

        btn_row.addWidget(auto_btn)
        btn_row.addWidget(manual_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        result = dialog.exec_()
        dialog.deleteLater()

        if result == QDialog.Accepted:
            self._run_auto_update_install(remote_ver)
        elif result == 2:
            webbrowser.open_new(self._manual_download_url(remote_ver))

    def _run_auto_update_install(self, remote_ver: str):
        remote_ver = str(remote_ver or "").strip()
        if not remote_ver:
            from src.ui.ui_message import MessageBox
            MessageBox("Version number is empty, cannot auto-update.")
            return

        if self._update_install_thread is not None and self._update_install_thread.isRunning():
            from src.ui.ui_message import MessageBox
            MessageBox("An update task is already in progress.")
            return

        self._update_cancelled = False

        dialog = QProgressDialog("Preparing to download update package...", None, 0, 100, self)
        dialog.setWindowTitle("Auto Update")
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setValue(0)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.show()
        self._update_progress_dialog = dialog

        thread = AppUpdateInstallThread(remote_ver)
        self._update_install_thread = thread

        def _on_canceled():
            self._update_cancelled = True
            if self._update_progress_dialog is not None:
                self._update_progress_dialog.hide()
                self._update_progress_dialog.deleteLater()
                self._update_progress_dialog = None

            if self._update_install_thread is not None and self._update_install_thread.isRunning():
                self._update_install_thread.terminate()
                self._update_install_thread.wait(2000)
                self._update_install_thread = None

            updater_dir = Path(AppPath.UpdaterRoot)
            platform_name = "windows" if os.name == "nt" else "linux"
            target_dir = updater_dir / f"auto-clock-{remote_ver}-{platform_name}"
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            Log.info(f"Auto-update cancelled by user, cleaned: {target_dir}")

        dialog.canceled.connect(_on_canceled)

        def _on_progress(percent: int, message: str):
            if self._update_cancelled:
                return
            if self._update_progress_dialog is None:
                return
            self._update_progress_dialog.setLabelText(message or "Updating...")
            self._update_progress_dialog.setValue(max(0, min(100, int(percent))))

        def _on_finished(ok: bool, message: str, launch_path: str):
            if self._update_cancelled:
                self._update_install_thread = None
                return

            if self._update_progress_dialog is not None:
                self._update_progress_dialog.setValue(100)
                self._update_progress_dialog.hide()
                self._update_progress_dialog.deleteLater()
                self._update_progress_dialog = None

            self._update_install_thread = None

            if not ok:
                from src.ui.ui_message import MessageBox
                MessageBox(f"Auto-update failed: {message}")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("Update Complete")
            dialog.setFixedSize(380, 170)
            dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            dialog.setStyleSheet("QDialog { background-color: #ffffff; }")

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(28, 22, 28, 18)
            layout.setSpacing(0)

            check = QLabel("\u2713")
            check.setAlignment(Qt.AlignCenter)
            check.setStyleSheet("font-size: 34px; color: #22c55e; font-weight: bold;")
            layout.addWidget(check)
            layout.addSpacing(8)

            text = QLabel(
                "A new version has been downloaded.\n"
                "Restart now to apply the update?"
            )
            text.setAlignment(Qt.AlignCenter)
            text.setStyleSheet(
                "font-family: 'Microsoft YaHei', 'SimHei', sans-serif;"
                "font-size: 13px; color: #4b5563;"
            )
            layout.addWidget(text)
            layout.addSpacing(18)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(10)
            btn_row.addStretch()

            later_btn = QPushButton("Later")
            later_btn.setFixedSize(100, 36)
            later_btn.setStyleSheet("""
                QPushButton {
                    background: #ffffff; color: #374151;
                    border: 1px solid #d1d5db; border-radius: 6px;
                    font-size: 13px; font-weight: 600;
                }
                QPushButton:hover { background: #f3f4f6; border-color: #9ca3af; }
                QPushButton:pressed { background: #e5e7eb; }
            """)

            restart_btn = QPushButton("Restart Now")
            restart_btn.setFixedSize(120, 36)
            restart_btn.setStyleSheet("""
                QPushButton {
                    background: #2563eb; color: white;
                    border: none; border-radius: 6px;
                    font-size: 13px; font-weight: 600;
                }
                QPushButton:hover { background: #1d4ed8; }
                QPushButton:pressed { background: #1e40af; }
            """)

            restart_btn.clicked.connect(dialog.accept)
            later_btn.clicked.connect(dialog.reject)

            btn_row.addWidget(restart_btn)
            btn_row.addWidget(later_btn)
            btn_row.addStretch()
            layout.addLayout(btn_row)

            result = dialog.exec_()
            dialog.deleteLater()

            def _write_bat(app_dir, new_dir, launch, include_start):
                updater_dir = Path(AppPath.UpdaterRoot)
                updater_dir.mkdir(parents=True, exist_ok=True)
                if sys.platform == "win32":
                    name = "_replace.bat" if include_start else "_apply_update.bat"
                    bat_path = updater_dir / name
                    lines = [
                        '@echo off\n',
                        'timeout /t 3 /nobreak >nul\n',
                        f'robocopy "{new_dir}" "{app_dir}" /E /MOVE >nul 2>&1\n',
                        f'if exist "{new_dir}" rmdir /S /Q "{new_dir}"\n',
                    ]
                    if include_start:
                        lines.append(f'start "" "{app_dir / launch.name}"\n')
                    lines.append('del "%~f0"\n')
                    bat_path.write_text("".join(lines), encoding="utf-8")
                    return bat_path
                else:
                    name = "_replace.sh" if include_start else "_apply_update.sh"
                    sh_path = updater_dir / name
                    lines = [
                        '#!/bin/bash\n',
                        'sleep 3\n',
                        f'cp -a "{new_dir}/." "{app_dir}/"\n',
                        f'rm -rf "{new_dir}"\n',
                    ]
                    if include_start:
                        lines.append(f'nohup "{app_dir / launch.name}" > /dev/null 2>&1 &\n')
                    lines.append('rm -f "$0"\n')
                    sh_path.write_text("".join(lines), encoding="utf-8")
                    os.chmod(str(sh_path), 0o755)
                    return sh_path

            try:
                launch = Path(str(launch_path or "").strip())
                if launch.exists():
                    new_dir = launch.parent
                    app_dir = Path(sys.executable).resolve().parent

                    if result == QDialog.Accepted:
                        bat = _write_bat(app_dir, new_dir, launch, include_start=True)
                        subprocess.Popen(
                            [str(bat)],
                            shell=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        ) if sys.platform == "win32" else subprocess.Popen(
                            [str(bat)],
                            shell=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        QApplication.quit()
                    else:
                        bat = _write_bat(app_dir, new_dir, launch, include_start=False)
                        self._pending_update_bat = bat
                else:
                    if result == QDialog.Accepted:
                        webbrowser.open_new(self._release_page(remote_ver))
                        QApplication.quit()
            except Exception:
                if result == QDialog.Accepted:
                    webbrowser.open_new(self._release_page(remote_ver))
                    QApplication.quit()

        thread.progress_changed.connect(_on_progress)
        thread.install_finished.connect(_on_finished)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def refresh_ssh_status(self):
        host = _safe_str(self.get_save_data(Key.SshHost, "")).strip()

        if not _is_non_empty(host):
            self._remote_connected = False
            self._remote_host = None
            _update_title_bar_status(self, is_local=True, ok=True, host=None)
            return

        ok = bool(self._remote_connected) and (self._remote_host == host)
        if ok:
            _update_title_bar_status(self, is_local=False, ok=True, host=host)
        else:
            _update_title_bar_status(self, is_local=True, ok=True, host=None)

    def is_remote_connected(self) -> bool:
        return bool(self._remote_connected)

    def connect_remote_and_reload(self) -> tuple[bool, str | None]:
        host = _safe_str(self.get_save_data(Key.SshHost, "")).strip()
        username = _safe_str(self.get_save_data(Key.SshUsername, "")).strip()
        password = _safe_str(self.get_save_data(Key.SshPassword, ""))
        use_pkey = _truthy(self.get_save_data(Key.SshUsePrivateKey, False))
        pkey_path = _safe_str(self.get_save_data(Key.SshPrivateKeyPath, "")).strip()

        if not _is_non_empty(host):
            return False, "未填写IP"
        if not _is_non_empty(username):
            return False, "未填写账户名"
        if use_pkey and not _is_non_empty(pkey_path):
            return False, "启用私钥但未选择私钥文件"

        cfg = SshConfig(
            host=host,
            username=username,
            password=None if use_pkey else password,
            pkey_path=pkey_path if use_pkey else None,
            timeout_sec=10,
        )
        remote_app_root_override = _safe_str(self.get_save_data(Key.SshRemoteAppRoot, "")).strip()

        dialog = QProgressDialog("Connecting to remote server...", None, 0, 100, self)
        dialog.setWindowTitle("SSH Connection")
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setValue(0)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setFixedSize(dialog.width() + 120, dialog.height())
        dialog.show()

        thread = RemoteConnectSetupThread(cfg, host, self._local_data_root, remote_app_root_override)

        state = {"ok": False, "error": ""}
        wait_loop = QEventLoop()

        def _on_progress(percent: int, message: str):
            dialog.setLabelText(message)
            dialog.setValue(max(0, min(100, int(percent))))

        def _on_finished(ok: bool, msg: str):
            state["ok"] = ok
            state["error"] = msg
            wait_loop.quit()

        thread.progress_changed.connect(_on_progress)
        thread.finished.connect(_on_finished)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        wait_loop.exec_()

        dialog.hide()
        dialog.deleteLater()

        if not state["ok"]:
            self._cleanup_remote_state()
            return False, state["error"]

        store = thread.store
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

        self._remote_plan_service = RemotePlanService(
            lambda: self._remote_ssh_cfg,
            lambda: AppPath.RemoteAppRoot,
        )
        self.load_data_json()
        self._reload_pages()
        self.refresh_ssh_status()

        return True, None

    def _cleanup_remote_state(self):
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
                for k in self._local_settings_keys():
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

    @staticmethod
    def _local_settings_keys() -> set[str]:
        keys = set(AutoClockWindow._ssh_keys())
        keys.add(Key.CheckUpdateOnStartup)
        return keys

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
            for k in self._local_settings_keys():
                merged.pop(k, None)
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
            if key in self._local_settings_keys():
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
            if key in self._local_settings_keys():
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


class RemoteConnectSetupThread(QThread):
    progress_changed = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, ssh_cfg: SshConfig, host: str, local_data_root: str, remote_app_root_override: str):
        super().__init__()
        self._ssh_cfg = ssh_cfg
        self._host = host
        self._local_data_root = local_data_root
        self._remote_app_root_override = remote_app_root_override
        self.store: RemoteDataStore | None = None

    def run(self):
        try:
            self.progress_changed.emit(5, "Connecting to remote server...")

            store = RemoteDataStore(
                ssh_cfg=self._ssh_cfg,
                host=self._host,
                local_data_root=self._local_data_root,
                remote_app_root_override=self._remote_app_root_override,
            )
            ok, err = store.bootstrap()
            if not ok:
                self.finished.emit(False, err or "Bootstrap failed")
                return
            if not store.cache_data_root:
                self.finished.emit(False, "远端缓存目录初始化失败")
                return
            if not store.remote_app_root_abs or not store.remote_data_root_abs:
                self.finished.emit(False, "远端目录初始化失败")
                return

            self.store = store

            version = Utils.get_app_version_from_config_json(default="")
            if version:
                url = WebPath.LinuxRunnerDownloadUrlTemplate.format(version=version)
                with SshClient(self._ssh_cfg) as ssh:
                    layout = RemoteLinuxLayout(app_root=store.remote_app_root_abs)
                    remote = RemoteLinuxRunner(ssh, layout=layout)

                    if remote.remote_has_version(version):
                        self.progress_changed.emit(80, "Runner already downloaded, setting current...")
                    else:
                        self.progress_changed.emit(30, "Downloading runner...")

                        def _on_progress(pct: int):
                            self.progress_changed.emit(max(30, min(80, pct)), f"Downloading runner... ({pct}%)")

                        ok, err = remote.ensure_installed_from_url(version, url, progress_callback=_on_progress)
                        if not ok:
                            self.finished.emit(False, err or "Runner installation failed")
                            return

                    self.progress_changed.emit(95, "Setting current version...")
                    code, _, err2 = remote.set_current(version)
                    if code != 0:
                        self.finished.emit(False, err2 or "Set current version failed")
                        return

            self.progress_changed.emit(100, "Connected")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


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
