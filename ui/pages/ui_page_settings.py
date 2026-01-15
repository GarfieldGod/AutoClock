from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSizePolicy

from src.utils.const import Key
from ui.main_window.auto_clock_window import AutoClockPageContent, AutoClockContainer
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import CheckBox, LineEdit, PasswordLineEdit, FileSelectLineEdit, ComboBox
import platform


class ToolSettingsPage(AutoClockPageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(ToolSettingsPage, self).__init__(y, x)

    def init_container(self):
        tool_config = ToolConfigContainer(3, 2)
        self.add_container(tool_config, 0, 0)

        ssh_config = SshConfigContainer(3, 3)
        self.add_container(ssh_config, 2, 0)

        self.input_save_widget = []
        if platform.system() == 'Linux':
            self.input_save_widget.append(tool_config.check_linux_credentials_on_plan_create)

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

        self.init_ui_layout()

    def init_ui_layout(self):
        group_tool = QGroupBox("Tool Settings")
        group_tool.setStyleSheet(get_group_css({}))
        layout_tool = QVBoxLayout(group_tool)

        if platform.system() == 'Linux':
            label = QLabel("Linux: 创建系统计划前提示检查账号/自动登录配置")
            layout_tool.addWidget(label)
            layout_tool.addWidget(self.check_linux_credentials_on_plan_create)
        else:
            label = QLabel("当前系统无Linux相关工具设置")
            layout_tool.addWidget(label)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_tool)


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

        self.btn_connect = QPushButton("连接")
        self.btn_disconnect = QPushButton("断开")

        self.init_ui_layout()

    def init_ui_layout(self):
        group = QGroupBox("SSH Settings")
        group.setStyleSheet(get_group_css({}))
        layout = QVBoxLayout(group)

        def _add_row(text: str, widget):
            row = QHBoxLayout()
            label = QLabel(text)
            label.setFixedWidth(120)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(label)
            row.addWidget(widget, stretch=1)
            layout.addLayout(row)

        _add_row("是否启用SSH", self.ssh_enabled)
        _add_row("目标平台", self.ssh_server_platform)
        _add_row("IP", self.ssh_host)
        _add_row("账户名", self.ssh_username)
        _add_row("密码", self.ssh_password)
        _add_row("启用私钥", self.ssh_use_private_key)

        row_key = QHBoxLayout()
        label_key = QLabel("私钥文件")
        label_key.setFixedWidth(120)
        self.ssh_private_key_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row_key.addWidget(label_key)
        row_key.addWidget(self.ssh_private_key_path, stretch=1)
        layout.addLayout(row_key)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_connect)
        btn_row.addWidget(self.btn_disconnect)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group)

        self.btn_connect.clicked.connect(self._on_connect_clicked)
        self.btn_disconnect.clicked.connect(self._on_disconnect_clicked)

    def _on_connect_clicked(self):
        try:
            w = self.window()

            if platform.system() == "Windows":
                if str(self.ssh_server_platform.currentText()).strip() != "Linux":
                    from src.ui.ui_message import MessageBox
                    MessageBox("请先选择合法的平台类型!")
                    self._update_lock_state(False)
                    return

            if hasattr(w, "connect_remote_and_reload"):
                ok, err = w.connect_remote_and_reload()
                if not ok:
                    from src.ui.ui_message import MessageBox
                    MessageBox(f"连接失败：{err or ''}")
                    self._update_lock_state(False)
                else:
                    self._update_lock_state(True)
            else:
                from src.ui.ui_message import MessageBox
                MessageBox("当前窗口不支持SSH连接")
        except Exception as e:
            from src.ui.ui_message import MessageBox
            MessageBox(f"连接异常：{e}")
            self._update_lock_state(False)

    def _on_disconnect_clicked(self):
        try:
            w = self.window()
            if hasattr(w, "disconnect_remote_and_reload"):
                w.disconnect_remote_and_reload()
                self._update_lock_state(False)
            else:
                from src.ui.ui_message import MessageBox
                MessageBox("当前窗口不支持SSH断开")
        except Exception as e:
            from src.ui.ui_message import MessageBox
            MessageBox(f"断开异常：{e}")

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
