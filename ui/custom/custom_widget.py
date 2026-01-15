from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit, QCheckBox, QWidget, QHBoxLayout, QPushButton, QFileDialog, QComboBox

from src.utils.const import Key
from src.utils.utils import QtUI, Utils
from src.utils.const import AppPath


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


class PasswordLineEdit(LineEdit):
    def __init__(self, key, default="", parent=None):
        super(PasswordLineEdit, self).__init__(key, default=default, parent=parent)
        self.setEchoMode(QLineEdit.Password)


class FileSelectLineEdit(QWidget):
    def __init__(self, key, default="", parent=None):
        super(FileSelectLineEdit, self).__init__(parent)
        self.key = key
        self.default = default

        self._line = QLineEdit()
        self._btn = QPushButton("...")
        self._btn.setFixedWidth(30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._line)
        layout.addWidget(self._btn)

        self._set_func = None
        self._line.textChanged.connect(self._on_text_changed)
        self._btn.clicked.connect(self._choose_file)

    def _on_text_changed(self):
        if self._set_func is not None:
            self._set_func(self.key, self._line.text())

    def value_changed_func(self, set_func):
        self._set_func = set_func

    def set_value(self, value):
        self._line.setText(str(value) if value is not None else "")

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", "")
        if not path:
            return

        try:
            import os
            import shutil
            from pathlib import Path

            keys_dir = Path(AppPath.DataRoot) / "ssh_keys"
            keys_dir.mkdir(parents=True, exist_ok=True)
            target = keys_dir / Path(path).name
            shutil.copy2(path, target)
            self._line.setText(str(target))
        except Exception:
            self._line.setText(path)

class CheckBox(QCheckBox):
    def __init__(self, key, default=False, parent=None):
        super(CheckBox, self).__init__(parent)
        self.key = key
        self.default = default

    def value_changed_func(self, set_func):
        self.toggled.connect(lambda : set_func(self.key, self.isChecked()))

    def set_value(self, value):
        self.setChecked(value)


class ComboBox(QComboBox):
    def __init__(self, key, items: list[str], default: str = "", parent=None):
        super(ComboBox, self).__init__(parent)
        self.key = key
        self.default = default
        self._set_func = None

        for it in items:
            self.addItem(str(it))

        self.currentTextChanged.connect(self._on_changed)

    def _on_changed(self, _text: str):
        if self._set_func is not None:
            self._set_func(self.key, self.currentText())

    def value_changed_func(self, set_func):
        self._set_func = set_func

    def set_value(self, value):
        text = str(value) if value is not None else ""
        idx = self.findText(text)
        if idx >= 0:
            self.setCurrentIndex(idx)
            return
        idx = self.findText(str(self.default))
        if idx >= 0:
            self.setCurrentIndex(idx)

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
