import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap


def load_local_image(image_label, image_path, default_value=""):
    pixmap = QPixmap(image_path)

    if pixmap.isNull():
        image_label.setText(default_value)
        return

    scaled_pixmap = pixmap.scaled(
        image_label.size(),
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

    image_label.setPixmap(scaled_pixmap)

def get_ui_resource_path():
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        base_path = os.path.dirname(parent_dir)

    return os.path.join(base_path, "ui", "resource")