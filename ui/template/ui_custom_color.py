from dataclasses import dataclass

from PyQt5.QtGui import QColor

@dataclass
class CustomColor:
    dark_mode = False
    if dark_mode:
        dark_87_90_95 = QColor(25,25,25)
        white_253_254_249 = QColor(75,75,75)
        yellow_247_243_232 = QColor(50,50,50)
    else:
        dark_87_90_95 = QColor(87,90,95)
        white_253_254_249 = QColor(253,254,249)
        yellow_247_243_232 = QColor(247,243,232)