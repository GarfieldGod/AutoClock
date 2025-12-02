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