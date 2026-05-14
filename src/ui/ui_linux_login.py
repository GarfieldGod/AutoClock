from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton, QLineEdit, QDialog, QHBoxLayout, QLabel, QVBoxLayout, QTextEdit, QLayout
from PyQt5.QtCore import Qt
import os

from src.utils.utils import Utils
from src.ui.ui_message import MessageBox
from src.extend.auto_linux_login import auto_linux_login_off, auto_linux_login_on, check_auto_login_status, validate_linux_credentials, get_linux_credentials_status
from src.extend.auto_linux_sudo import save_sudoers_config, check_sudo_permission, get_sudo_install_commands
from src.utils.const import AppPath, Key

_DIALOG_STYLE = """
    QDialog {
        background-color: #ffffff;
    }
"""

_BTN_PRIMARY = """
    QPushButton {
        background-color: #2563eb; color: white;
        border: none; border-radius: 6px;
        padding: 8px 24px; font-weight: 600; font-size: 13px;
        min-width: 80px;
    }
    QPushButton:hover { background-color: #1d4ed8; }
    QPushButton:pressed { background-color: #1e40af; }
"""

_BTN_SECONDARY = """
    QPushButton {
        background-color: #ffffff; color: #374151;
        border: 1px solid #d1d5db; border-radius: 6px;
        padding: 8px 24px; font-weight: 600; font-size: 13px;
        min-width: 80px;
    }
    QPushButton:hover { background-color: #f3f4f6; border-color: #9ca3af; }
    QPushButton:pressed { background-color: #e5e7eb; }
"""

_BTN_DANGER = """
    QPushButton {
        background-color: #ef4444; color: white;
        border: none; border-radius: 6px;
        padding: 8px 20px; font-weight: 600; font-size: 13px;
    }
    QPushButton:hover { background-color: #dc2626; }
    QPushButton:pressed { background-color: #b91c1c; }
"""

_BTN_OUTLINE = """
    QPushButton {
        background-color: #ffffff; color: #2563eb;
        border: 1px solid #2563eb; border-radius: 6px;
        padding: 8px 20px; font-weight: 600; font-size: 13px;
    }
    QPushButton:hover { background-color: #eff6ff; }
    QPushButton:pressed { background-color: #dbeafe; }
"""

_LINE_STYLE = (
    "QLineEdit { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px; font-size: 13px; }"
    "QLineEdit:focus { border-color: #2563eb; }"
)


class LinuxLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置 Linux 自动登录")
        self.setWindowIcon(QIcon(Utils.get_ico_path()))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(_DIALOG_STYLE)
        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet(_LINE_STYLE)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Linux通常不需要密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet(_LINE_STYLE)

        self.show_password_btn = QPushButton()
        self.show_password_btn.setFixedSize(28, 28)
        self.show_password_btn.setStyleSheet("border: none; background-color: transparent; padding:0; font-size:18px;")

        self.show_password_btn.setText("\U0001F512")
        self.show_password_btn.setToolTip("显示密码")
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)

        password_layout = QHBoxLayout()
        password_layout.addWidget(self.password_edit)
        password_layout.addWidget(self.show_password_btn)
        password_layout.setContentsMargins(0, 0, 0, 0)

        self.button_clear_auto_login = QPushButton("清除")
        self.button_clear_auto_login.setStyleSheet(_BTN_DANGER)
        self.button_clear_auto_login.clicked.connect(self.clear_auto_login)

        self.button_config_sudo = QPushButton("配置sudo权限")
        self.button_config_sudo.setStyleSheet(_BTN_OUTLINE)
        self.button_config_sudo.clicked.connect(self.config_sudo_permission)

        self.sudo_status_text = QLabel("正在检查sudo权限...")
        self.sudo_status_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.sudo_status_text.setStyleSheet("color:#6b7280; font-size:13px;")

        self.credentials_status_text = QLabel("请输入账号信息")
        self.credentials_status_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.credentials_status_text.setStyleSheet("color: #d97706; font-size:13px;")

        self.install_commands_text = QTextEdit()
        self.install_commands_text.setMaximumHeight(100)
        self.install_commands_text.setReadOnly(True)
        self.install_commands_text.setPlaceholderText("sudo权限配置命令将在这里显示...")
        self.install_commands_text.setStyleSheet(
            "QTextEdit { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px; font-size: 12px; background-color:#f9fafb; }"
        )

        self.status_text = QLabel("正在检查状态...")
        self.status_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_text.setStyleSheet("font-size:13px;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        def _section_title(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("color:#374151; font-weight:700; font-size:14px; padding: 4px 0;")
            return lbl

        main_layout.addWidget(_section_title("Linux 自动登录配置"))

        def _make_row(label_text, widget, label_width=120):
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(label_width)
            lbl.setStyleSheet("color:#4b5563; font-weight:600; font-size:13px;")
            row.addWidget(lbl)
            if isinstance(widget, QLayout):
                row.addLayout(widget, 1)
            else:
                row.addWidget(widget, 1)
            main_layout.addLayout(row)

        _make_row("Linux 用户名:", self.name_edit)
        _make_row("密码 (可选):", password_layout)
        _make_row("账号状态:", self.credentials_status_text)
        _make_row("清除自动登录:", self.button_clear_auto_login)

        sep = QLabel("\u2500" * 40)
        sep.setAlignment(Qt.AlignCenter)
        sep.setStyleSheet("color: #d1d5db; margin: 4px 0;")
        main_layout.addWidget(sep)

        main_layout.addWidget(_section_title("sudo 权限配置"))
        _make_row("sudo权限状态:", self.sudo_status_text)
        _make_row("配置sudo权限:", self.button_config_sudo)
        _make_row("安装命令:", self.install_commands_text)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.status_text)
        bottom_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(_BTN_PRIMARY)
        ok_btn.clicked.connect(self.on_accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(_BTN_SECONDARY)
        cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(ok_btn)
        bottom_row.addWidget(cancel_btn)
        main_layout.addLayout(bottom_row)

        warning = QLabel("\u26A0\uFE0F 注意：此操作需要管理员权限，请确保应用以sudo或管理员身份运行\n\uD83D\uDCA1 sudo权限用于关机、睡眠等系统操作，创建定时任务前需要配置")
        warning.setStyleSheet("color: #d97706; font-size: 12px; padding: 8px; background-color: #fffbeb; border-radius: 6px;")
        warning.setWordWrap(True)
        main_layout.addWidget(warning)

        self.update_status_display()
        self.update_sudo_status_display()
        self.load_credentials()
        self.name_edit.textChanged.connect(self.validate_credentials)
        self.password_edit.textChanged.connect(self.validate_credentials)

    def values(self):
        return self.name_edit.text().strip(), self.password_edit.text().strip()

    def on_accept(self):
        try:
            username, password = self.values()
            if username:
                self.save_credentials()
                backup_path = auto_linux_login_on(username, password if password else None)
                self.update_status_display()
                self.accept()
                MessageBox("设置成功！重启系统后生效。\n备份文件已保存。")
            else:
                MessageBox("用户名不能为空！")
        except Exception as e:
            self.update_status_display()
            MessageBox(f"设置失败！\n错误：{str(e)}")

    def toggle_password_visibility(self):
        if self.password_edit.echoMode() == QLineEdit.Password:
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.show_password_btn.setText("\U0001F441")
            self.show_password_btn.setToolTip("隐藏密码")
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.show_password_btn.setText("\U0001F512")
            self.show_password_btn.setToolTip("显示密码")

    def update_status_display(self):
        enabled, status_text = check_auto_login_status()
        if enabled is True:
            self.status_text.setText("\u2705\u5DF2\u542F\u7528")
            self.status_text.setStyleSheet("color: #16a34a; font-size:13px;")
        elif enabled is False:
            self.status_text.setText("\u274C\u672A\u542F\u7528")
            self.status_text.setStyleSheet("color: #dc2626; font-size:13px;")
        else:
            self.status_text.setText("\u2753\u672A\u77E5")
            self.status_text.setStyleSheet("color: #d97706; font-size:13px;")

    def clear_auto_login(self):
        try:
            backup_path = auto_linux_login_off()
            self.update_status_display()
            MessageBox(f"清除成功！\n清除前的备份文件：{backup_path}\n重启系统后生效。")
        except Exception as e:
            self.update_status_display()
            MessageBox(f"清除失败！\n错误：{e}")

    def config_sudo_permission(self):
        try:
            username = self.name_edit.text().strip() or None
            config_path = save_sudoers_config(username)
            install_commands = get_sudo_install_commands(config_path)
            commands_text = "\n".join(install_commands)
            self.install_commands_text.setPlainText(commands_text)
            self.update_sudo_status_display()
            MessageBox(f"sudoers配置文件已生成！\n文件路径：{config_path}\n\n请在终端中执行以下命令完成安装：\n{commands_text}"
                f"\n\n显示类似如下字样则为配置成功:"
                f"\n/etc/sudoers: parsed OK\n/etc/sudoers.d/README: parsed OK\n/etc/sudoers.d/auto-clock: parsed OK")
        except Exception as e:
            MessageBox(f"配置sudo权限失败！\n错误：{str(e)}")

    def update_sudo_status_display(self):
        has_permission, status_text = check_sudo_permission()
        if has_permission is True:
            self.sudo_status_text.setText("\u2705\u5DF2\u914D\u7F6E")
            self.sudo_status_text.setStyleSheet("color: #16a34a; font-size:13px;")
        elif has_permission is False:
            self.sudo_status_text.setText("\u274C\u672A\u914D\u7F6E")
            self.sudo_status_text.setStyleSheet("color: #dc2626; font-size:13px;")
        else:
            self.sudo_status_text.setText("\u2753\u68C0\u67E5\u5931\u8D25")
            self.sudo_status_text.setStyleSheet("color: #d97706; font-size:13px;")

    def validate_credentials(self):
        username = self.name_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username:
            self.credentials_status_text.setText("请输入用户名")
            self.credentials_status_text.setStyleSheet("color: #d97706; font-size:13px;")
            return
        try:
            is_valid, status_msg = validate_linux_credentials(username, password if password else None)
            if is_valid is True:
                self.credentials_status_text.setText("\u2705\u6709\u6548")
                self.credentials_status_text.setStyleSheet("color: #16a34a; font-size:13px;")
            elif is_valid is False:
                self.credentials_status_text.setText("\u26A0\uFE0F\u65E0\u6548")
                self.credentials_status_text.setStyleSheet("color: #dc2626; font-size:13px;")
                self.credentials_status_text.setToolTip(status_msg)
            else:
                self.credentials_status_text.setText("\u2753\u672A\u77E5")
                self.credentials_status_text.setStyleSheet("color: #d97706; font-size:13px;")
                self.credentials_status_text.setToolTip(status_msg)
        except Exception as e:
            self.credentials_status_text.setText("\u26A0\uFE0F\u9A8C\u8BC1\u5931\u8D25")
            self.credentials_status_text.setStyleSheet("color: #dc2626; font-size:13px;")
            self.credentials_status_text.setToolTip(f"验证出错：{str(e)}")

    def get_credentials_status(self):
        username = self.name_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username:
            return False, "未配置用户名"
        try:
            is_valid, status_msg = validate_linux_credentials(username, password if password else None)
            return is_valid, status_msg
        except Exception as e:
            return False, f"验证失败：{str(e)}"

    def load_credentials(self):
        try:
            if os.path.exists(AppPath.DataJson):
                data = Utils.read_dict_from_json(AppPath.DataJson)
                if data:
                    self.name_edit.setText(data.get(Key.LinuxUserName, ""))
                    self.validate_credentials()
        except Exception as e:
            from src.utils.log import Log
            Log.warning(f"加载Linux账号信息失败: {str(e)}")

    def save_credentials(self):
        try:
            username = self.name_edit.text().strip()
            if username:
                data = {}
                if os.path.exists(AppPath.DataJson):
                    data = Utils.read_dict_from_json(AppPath.DataJson) or {}
                data[Key.LinuxUserName] = username
                Utils.write_dict_to_file(AppPath.DataJson, data)
                from src.utils.log import Log
                Log.info("Linux账号信息已保存")
        except Exception as e:
            from src.utils.log import Log
            Log.warning(f"保存Linux账号信息失败: {str(e)}")
