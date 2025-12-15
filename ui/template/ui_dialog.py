import os
import sys

from PyQt5.QtCore import Qt, QRectF, QSize
from PyQt5.QtGui import QBrush, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLineEdit, QComboBox, QApplication, QSpacerItem, \
    QPushButton, QHBoxLayout, QSizePolicy

from ui.template.element.ui_element_title import TitleBarArea
from ui.template.ui_custom_color import CustomColor
from ui.template.ui_custom_function import get_ui_resource_path


class Dialog(QDialog):
    round_radius = 15
    background_color = CustomColor.white_253_254_249
    title_color = CustomColor.dark_87_90_95
    border_width = 1
    border_color = CustomColor.dark_87_90_95
    def __init__(self, title_text, title_height=50,
                 show_confirm_button=True, show_cancel_button=True, button_right=True, button_size=QSize(80,40),
                 parent=None):
        super().__init__(parent)

        self.setObjectName("Dialog")
        self.setMinimumWidth(500)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.title_bar_height = title_height
        self.content = None

        self.show_confirm = show_confirm_button
        self.show_cancel = show_cancel_button
        self.button_right = button_right

        self.title_bar = TitleBarArea(
            title_text=title_text,
            title_desc="",
            title_bar_height=self.title_bar_height,
            show_min_button=False,
            show_max_button=False,
            show_close_button=False,
            window=self)

        self.confirm_button = QPushButton("confirm")
        self.confirm_button.setFixedSize(button_size)
        if not show_confirm_button: self.confirm_button.hide()
        self.cancel_button = QPushButton("cancel")
        self.cancel_button.setFixedSize(button_size)
        if not show_cancel_button: self.cancel_button.hide()
        self.confirm_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.init_content_widget()
        self.init_layout()
        self.load_qss()

    def init_content_widget(self):
        pass

    def show_confirm_button(self):
        self.confirm_button.show()

    def show_cancel_button(self):
        self.cancel_button.show()

    def init_layout(self):
        widget_layout = QVBoxLayout(self)
        widget_layout.setSpacing(0)
        widget_layout.setContentsMargins(0,0,0,0)
        widget_layout.addWidget(self.title_bar)
        if self.content is not None:
            widget_layout.addWidget(self.content)

        button_layout = QHBoxLayout()
        if self.show_confirm and self.show_cancel and self.button_right:
            button_layout.addStretch(4)
        button_layout.addStretch(1)
        button_layout.addWidget(self.confirm_button)
        if self.show_confirm and self.show_cancel:
            button_layout.addStretch(1)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch(1)

        widget_layout.addLayout(button_layout)
        widget_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum))

    def values(self):
        pass

    def load_qss(self):
        qss_path = os.path.join(get_ui_resource_path(), "qss", "ui_main_window.qss")
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                qss_content = f.read()
            self.setStyleSheet(qss_content)
        except FileNotFoundError:
            print(f"错误：未找到 QSS 文件 {qss_path}")
        except Exception as e:
            print(f"加载 QSS 失败：{e}")

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


            right_rect = QRectF(
                0,  # 左边界
                0,  # 上边界
                widget_rect.width(),  # 宽度
                self.title_bar_height  # 高度
            )
            painter.fillRect(right_rect, QBrush(self.title_color))

            # 绘制content背景
            right_rect = QRectF(
                0,  # 左边界
                self.title_bar_height,  # 上边界
                widget_rect.width(),  # 宽度
                widget_rect.height() - self.title_bar_height  # 高度
            )
            painter.fillRect(right_rect, QBrush(self.background_color))

            if self.border_width > 0:  # 边框宽度>0才绘制
                painter.setPen(QPen(
                    self.border_color,  # 边框颜色
                    self.border_width,  # 边框宽度
                    Qt.SolidLine,  # 边框样式（实线）
                    Qt.RoundCap,  # 线帽圆角（避免边框端点尖锐）
                    Qt.RoundJoin  # 线连接圆角（避免边框转角尖锐）
                ))
                painter.setBrush(Qt.NoBrush)  # 边框不需要填充
                painter.drawPath(path)  # 沿着圆角路径画边框
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = Dialog("111")
    if dlg.exec_() == QDialog.Accepted:
        print(1)
    sys.exit(app.exec_())