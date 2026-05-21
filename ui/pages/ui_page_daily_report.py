import os
import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QScrollArea, QSizePolicy, QDialog

from src.utils.const import Key, AppPath
from ui.main_window.auto_clock_window import AutoClockPageContent
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import LineEdit, TextEdit
from src.ui.ui_message import MessageBox


class DailyReportPage(AutoClockPageContent):
    def __init__(self, y, x):
        self.rows = y
        self.columns = x
        self.containers = []
        self.input_save_widget = []
        QWidget.__init__(self)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.viewport().setStyleSheet("background: transparent;")

        inner = QWidget()
        inner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        inner.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(inner)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self._build_driver_section(layout)
        self._build_auth_login_section(layout)
        self._build_template_section(layout)

        layout.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.input_save_widget = [
            self.driver_path,
            self.work_desc,
            self.normal_hours,
            self.overtime_hours,
            self.project_name,
            self.project_task,
            self.activity_type,
            self.project_module,
        ]
        self._auth_status_worker = None
        self._auth_check_last_ts = 0.0
        self._auth_check_last_ctx = None
        self._auth_check_cooldown_sec = 30

    def _build_driver_section(self, parent_layout):
        group = QGroupBox("Driver")
        group.setStyleSheet(get_group_css({}))
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel("Edge Driver Path:"))
        path_layout = QHBoxLayout()
        self.driver_path = LineEdit(Key.DriverPath)
        path_layout.addWidget(self.driver_path)
        download_btn = QPushButton("⬇")
        download_btn.setFixedSize(28, 28)
        download_btn.setStyleSheet("border: none; background-color: transparent; padding:0; font-size:18px;")
        download_btn.setToolTip("Auto download matching Edge Driver")
        download_btn.clicked.connect(lambda: self._download_driver(download_btn))
        path_layout.addWidget(download_btn)
        layout.addLayout(path_layout)

        parent_layout.addWidget(group)

    def _download_driver(self, btn):
        from PyQt5.QtWidgets import QApplication
        from src.utils.utils import Utils
        try:
            btn.setEnabled(False)
            btn.setText("⏳")
            QApplication.processEvents()
            w = self.window()
            if hasattr(w, "is_remote_connected") and w.is_remote_connected() and hasattr(w, "ensure_remote_driver"):
                ok, result = w.ensure_remote_driver()
            else:
                ok, result = Utils.download_edge_web_driver()
            if ok:
                self.driver_path.setText(result)
                MessageBox(f"Driver downloaded successfully!\nPath: {result}")
            else:
                MessageBox(f"Driver download failed!\nError: {result}")
        except Exception as e:
            MessageBox(f"Driver download error: {str(e)}")
        finally:
            btn.setEnabled(True)
            btn.setText("⬇")

    def _build_auth_login_section(self, parent_layout):
        group = QGroupBox("Auth Login")
        group.setStyleSheet(get_group_css({"Text_Color": "#D32F2F"}))
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout_group = QVBoxLayout(group)

        info = QLabel(
            "Click 'Authorization' to open the auth dialog.\n"
            "Scan the QR code with your phone or use the phone login option."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout_group.addWidget(info)

        btn_layout = QHBoxLayout()
        self._auth_btn = QPushButton("Authorization")
        self._auth_btn.setStyleSheet(
            "QPushButton { background: #2563eb; color: white; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-weight: 600; font-size: 13px; }"
            "QPushButton:hover { background: #1d4ed8; }"
            "QPushButton:pressed { background: #1e40af; }"
            "QPushButton:disabled { background: #93c5fd; }"
        )
        self._auth_btn.clicked.connect(self._start_auth)
        btn_layout.addWidget(self._auth_btn)

        self._auth_status_label = QLabel()
        self._auth_status_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        btn_layout.addWidget(self._auth_status_label)
        btn_layout.addStretch()
        layout_group.addLayout(btn_layout)

        parent_layout.addWidget(group)

    def _update_auth_status(self):
        if not self.get_data_func:
            return
        authorized = self.get_data_func(Key.DailyAuthorized, False)
        if authorized:
            self._auth_status_label.setText("✓ Authorized")
            self._auth_status_label.setStyleSheet("color: #16a34a; font-size: 12px; font-weight: 600;")
        else:
            self._auth_status_label.setText("✗ Not Authorized")
            self._auth_status_label.setStyleSheet("color: #dc2626; font-size: 12px; font-weight: 600;")

    def _set_auth_status(self, authorized):
        old_authorized = None
        if self.get_data_func:
            old_authorized = bool(self.get_data_func(Key.DailyAuthorized, False))
        if self.set_data_func:
            new_authorized = bool(authorized)
            if old_authorized is None or old_authorized != new_authorized:
                self.set_data_func(Key.DailyAuthorized, new_authorized)
        self._update_auth_status()

    def _show_auth_checking(self):
        self._auth_status_label.setText("… Checking")
        self._auth_status_label.setStyleSheet("color: #6b7280; font-size: 12px; font-weight: 600;")

    def _on_auth_status_ready(self, authorized, ctx):
        self._auth_check_last_ts = time.monotonic()
        self._auth_check_last_ctx = ctx
        self._set_auth_status(bool(authorized))

    def _on_auth_status_error(self, _msg, ctx):
        self._auth_check_last_ts = time.monotonic()
        self._auth_check_last_ctx = ctx
        self._set_auth_status(False)

    def _refresh_auth_status_async(self):
        from src.utils.utils import Utils
        from src.core.daily_report.daily_report_manager import AuthStatusCheckWorker

        if self._auth_status_worker and self._auth_status_worker.isRunning():
            return

        w = self.window()
        is_remote = hasattr(w, "is_remote_connected") and w.is_remote_connected()

        data = Utils.read_dict_from_json(AppPath.DataJson)
        driver_path = (data.get(Key.DriverPath) or "").strip()
        show_web_page = False

        if not is_remote and (not driver_path or not os.path.exists(driver_path)):
            self._set_auth_status(False)
            return

        ssh_cfg = getattr(w, '_remote_ssh_cfg', None) if is_remote else None
        if is_remote and (not ssh_cfg or not driver_path):
            self._set_auth_status(False)
            return

        ctx = (bool(is_remote), str(driver_path).strip())
        now = time.monotonic()
        if self._auth_check_last_ctx == ctx and (now - self._auth_check_last_ts) < self._auth_check_cooldown_sec:
            return

        self._show_auth_checking()

        worker = AuthStatusCheckWorker(
            is_remote=is_remote,
            driver_path=driver_path,
            show_web_page=show_web_page,
            ssh_cfg=ssh_cfg,
        )
        worker.status_ready.connect(lambda ok, _ctx=ctx: self._on_auth_status_ready(ok, _ctx))
        worker.status_error.connect(lambda msg, _ctx=ctx: self._on_auth_status_error(msg, _ctx))
        worker.finished.connect(lambda: setattr(self, "_auth_status_worker", None))
        self._auth_status_worker = worker
        worker.start()

    def showEvent(self, event):
        super().showEvent(event)
        self._show_auth_checking()
        self._refresh_auth_status_async()

    def _start_auth(self):
        from src.utils.utils import Utils
        from src.core.daily_report.daily_report_manager import AuthWorker, RemoteAuthWorker
        from ui.dialogs.daily_auth_dialog import DailyAuthDialog

        if self._auth_status_worker and self._auth_status_worker.isRunning():
            self._auth_status_worker.wait(12000)

        w = self.window()
        is_remote = hasattr(w, "is_remote_connected") and w.is_remote_connected()
        show_web_page = str(os.environ.get("AUTO_CLOCK_DEBUG_AUTH_SHOW_WEB", "")).strip().lower() in {
            "1", "true", "yes", "on"
        }

        if is_remote:
            ssh_cfg = getattr(w, '_remote_ssh_cfg', None)
            if not ssh_cfg:
                MessageBox("No SSH connection found. Please connect to remote first.")
                return
            if hasattr(w, "ensure_remote_driver"):
                ok, result = w.ensure_remote_driver()
                if not ok:
                    MessageBox(str(result or "Failed to ensure remote Edge Driver."))
                    return
            data = Utils.read_dict_from_json(AppPath.DataJson)
            driver_path = (data.get(Key.DriverPath) or "").strip()
            if not driver_path:
                MessageBox("Remote driver path not configured in remote data.json.")
                return
            worker = RemoteAuthWorker(ssh_cfg, driver_path, show_web_page=show_web_page)
        else:
            data = Utils.read_dict_from_json(AppPath.DataJson)
            driver_path = (data.get(Key.DriverPath) or "").strip()
            if not driver_path or not os.path.exists(driver_path):
                MessageBox("Please configure a valid Edge Driver Path first.")
                return
            worker = AuthWorker(driver_path, show_web_page=show_web_page)

        dialog = DailyAuthDialog(self.window())
        dialog.set_callbacks(
            on_phone_submit=lambda phone: worker.set_phone(phone),
            on_code_submit=lambda code: worker.set_code(code),
            on_switch_phone=lambda: worker.switch_to_phone(),
            on_switch_qr=lambda: worker.switch_to_qr(),
            on_cancel=lambda: worker.cancel(),
        )
        worker.qr_ready.connect(dialog.show_qr_code)
        worker.need_phone.connect(dialog.show_phone_input)
        worker.need_code.connect(dialog.show_code_input)
        worker.auth_success.connect(lambda: self._on_auth_result(dialog, worker, True, None))
        worker.auth_error.connect(lambda msg: self._on_auth_result(dialog, worker, False, msg))
        worker.start()

        self._auth_btn.setEnabled(False)
        dialog.exec_()
        if dialog.result() != QDialog.Accepted:
            self._auth_btn.setEnabled(True)

    def _on_auth_result(self, dialog, worker, ok, error):
        if ok:
            dialog.show_success()
            self._set_auth_status(True)
        elif error:
            dialog.show_error(error)
            self._set_auth_status(False)
            self._auth_btn.setEnabled(True)
        else:
            self._auth_btn.setEnabled(True)

    def _build_template_section(self, parent_layout):
        group = QGroupBox("Daily Report")
        group.setStyleSheet(get_group_css({}))
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout_group = QVBoxLayout(group)

        layout_group.addWidget(QLabel("Work Description:"))
        self.work_desc = TextEdit(Key.DailyWorkDesc)
        self.work_desc.setMaximumHeight(60)
        self.work_desc.setPlaceholderText("Use Ctrl+Enter or Shift+Enter to insert newline")
        layout_group.addWidget(self.work_desc)

        row1 = QHBoxLayout()
        w1 = QWidget()
        l1 = QVBoxLayout(w1)
        l1.setContentsMargins(0, 0, 0, 0)
        l1.addWidget(QLabel("Normal Hours:"))
        self.normal_hours = LineEdit(Key.DailyNormalHours)
        l1.addWidget(self.normal_hours)

        w2 = QWidget()
        l2 = QVBoxLayout(w2)
        l2.setContentsMargins(0, 0, 0, 0)
        l2.addWidget(QLabel("Overtime Hours:"))
        self.overtime_hours = LineEdit(Key.DailyOvertimeHours)
        l2.addWidget(self.overtime_hours)

        row1.addWidget(w1)
        row1.addWidget(w2)
        layout_group.addLayout(row1)

        row2 = QHBoxLayout()
        w3 = QWidget()
        l3 = QVBoxLayout(w3)
        l3.setContentsMargins(0, 0, 0, 0)
        l3.addWidget(QLabel("Project Name:"))
        self.project_name = LineEdit(Key.DailyProjectName)
        l3.addWidget(self.project_name)

        w4 = QWidget()
        l4 = QVBoxLayout(w4)
        l4.setContentsMargins(0, 0, 0, 0)
        l4.addWidget(QLabel("Project Task:"))
        self.project_task = LineEdit(Key.DailyTaskName)
        l4.addWidget(self.project_task)

        row2.addWidget(w3)
        row2.addWidget(w4)
        layout_group.addLayout(row2)

        row3 = QHBoxLayout()
        w5 = QWidget()
        l5 = QVBoxLayout(w5)
        l5.setContentsMargins(0, 0, 0, 0)
        l5.addWidget(QLabel("Activity Type:"))
        self.activity_type = LineEdit(Key.DailyActivityType)
        l5.addWidget(self.activity_type)

        w6 = QWidget()
        l6 = QVBoxLayout(w6)
        l6.setContentsMargins(0, 0, 0, 0)
        l6.addWidget(QLabel("Project Module:"))
        self.project_module = LineEdit(Key.DailyProjectModule)
        l6.addWidget(self.project_module)

        row3.addWidget(w5)
        row3.addWidget(w6)
        layout_group.addLayout(row3)

        parent_layout.addWidget(group)


