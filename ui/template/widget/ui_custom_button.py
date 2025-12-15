from PyQt5.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QColor
import sys

class PushButton(QPushButton):
    def __init__(self, text="",
                 color_default=QColor("#FFFFFF"),
                 border_default=1,
                 radius_default=5,
                 font_size_default=14,
                 border_color_default=QColor("#9C9C9C"),
                 font_color_default=QColor("#000000"),
                 duration=300,
                 color_hover=QColor("#DEEDFE"),
                 border_hover=None,
                 radius_hover=None,
                 font_size_hover=None,
                 border_color_hover=QColor("#5BA1F4"),
                 font_color_hover=None,
                 padding="10px 20px",
                 parent=None):
        super().__init__(text, parent)
        self._color = color_default
        self._border = border_default
        self._radius = radius_default
        self._font_size = font_size_default
        self._border_color = border_color_default
        self._font_color = font_color_default

        self.padding = padding

        self.default_value = [ # default value
            color_default,
            border_default,
            radius_default,
            font_size_default,
            border_color_default,
            font_color_default,
        ]

        self.hover_value = [ # hover value
            color_hover if color_hover else color_default,
            border_hover if border_hover else border_default,
            radius_hover if radius_hover else radius_default,
            font_size_hover if font_size_hover else font_size_default,
            border_color_hover if border_color_hover else border_color_default,
            font_color_hover if font_color_hover else font_color_default,
        ]

        props = [b"color", b"border", b"radius", b"font_size", b"border_color", b"font_color"] # props
        self.animations = []
        for prop in props:
            animation = QPropertyAnimation(self, prop)
            animation.setDuration(duration)
            animation.setEasingCurve(QEasingCurve.InOutQuad)
            self.animations.append(animation)

        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                border: {self._border}px solid {self._border_color.name()};
                color: {self._font_color.name()};
                padding: {self.padding};
                font-size: {self._font_size}px;
                border-radius: {self._radius}px;
            }}
        """)

    def get_snapshot(self):
        snapshot = [
            self._color,
            self._border,
            self._radius,
            self._font_size,
            self._border_color,
            self._font_color
        ]
        return snapshot

    @pyqtProperty(QColor)
    def font_color(self):
        return self._font_color

    @font_color.setter
    def font_color(self, value):
        self._font_color = value
        self._update_style()

    @pyqtProperty(QColor)
    def border_color(self):
        return self._border_color

    @border_color.setter
    def border_color(self, value):
        self._border_color = value
        self._update_style()

    @pyqtProperty(int)
    def font_size(self):
        return self._font_size

    @font_size.setter
    def font_size(self, value):
        self._font_size = value
        self._update_style()

    @pyqtProperty(QColor)
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self._update_style()

    @pyqtProperty(int)
    def border(self):
        return self._border

    @border.setter
    def border(self, value):
        self._border = value
        self._update_style()

    @pyqtProperty(int)
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, value):
        self._radius = value
        self._update_style()

    def enterEvent(self, event):
        try:
            snap = self.get_snapshot()
            for index in range(len(self.animations)):
                self.animations[index].stop()
                self.animations[index].setStartValue(snap[index])
                self.animations[index].setEndValue(self.hover_value[index])
                self.animations[index].start()
        except Exception as e:
            print(e)
        super().enterEvent(event)

    def leaveEvent(self, event):
        try:
            snap = self.get_snapshot()
            for index in range(len(self.animations)):
                self.animations[index].stop()
                self.animations[index].setStartValue(snap[index])
                self.animations[index].setEndValue(self.default_value[index])
                self.animations[index].start()
        except Exception as e:
            print(e)
        super().leaveEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout()
    btn = PushButton(
        text="Hover Me!",
        color_default = QColor("#4CAF50"),
        border_default = 1,
        radius_default = 0,
        font_size_default = 14,
        border_color_default = QColor("#673AB7"),
        font_color_default = QColor("#673AB7"),
        color_hover=QColor("#673AB7"),
        border_hover=3,
        radius_hover=10,
        font_size_hover=16,
        border_color_hover=QColor("#4CAF50"),
        font_color_hover=QColor("#4CAF50"),
        duration=300
    )
    layout.addWidget(btn)
    window.setLayout(layout)
    window.show()
    sys.exit(app.exec_())