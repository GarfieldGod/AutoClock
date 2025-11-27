from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget


class AppIconArea(QWidget):
    def __init__(self, width: int, height: int, parent=None):
        super(AppIconArea, self).__init__(parent)
        self.icon_width = width
        self.icon_height = height

        self.init_ui()

    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        # self.app_icon.setPixmap(QPixmap("icon.png"))
        self.setFixedSize(self.icon_width, self.icon_height)