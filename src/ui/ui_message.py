from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QDialog, QPushButton

from src.utils.utils import Utils


_DIALOG_STYLE = """
    QDialog {
        background-color: #ffffff;
        border-radius: 12px;
    }
"""

_BTN_PRIMARY = """
    QPushButton {
        background-color: #2563eb; color: white;
        border: none; border-radius: 6px;
        padding: 8px 20px; font-weight: 600; font-size: 13px;
        min-width: 80px;
    }
    QPushButton:hover { background-color: #1d4ed8; }
    QPushButton:pressed { background-color: #1e40af; }
"""

_BTN_SECONDARY = """
    QPushButton {
        background-color: #ffffff; color: #374151;
        border: 1px solid #d1d5db; border-radius: 6px;
        padding: 8px 20px; font-weight: 600; font-size: 13px;
        min-width: 80px;
    }
    QPushButton:hover { background-color: #f3f4f6; border-color: #9ca3af; }
    QPushButton:pressed { background-color: #e5e7eb; }
"""


class _MessageDialog(QDialog):
    def __init__(self, message, message_name="Message", parent=None, need_check=False, buttons=None):
        super().__init__(parent)
        self.setWindowTitle(message_name)
        self.setWindowIcon(QIcon(Utils.get_ico_path()))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(_DIALOG_STYLE)

        self.clicked_button_text = None

        label = QLabel(str(message))
        font = QFont()
        font.setFamily("Consolas")
        font.setPointSize(10)
        label.setFont(font)
        label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        label.setWordWrap(True)
        label.setMinimumWidth(300)
        label.setMaximumWidth(500)
        label.setStyleSheet("color:#374151; padding:12px 8px;")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)

        layout_center_label = QHBoxLayout()
        layout_center_label.addStretch(1)
        layout_center_label.addWidget(label)
        layout_center_label.addStretch(1)

        layout_center_button = QHBoxLayout()
        layout_center_button.addStretch(1)

        if buttons is not None and isinstance(buttons, (list, tuple)) and len(buttons) > 0:
            for i, text in enumerate(buttons):
                btn = QPushButton(str(text))
                btn.setStyleSheet(_BTN_PRIMARY if i == 0 else _BTN_SECONDARY)
                btn.clicked.connect(lambda checked, t=text: self._on_custom_button_clicked(t))
                layout_center_button.addWidget(btn)
        else:
            if need_check:
                ok_btn = QPushButton("OK")
                ok_btn.setStyleSheet(_BTN_PRIMARY)
                cancel_btn = QPushButton("Cancel")
                cancel_btn.setStyleSheet(_BTN_SECONDARY)
                ok_btn.clicked.connect(self.accept)
                cancel_btn.clicked.connect(self.reject)
                layout_center_button.addWidget(ok_btn)
                layout_center_button.addWidget(cancel_btn)
            else:
                ok_btn = QPushButton("OK")
                ok_btn.setStyleSheet(_BTN_PRIMARY)
                ok_btn.clicked.connect(self.accept)
                layout_center_button.addWidget(ok_btn)

        layout_center_button.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addLayout(layout_center_label)
        layout.addStretch()
        layout.addLayout(layout_center_button)

    def _on_custom_button_clicked(self, text):
        self.clicked_button_text = text
        self.accept()


def MessageBox(message, message_name="Message", parent=None, need_check=False, message_only=True, buttons=None):
    dlg = _MessageDialog(message, message_name=message_name, parent=parent, need_check=need_check, buttons=buttons)

    if buttons is not None and isinstance(buttons, (list, tuple)) and len(buttons) > 0:
        dlg.exec_()
        return dlg.clicked_button_text

    if message_only:
        dlg.exec_()

    return dlg
