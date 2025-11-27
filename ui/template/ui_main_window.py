import os

from PyQt5.QtCore import Qt, QRectF, QSize, QPoint
from PyQt5.QtGui import QPainter, QBrush, QPainterPath, QPixmap
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QListWidgetItem,
                             QStackedWidget, QLabel, QPushButton, QApplication)

from ui.template.element.ui_element_content import ContentArea
from ui.template.element.ui_element_icon import AppIconArea
from ui.template.element.ui_element_navigation import NavigationArea
from ui.template.element.ui_element_space import SpaceArea
from ui.template.element.ui_element_title import TitleBarArea
from ui.template.ui_page import PageContent, PageNavigation
from ui.template.ui_custom_color import CustomColor


class MainWindow(QMainWindow):
    title_bar_background_color = CustomColor.white_253_254_249
    space_background_color = CustomColor.white_253_254_249
    navigation_background_color = CustomColor.dark_87_90_95
    content_background_color = CustomColor.yellow_247_243_232

    def __init__(
            self, title_text="", title_desc="", icon_path="", window_size=QSize(640, 480),
            show_min_button=True,show_max_button=True,show_close_button=True,
            navigation_width=90, title_bar_height=50, space_width=60,
            round_radius=25, window_padding=0
                 ):
        super().__init__()
        try:
            # data
            self.title_text = title_text
            self.title_desc = title_desc
            self.icon_path = icon_path
            self.window_size = window_size
            self.navigation_width = navigation_width
            self.title_bar_height = title_bar_height
            self.space_width = space_width
            self.round_radius = round_radius
            self.window_padding = window_padding

            # const data
            self.title_bar_background_height = title_bar_height + window_padding
            self.navigation_background_width = navigation_width + window_padding
            self.content_background_left = self.navigation_background_width + space_width
            self.content_background_top = self.title_bar_background_height

            # elements
            self.central_widget = QWidget()
            self.app_icon = AppIconArea(50,50)
            self.navigation = NavigationArea(self.navigation_width)
            self.title_bar = TitleBarArea(
                title_text=self.title_text,
                title_desc=self.title_desc,
                title_bar_height=self.title_bar_height,
                show_min_button=show_min_button,
                show_max_button=show_max_button,
                show_close_button=show_close_button,
                window=self)
            self.space = SpaceArea(self.space_width)
            self.content = ContentArea()

            # init
            self.init_window()
            self.load_qss()
        except Exception as e:
            print(e)

    def init_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(self.window_size)

        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(self.window_padding, self.window_padding, self.window_padding, self.window_padding)
        main_layout.setSpacing(0)

        content_main_layout = QVBoxLayout()
        content_main_layout.setContentsMargins(0, 0, 0, 0)
        content_main_layout.setSpacing(0)

        content_bottom_layout = QHBoxLayout()
        content_bottom_layout.setContentsMargins(0, 0, 0, 0)
        content_bottom_layout.setSpacing(0)
        content_bottom_layout.addWidget(self.space)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.content)

        content_bottom_layout.addLayout(content_layout)

        content_main_layout.addWidget(self.title_bar)
        content_main_layout.addLayout(content_bottom_layout)

        navigation_layout = QVBoxLayout()
        navigation_layout.setContentsMargins(0, 0, 0, 0)
        navigation_layout.setSpacing(0)
        navigation_layout.addWidget(self.app_icon)
        navigation_layout.addWidget(self.navigation)

        main_layout.addLayout(navigation_layout)
        main_layout.addLayout(content_main_layout)

    def load_qss(self):
        qss_path = os.path.join(os.path.dirname(__file__), "ui_main_window.qss")
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                qss_content = f.read()
            self.setStyleSheet(qss_content)
        except FileNotFoundError:
            print(f"错误：未找到 QSS 文件 {qss_path}")
        except Exception as e:
            print(f"加载 QSS 失败：{e}")

    def add_page(self, navigation, page):
        if not isinstance(navigation, PageNavigation) or not isinstance(page, PageContent):
            raise Exception("invalid navigation or page")

        navigation_item = QListWidgetItem()
        navigation_item.setSizeHint(QSize(60, 60))
        self.navigation.addItem(navigation_item)
        self.navigation.setItemWidget(navigation_item, navigation)
        self.navigation.itemClicked.connect(self.switch_page)

        self.navigation.setCurrentRow(0)
        self.content.addWidget(page)

        if self.navigation.count() == 1:
            self.switch_page(0)

    def switch_page(self, item):
        try:
            if isinstance(item, QListWidgetItem):
                current_index = self.navigation.row(item)
            elif isinstance(item, int):
                current_index = item
            else:
                raise Exception("invalid item")

            for index in range(self.navigation.count()):
                item = self.navigation.item(index)
                temp_navigation = self.navigation.itemWidget(item)
                if index == current_index:
                    temp_navigation.set_background_color(self.space_background_color)
                    temp_navigation.show_clicked()
                else:
                    temp_navigation.set_background_color(self.navigation_background_color)
                    temp_navigation.show_not_clicked()

            current_page = self.content.currentWidget()
            target_page = self.content.widget(current_index)

            # fade_out = QPropertyAnimation(current_page, b"windowOpacity")
            # fade_out.setDuration(3000)  # 动画时长（毫秒）
            # fade_out.setStartValue(1.0)
            # fade_out.setEndValue(0.0)
            # fade_out.setEasingCurve(QEasingCurve.InOutQuad)  # 缓动曲线
            #
            # # 显示目标页面（淡入）
            # fade_in = QPropertyAnimation(target_page, b"windowOpacity")
            # fade_in.setDuration(3000)
            # fade_in.setStartValue(0.0)
            # fade_out.setEndValue(1.0)
            # fade_in.setEasingCurve(QEasingCurve.InOutQuad)
            #
            # # 执行动画并切换页面
            # fade_out.start()
            # fade_in.start()
            self.content.setCurrentIndex(current_index)
        except Exception as e:
            print(e)

    def mousePressEvent(self, event):
        title_bar = self.title_bar
        if title_bar.is_maximized:
            return
        try:
            if event.button() == Qt.LeftButton and title_bar.geometry().contains(event.pos()):
                title_bar.is_dragging = True
                title_bar.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
        except Exception as e:
            print(e)

    def mouseMoveEvent(self, event):
        title_bar = self.title_bar
        try:
            if title_bar.is_dragging and event.buttons() & Qt.LeftButton:
                self.move(event.globalPos() - title_bar.drag_start_pos)
                event.accept()
        except Exception as e:
            print(e)

    def mouseReleaseEvent(self, event):
        title_bar = self.title_bar
        try:
            if event.button() == Qt.LeftButton:
                title_bar.is_dragging = False
                event.accept()
        except Exception as e:
            print(e)

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(Qt.NoPen)

            widget_rect = self.rect()
            path = QPainterPath()
            path.addRoundedRect(
                QRectF(widget_rect),
                self.round_radius,
                self.round_radius
            )
            painter.setClipPath(path)

            split_width = self.navigation_background_width

            left_rect = QRectF(
                0,
                0,
                split_width,
                widget_rect.height()
            )
            painter.fillRect(left_rect, QBrush(self.navigation_background_color))

            right_rect = QRectF(
                split_width,
                0,
                widget_rect.width() - split_width,
                self.title_bar_background_height
            )
            painter.fillRect(right_rect, QBrush(self.title_bar_background_color))

            # 绘制space背景
            right_rect = QRectF(
                split_width,  # 左边界
                self.title_bar_height,  # 上边界
                self.space_width,  # 宽度
                widget_rect.height() - self.title_bar_height  # 高度
            )
            painter.fillRect(right_rect, QBrush(self.space_background_color))

            # 绘制content背景
            right_rect = QRectF(
                self.content_background_left,  # 左边界
                self.content_background_top,  # 上边界
                widget_rect.width() - self.content_background_left,  # 宽度
                widget_rect.height() - self.content_background_top  # 高度
            )
            painter.fillRect(right_rect, QBrush(self.content_background_color))
        except Exception as e:
            print(e)