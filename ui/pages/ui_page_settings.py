from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSizePolicy

from src.utils.const import Key
from src.utils.utils import Utils
from ui.main_window.auto_clock_window import AutoClockPageContent, AutoClockContainer
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import CheckBox, LineEdit, PasswordLineEdit, FileSelectLineEdit, ComboBox
import platform


class ToolSettingsPage(AutoClockPageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(ToolSettingsPage, self).__init__(y, x)

    def init_container(self):
        tool_config = ToolConfigContainer(4, 2)
        self.add_container(tool_config, 0, 0)

        ssh_config = SshConfigContainer(4, 3)
        self.add_container(ssh_config, 2, 0)

        self.input_save_widget = []
        if platform.system() == 'Linux':
            self.input_save_widget.append(tool_config.check_linux_credentials_on_plan_create)

        self.input_save_widget.append(tool_config.check_update_on_startup)
        self.input_save_widget.append(ssh_config.ssh_enabled)
        self.input_save_widget.append(ssh_config.ssh_host)
        self.input_save_widget.append(ssh_config.ssh_username)
        self.input_save_widget.append(ssh_config.ssh_password)
        self.input_save_widget.append(ssh_config.ssh_use_private_key)
        self.input_save_widget.append(ssh_config.ssh_private_key_path)
        self.input_save_widget.append(ssh_config.ssh_server_platform)


class ToolConfigContainer(AutoClockContainer):
    def __init__(self, x, y):
        super(ToolConfigContainer, self).__init__(x, y)

        self.check_linux_credentials_on_plan_create = CheckBox(Key.CheckLinuxCredentialsOnPlanCreate, default=True)
        self.check_update_on_startup = ComboBox(
            Key.CheckUpdateOnStartup,
            items=["Check At Startup", "Never"],
            data_values=["on_startup", "never"],
            default="on_startup",
        )
        self.btn_check_update = QPushButton("Check")

        self.init_ui_layout()

    def init_ui_layout(self):
        group_tool = QGroupBox("Tool Settings")
        group_tool.setStyleSheet(get_group_css({"BackGround_Color": "#fbfbfd", "Border_Color": "#cfd6e0"}))
        group_tool.setMinimumWidth(390)
        layout_tool = QVBoxLayout(group_tool)
        layout_tool.setContentsMargins(16, 14, 16, 14)
        layout_tool.setSpacing(8)

        title = QLabel("General Preferences")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color:#374151;")
        title.setMinimumHeight(18)
        layout_tool.addWidget(title)

        if platform.system() == 'Linux':
            label = QLabel("Validate account settings before creating Linux system plans")
            label.setWordWrap(True)
            label.setStyleSheet("color:#4b5563;")
            layout_tool.addWidget(label)
            layout_tool.addWidget(self.check_linux_credentials_on_plan_create)
        else:
            label = QLabel("No Linux-specific options on this platform")
            label.setStyleSheet("color:#6b7280;")
            label.setMinimumHeight(18)
            layout_tool.addWidget(label)

        row_update = QHBoxLayout()
        row_update.setSpacing(8)
        label_update = QLabel("Update")
        label_update.setFixedWidth(70)
        row_update.addWidget(label_update)
        self.check_update_on_startup.setMinimumWidth(160)
        row_update.addWidget(self.check_update_on_startup, stretch=1)
        layout_tool.addLayout(row_update)

        row_version = QHBoxLayout()
        row_version.setSpacing(8)
        label_version = QLabel("Version")
        label_version.setFixedWidth(70)
        value_version = QLabel(Utils.get_app_version_from_config_json(default="unknown"))
        value_version.setStyleSheet("color:#111827; font-weight:600;")
        row_version.addWidget(label_version)
        row_version.addWidget(value_version, stretch=1)
        row_version.addWidget(self.btn_check_update)
        layout_tool.addLayout(row_version)

        self.btn_check_update.setCursor(Qt.PointingHandCursor)
        self.btn_check_update.setMinimumWidth(86)
        self.btn_check_update.setFixedHeight(28)
        self.btn_check_update.setStyleSheet(
            "QPushButton {"
            "background-color:#2563eb; color:white; border:1px solid #1d4ed8;"
            "border-radius:6px; padding:0 10px; font-weight:600; }"
            "QPushButton:hover { background-color:#1d4ed8; }"
            "QPushButton:pressed { background-color:#1e40af; }"
        )

        layout_container = QVBoxLayout(self)
        layout_container.setContentsMargins(0, 0, 0, 0)
        layout_container.addWidget(group_tool)

        self.btn_check_update.clicked.connect(self._on_check_update_clicked)

    def _on_check_update_clicked(self):
        try:
            w = self.window()
            if hasattr(w, "check_app_update"):
                w.check_app_update(manual=True)
            else:
                from src.ui.ui_message import MessageBox
                MessageBox("Current window does not support update checks")
        except Exception as e:
            from src.ui.ui_message import MessageBox
            MessageBox(f"Check update failed: {e}")


class SshConfigContainer(AutoClockContainer):
    def __init__(self, x, y):
        super(SshConfigContainer, self).__init__(x, y)

        self.ssh_enabled = CheckBox(Key.SshEnabled, default=False)
        self.ssh_host = LineEdit(Key.SshHost, default="")
        self.ssh_username = LineEdit(Key.SshUsername, default="")
        self.ssh_password = PasswordLineEdit(Key.SshPassword, default="")
        self.ssh_use_private_key = CheckBox(Key.SshUsePrivateKey, default=False)
        self.ssh_private_key_path = FileSelectLineEdit(Key.SshPrivateKeyPath, default="")

        if platform.system() == "Windows":
            platform_items = ["---", "Linux"]
        else:
            platform_items = ["---"]
        self.ssh_server_platform = ComboBox(Key.SshServerPlatform, items=platform_items, default="---")

        self.btn_connect = QPushButton("Connect")
        self.btn_disconnect = QPushButton("Disconnect")

        self.init_ui_layout()

    def init_ui_layout(self):
        group = QGroupBox("SSH Settings")
        group.setStyleSheet(get_group_css({"BackGround_Color": "#fbfbfd", "Border_Color": "#cfd6e0"}))
        group.setMinimumWidth(390)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        tip = QLabel("Use SSH to manage tasks on a remote Linux host")
        tip.setStyleSheet("color:#4b5563;")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        def _add_row(text: str, widget):
            row = QHBoxLayout()
            row.setSpacing(10)
            label = QLabel(text)
            label.setFixedWidth(118)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(label)
            row.addWidget(widget, stretch=1)
            layout.addLayout(row)

        _add_row("Enable SSH", self.ssh_enabled)
        _add_row("Target Platform", self.ssh_server_platform)
        _add_row("IP", self.ssh_host)
        _add_row("Username", self.ssh_username)
        _add_row("Password", self.ssh_password)
        _add_row("Use Private Key", self.ssh_use_private_key)

        row_key = QHBoxLayout()
        row_key.setSpacing(10)
        label_key = QLabel("Private Key File")
        label_key.setFixedWidth(118)
        self.ssh_private_key_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row_key.addWidget(label_key)
        row_key.addWidget(self.ssh_private_key_path, stretch=1)
        layout.addLayout(row_key)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addWidget(self.btn_connect)
        btn_row.addWidget(self.btn_disconnect)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_disconnect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.setFixedHeight(28)
        self.btn_disconnect.setFixedHeight(28)
        self.btn_connect.setStyleSheet(
            "QPushButton {"
            "background-color:#059669; color:white; border:1px solid #047857;"
            "border-radius:6px; padding:0 12px; font-weight:600; }"
            "QPushButton:hover { background-color:#047857; }"
            "QPushButton:pressed { background-color:#065f46; }"
        )
        self.btn_disconnect.setStyleSheet(
            "QPushButton {"
            "background-color:#6b7280; color:white; border:1px solid #4b5563;"
            "border-radius:6px; padding:0 12px; font-weight:600; }"
            "QPushButton:hover { background-color:#4b5563; }"
            "QPushButton:pressed { background-color:#374151; }"
        )

        layout_container = QVBoxLayout(self)
        layout_container.setContentsMargins(0, 0, 0, 0)
        layout_container.addWidget(group)

        self.btn_connect.clicked.connect(self._on_connect_clicked)
        self.btn_disconnect.clicked.connect(self._on_disconnect_clicked)

    def _on_connect_clicked(self):
        try:
            w = self.window()

            if platform.system() == "Windows":
                if str(self.ssh_server_platform.currentText()).strip() != "Linux":
                    from src.ui.ui_message import MessageBox
                    MessageBox("Please select a valid target platform first")
                    self._update_lock_state(False)
                    return

            if hasattr(w, "connect_remote_and_reload"):
                ok, err = w.connect_remote_and_reload()
                if not ok:
                    from src.ui.ui_message import MessageBox
                    MessageBox(f"Connect failed: {err or ''}")
                    self._update_lock_state(False)
                else:
                    self._update_lock_state(True)
            else:
                from src.ui.ui_message import MessageBox
                MessageBox("Current window does not support SSH connection")
        except Exception as e:
            from src.ui.ui_message import MessageBox
            MessageBox(f"Connect error: {e}")
            self._update_lock_state(False)

    def _on_disconnect_clicked(self):
        try:
            w = self.window()
            if hasattr(w, "disconnect_remote_and_reload"):
                w.disconnect_remote_and_reload()
                self._update_lock_state(False)
            else:
                from src.ui.ui_message import MessageBox
                MessageBox("Current window does not support SSH disconnect")
        except Exception as e:
            from src.ui.ui_message import MessageBox
            MessageBox(f"Disconnect error: {e}")

    def _update_lock_state(self, connected: bool):
        # 连接成功后锁定配置，避免连接过程中修改 host/user 等导致状态混乱
        for w in [
            self.ssh_enabled,
            self.ssh_server_platform,
            self.ssh_host,
            self.ssh_username,
            self.ssh_password,
            self.ssh_use_private_key,
            self.ssh_private_key_path,
        ]:
            try:
                w.setEnabled(not connected)
            except Exception:
                pass

        try:
            self.btn_connect.setEnabled(not connected)
            self.btn_disconnect.setEnabled(connected)
        except Exception:
            pass
