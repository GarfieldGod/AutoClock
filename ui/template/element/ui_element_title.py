from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication


class TitleBarArea(QWidget):
    def __init__(self,
                 title_text: str, title_desc:str, title_bar_height,
                 show_min_button, show_max_button, show_close_button,
                 window, parent=None):
        super(TitleBarArea, self).__init__(parent)
        if window is None:
            raise Exception("Parent widget cannot be None for TitleBar.")
        self.title_text = title_text
        self.title_desc = title_desc
        self.title_bar_height = title_bar_height
        self.show_min_button = show_min_button
        self.show_max_button = show_max_button
        self.show_close_button = show_close_button
        self.this_parent = window

        self.min_btn = QPushButton("-")
        self.max_btn = QPushButton("□")
        self.close_btn = QPushButton("×")

        self.title_layout = QHBoxLayout(self)
        self.button_layout = QHBoxLayout()
        self.init_ui()

    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(self.title_bar_height)
        self.setObjectName("TitleBar")

        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(0)

        self.init_title_label()

        self.button_layout.setContentsMargins(0, 0, 10, 0)
        self.button_layout.setSpacing(10)

        if self.show_min_button:
            self.init_min_button()
        if self.show_max_button:
            self.init_max_button()
        if self.show_close_button:
            self.init_close_button()

        self.title_layout.addLayout(self.button_layout)

    def init_title_label(self):
        title_label = QLabel(self.title_text)
        title_label.setObjectName("title_label")
        self.title_layout.addWidget(title_label)

        title_desc = QLabel(self.title_desc)
        title_desc.setObjectName("title_desc")

        self.title_layout.addWidget(title_desc, stretch=1)

    def init_min_button(self):
        self.min_btn.setFixedSize(28, 28)
        self.min_btn.setObjectName("min_btn")
        self.min_btn.clicked.connect(self.this_parent.showMinimized)
        self.button_layout.addWidget(self.min_btn)

    def init_max_button(self):
        self.max_btn.setFixedSize(28, 28)
        self.max_btn.setObjectName("max_btn")
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.button_layout.addWidget(self.max_btn)

    def init_close_button(self):
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setObjectName("close_btn")
        self.close_btn.clicked.connect(self.this_parent.on_window_close)
        self.button_layout.addWidget(self.close_btn)

    is_maximized = False
    is_dragging = False
    normal_geometry = None
    drag_start_pos = QPoint()
    def toggle_maximize(self):
        try:
            print()
            if not self.is_maximized:
                self.is_maximized = True
                self.max_btn.setText("▢")
                self.max_btn.setChecked(True)
                self.normal_geometry = self.this_parent.frameGeometry()
                self.this_parent.setGeometry(QApplication.desktop().availableGeometry())
            else:
                self.is_maximized = False
                self.max_btn.setText("□")
                self.max_btn.setChecked(False)
                self.this_parent.setGeometry(self.normal_geometry)
        except Exception as e:
            print(e)