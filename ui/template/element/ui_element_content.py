from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QStackedWidget


class ContentArea(QStackedWidget):
    def __init__(self, parent=None):
        super(ContentArea, self).__init__(parent)

        self.init_ui()

    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("Content")