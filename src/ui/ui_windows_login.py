from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton, QLineEdit, QDialog, QHBoxLayout, QLabel, QVBoxLayout, QLayout
from PyQt5.QtCore import Qt

from src.utils.utils import Utils
from src.ui.ui_message import MessageBox
from src.extend.auto_windows_login import auto_windows_login_off, auto_windows_login_on, check_auto_login_status

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

_LINE_STYLE = (
    "QLineEdit { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px; font-size: 13px; }"
    "QLineEdit:focus { border-color: #2563eb; }"
)


class WindowsLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Windows Auto Login")
        self.setWindowIcon(QIcon(Utils.get_ico_path()))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(_DIALOG_STYLE)
        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet(_LINE_STYLE)
        self.password_edit = QLineEdit()
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

        self.button_clear_auto_login = QPushButton("Clear")
        self.button_clear_auto_login.setStyleSheet(_BTN_DANGER)
        self.button_clear_auto_login.clicked.connect(self.clear_auto_login)

        self.status_text = QLabel("正在检查状态...")
        self.status_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_text.setStyleSheet("font-size:13px;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        def _make_row(label_text, widget):
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(160)
            lbl.setStyleSheet("color:#4b5563; font-weight:600; font-size:13px;")
            row.addWidget(lbl)
            if isinstance(widget, QLayout):
                row.addLayout(widget, 1)
            else:
                row.addWidget(widget, 1)
            main_layout.addLayout(row)

        _make_row("Windows User Name:", self.name_edit)
        _make_row("Windows User Password:", password_layout)
        _make_row("Clear Auto Login:", self.button_clear_auto_login)

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

        self.update_status_display()

    def values(self):
        return self.name_edit.text().strip(), self.password_edit.text().strip()

    def on_accept(self):
        try:
            username, password = self.values()
            if username:
                backup_path = auto_windows_login_on(username, password)
                self.update_status_display()
                self.accept()
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
            backup_path = auto_windows_login_off()
            self.update_status_display()
            MessageBox(f"Clear Success!\nbackup before clear: {backup_path}")
        except Exception as e:
            self.update_status_display()
            MessageBox(f"Clear Failed!\nError: {e}")
