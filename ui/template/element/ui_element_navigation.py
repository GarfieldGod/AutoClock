from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidget


class NavigationArea(QListWidget):
    def __init__(self, width, parent=None):
        super(NavigationArea, self).__init__(parent)

        self.navigation_width = width
        self.init_ui()

    def init_ui(self):
        self.setFixedWidth(self.navigation_width)
        self.setObjectName("Navigation")
        self.setFocusPolicy(Qt.NoFocus)