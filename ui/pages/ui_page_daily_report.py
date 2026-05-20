import os

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QScrollArea, QSizePolicy, QApplication

from src.utils.const import Key, AppPath
from ui.main_window.auto_clock_window import AutoClockPageContent
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import LineEdit, TextEdit
from src.ui.ui_message import MessageBox
from src.utils.log import Log


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
            "Click the 'Authorization' button to open Edge and complete the login process.\n"
            "After logging in, close the browser. The authorization status will be saved automatically."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout_group.addWidget(info)

        btn_layout = QHBoxLayout()
        login_btn = QPushButton("Authorization")
        login_btn.setStyleSheet(
            "QPushButton { background: #2563eb; color: white; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-weight: 600; font-size: 13px; }"
            "QPushButton:hover { background: #1d4ed8; }"
            "QPushButton:pressed { background: #1e40af; }"
            "QPushButton:disabled { background: #93c5fd; }"
        )
        login_btn.clicked.connect(lambda: self._manual_login(login_btn))
        btn_layout.addWidget(login_btn)

        self._auth_status_label = QLabel()
        self._auth_status_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        btn_layout.addWidget(self._auth_status_label)
        btn_layout.addStretch()
        layout_group.addLayout(btn_layout)

        self._manual_login_btn = login_btn
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

    def showEvent(self, event):
        super().showEvent(event)
        self._update_auth_status()

    def _manual_login(self, btn):
        from src.utils.utils import Utils
        data = Utils.read_dict_from_json(AppPath.DataJson)
        driver_path = (data.get(Key.DriverPath) or "").strip()
        if not driver_path or not os.path.exists(driver_path):
            MessageBox("请先配置有效的 Edge Driver 路径。")
            return

        btn.setEnabled(False)
        btn.setText("Opening...")
        QApplication.processEvents()

        self._login_thread = _ManualLoginThread(driver_path)
        self._login_thread.finished.connect(lambda ok, err: self._on_login_done(btn, ok, err))
        self._login_thread.start()

    def _on_login_done(self, btn, ok, error):
        btn.setEnabled(True)
        btn.setText("Authorization")
        if ok:
            if self.set_data_func:
                self.set_data_func(Key.DailyAuthorized, True)
            self._update_auth_status()
            MessageBox("授权成功！已保存登录状态，可以自动执行日报了。")
        elif error:
            MessageBox(f"Login failed: {error}")

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


class _ManualLoginThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, driver_path):
        super().__init__()
        self.driver_path = driver_path

    def run(self):
        try:
            from src.core.daily_report.daily_report_manager import run_manual_login
            ok, error = run_manual_login(self.driver_path)
            self.finished.emit(ok, error)
        except Exception as e:
            self.finished.emit(False, str(e))
