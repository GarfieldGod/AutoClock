from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout

from ui.template.ui_custom_function import load_local_image


class AppIconArea(QWidget):
    def __init__(self, icon_path, size=QSize(50, 50), parent=None):
        super(AppIconArea, self).__init__(parent)
        self.icon_size = size
        self.icon_path = icon_path

        self.icon_label = QLabel()

        self.init_ui()

    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(self.icon_size)

        self.icon_label.setFixedSize(self.icon_size)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.icon_label)
        load_local_image(self.icon_label, self.icon_path)