from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel


class QtUI:
    @staticmethod
    def create_label(message, size=11, length=150, family="Arial", width_policy=None, height_policy=None,
                     alignment=None, fixed_width=None, fixed_height=None):
        label = QLabel(message)
        font = QFont()
        font.setFamily(family)
        font.setPointSize(size)
        label.setFont(font)
        label.setFixedWidth(length)
        if width_policy is not None and height_policy is not None:
            label.setSizePolicy(width_policy, height_policy)
        if alignment is not None:
            label.setAlignment(alignment)
        if fixed_width is not None:
            label.setFixedWidth(fixed_width)
        if fixed_height is not None:
            label.setFixedHeight(fixed_height)
        return label
