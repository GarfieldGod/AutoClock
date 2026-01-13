from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit, QCheckBox, QWidget, QHBoxLayout

from src.utils.const import Key
from src.utils.utils import QtUI, Utils


class LineEdit(QLineEdit):
    def __init__(self, key, default="", parent=None):
        super(LineEdit, self).__init__(parent)
        self.key = key
        self.default = default

    def value_changed_func(self, set_func):
        try:
            self.textChanged.connect(lambda : set_func(self.key, self.text()))
        except Exception as e:
            print(e)

    def set_value(self, value):
        self.setText(str(value))

class CheckBox(QCheckBox):
    def __init__(self, key, default=False, parent=None):
        super(CheckBox, self).__init__(parent)
        self.key = key
        self.default = default

    def value_changed_func(self, set_func):
        self.toggled.connect(lambda : set_func(self.key, self.isChecked()))

    def set_value(self, value):
        self.setChecked(value)

class TaskListWidget(QWidget):
    def __init__(self, task, parent=None):
        super(TaskListWidget, self).__init__(parent)
        self.init_ui(task)

    def init_ui(self, task):
        self.setObjectName(task[Key.TaskID])
        layout_plan_line = QHBoxLayout(self)
        layout_plan_line.setContentsMargins(0, 0, 0, 0)
        layout_plan_line.setAlignment(Qt.AlignCenter | Qt.AlignLeft)
        front_size = 8
        label_alignment = Qt.AlignLeft
        label_p = QtUI.create_label(Utils.truncate_text(task[Key.TaskName], 15),size=front_size, fixed_width=140)
        layout_plan_line.addWidget(label_p)
        label_o = QtUI.create_label(Utils.truncate_text(task[Key.Operation], 10),size=front_size, alignment=label_alignment, fixed_width=80)
        layout_plan_line.addWidget(label_o)
        label_t = QtUI.create_label(task[Key.TriggerType], size=front_size, alignment=label_alignment, fixed_width=50)
        layout_plan_line.addWidget(label_t)
        label_et = QtUI.create_label(task[Key.ExecuteTime],size=front_size, alignment=Qt.AlignCenter, fixed_width=50)
        layout_plan_line.addWidget(label_et)
        if task[Key.TriggerType] == Key.Once:
            layout_plan_line.addWidget(QtUI.create_label(task[Key.ExecuteDay],size=front_size, alignment=Qt.AlignCenter, fixed_width=80))
        elif task[Key.TriggerType] == Key.Weekly:
            layout_plan_line.addWidget(QtUI.create_label(task[Key.ExecuteDay],size=front_size, alignment=Qt.AlignCenter, fixed_width=80))
        elif task[Key.TriggerType] == Key.Monthly:
            layout_plan_line.addWidget(QtUI.create_label(task[Key.ExecuteDay],size=front_size, alignment=Qt.AlignCenter, fixed_width=80))
        elif task[Key.TriggerType] == Key.SmartHoliday:
            layout_plan_line.addWidget(QtUI.create_label("Smart", size=front_size, alignment=Qt.AlignCenter, fixed_width=80))
        elif task[Key.TriggerType] == Key.Multiple:
            layout_plan_line.addWidget(QtUI.create_label("[······]",size=front_size, alignment=Qt.AlignCenter, fixed_width=80))
            pass
