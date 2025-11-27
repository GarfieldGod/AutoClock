from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget


class SpaceArea(QWidget):
    def __init__(self, width: int, parent=None):
        super(SpaceArea, self).__init__(parent)
        self.space_width = width

        self.init_ui()

    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(self.space_width)
        self.setObjectName("Space")