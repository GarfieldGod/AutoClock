from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QDialogButtonBox, QHBoxLayout, QVBoxLayout, QLabel, QDialog, QPushButton

from src.utils.utils import Utils


class _MessageDialog(QDialog):
    def __init__(self, message, message_name="Message", parent=None, need_check=False, buttons=None):
        super().__init__(parent)
        self.setWindowTitle(message_name)
        self.setWindowIcon(QIcon(Utils.get_ico_path()))

        self.clicked_button_text = None

        label = QLabel(str(message))
        font = QFont()
        font.setFamily("Consolas")
        font.setPointSize(10)
        label.setFont(font)
        label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        # 允许文本选择和复制
        label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)

        layout_center_label = QHBoxLayout()
        layout_center_label.addStretch(1)
        layout_center_label.addWidget(label)
        layout_center_label.addStretch(1)

        layout_center_button = QHBoxLayout()
        layout_center_button.addStretch(1)

        if buttons is not None and isinstance(buttons, (list, tuple)) and len(buttons) > 0:
            # 自定义按钮列表
            for text in buttons:
                btn = QPushButton(str(text))
                btn.clicked.connect(lambda checked, t=text: self._on_custom_button_clicked(t))
                layout_center_button.addWidget(btn)
        else:
            # 兼容原有的 Ok / Ok+Cancel 模式
            if need_check:
                button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button.rejected.connect(self.reject)
            else:
                button = QDialogButtonBox(QDialogButtonBox.Ok)
            button.accepted.connect(self.accept)
            layout_center_button.addWidget(button)

        layout_center_button.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addLayout(layout_center_label)
        layout.addStretch()
        layout.addLayout(layout_center_button)

    def _on_custom_button_clicked(self, text):
        self.clicked_button_text = text
        self.accept()


def MessageBox(message, message_name="Message", parent=None, need_check=False, message_only=True, buttons=None):
    """通用消息框工具

    行为兼容旧代码：
    - 无 buttons:
        - message_only=True: 立即显示对话框并阻塞，返回对话框对象（通常被忽略）。
        - message_only=False: 返回对话框对象，由调用方自行调用 exec_()。
    - 有 buttons（列表）:
        - 立即显示对话框并阻塞，返回用户点击的按钮文本（str）。
    """
    dlg = _MessageDialog(message, message_name=message_name, parent=parent, need_check=need_check, buttons=buttons)

    if buttons is not None and isinstance(buttons, (list, tuple)) and len(buttons) > 0:
        # 选择型对话框：返回所选按钮文本
        dlg.exec_()
        return dlg.clicked_button_text

    # 保持原有语义：message_only=True 时在内部立即 exec
    if message_only:
        dlg.exec_()

    return dlg