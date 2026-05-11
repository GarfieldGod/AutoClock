from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QLineEdit, QCheckBox, QWidget, QHBoxLayout, QPushButton, QFileDialog, QComboBox, QSizePolicy

from src.utils.const import Key
from src.utils.utils import Utils
from src.utils.qt_ui import QtUI
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
    def __init__(self, key, items: list[str], default: str = "", data_values: list[str] | None = None, parent=None):
        super(ComboBox, self).__init__(parent)
        self.key = key
        self.default = default
        self._set_func = None
        self._data_values = data_values if data_values is not None else list(items)

        for it in items:
            self.addItem(str(it))

        self.currentTextChanged.connect(self._on_changed)

    def _on_changed(self, _text: str):
        if self._set_func is not None:
            idx = self.currentIndex()
            if 0 <= idx < len(self._data_values):
                self._set_func(self.key, self._data_values[idx])
            else:
                self._set_func(self.key, self.currentText())

    def value_changed_func(self, set_func):
        self._set_func = set_func

    def set_value(self, value):
        text = str(value) if value is not None else ""
        try:
            idx = self._data_values.index(text)
            self.setCurrentIndex(idx)
            return
        except ValueError:
            pass
        idx = self.findText(text)
        if idx >= 0:
            self.setCurrentIndex(idx)
            return
        try:
            idx = self._data_values.index(str(self.default))
            self.setCurrentIndex(idx)
        except ValueError:
            idx = self.findText(str(self.default))
            if idx >= 0:
                self.setCurrentIndex(idx)

class TaskListWidget(QWidget):
    COL_TASK = 108
    COL_OPERATION = 90
    COL_TRIGGER = 64
    COL_TIME = 44
    COL_SCHEDULE = 60
    COL_RESULT = 96
    COL_STATUS = 58

    def __init__(self, task, on_status_toggle=None, parent=None):
        super(TaskListWidget, self).__init__(parent)
        self._on_status_toggle = on_status_toggle
        self._status_button = None
        self.init_ui(task)

    def _apply_status_button_style(self, enabled: bool):
        if self._status_button is None:
            return
        if enabled:
            self._status_button.setText("ON")
            self._status_button.setStyleSheet(
                "QPushButton {"
                "background-color: #16a34a; color: white; border: 1px solid #15803d;"
                "border-radius: 10px; padding: 2px 6px; font-weight: 600; }"
            )
        else:
            self._status_button.setText("OFF")
            self._status_button.setStyleSheet(
                "QPushButton {"
                "background-color: #6b7280; color: white; border: 1px solid #4b5563;"
                "border-radius: 10px; padding: 2px 6px; font-weight: 600; }"
            )

    def _on_status_clicked(self, checked: bool):
        applied = checked
        if callable(self._on_status_toggle):
            ok = bool(self._on_status_toggle(self.objectName(), checked))
            if not ok:
                applied = not checked
                self._status_button.blockSignals(True)
                self._status_button.setChecked(applied)
                self._status_button.blockSignals(False)
        self._apply_status_button_style(applied)

    @staticmethod
    def _elide_text(text: str, width: int, size: int = 9, family: str = "Arial") -> str:
        font = QFont(family)
        font.setPointSize(size)
        metrics = QFontMetrics(font)
        return metrics.elidedText(str(text or ""), Qt.ElideRight, max(width - 10, 8))

    def init_ui(self, task):
        self.setObjectName(task[Key.TaskID])
        layout_plan_line = QHBoxLayout(self)
        layout_plan_line.setContentsMargins(6, 0, 6, 0)
        layout_plan_line.setSpacing(6)
        layout_plan_line.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        front_size = 9
        label_alignment = Qt.AlignLeft

        schedule_text = ""
        if task[Key.TriggerType] in [Key.Once, Key.Weekly, Key.Monthly]:
            schedule_text = str(task.get(Key.ExecuteDay, "") or "")
        elif task[Key.TriggerType] == Key.SmartHoliday:
            schedule_text = "Smart"
        elif task[Key.TriggerType] == Key.Multiple:
            schedule_text = "[Multiple]"
        else:
            schedule_text = "Daily"

        last_result = str(task.get(Key.LastRunResult, "-") or "-")
        status_on = bool(task.get(Key.Enabled, True))

        label_p = QtUI.create_label(
            self._elide_text(task[Key.TaskName], self.COL_TASK, size=front_size),
            size=front_size,
            fixed_width=self.COL_TASK,
            alignment=label_alignment,
            width_policy=QSizePolicy.Fixed,
            height_policy=QSizePolicy.Fixed,
        )
        label_p.setToolTip(str(task.get(Key.TaskName, "") or ""))
        layout_plan_line.addWidget(label_p)
        label_o = QtUI.create_label(
            self._elide_text(task[Key.Operation], self.COL_OPERATION, size=front_size),
            size=front_size,
            alignment=label_alignment,
            fixed_width=self.COL_OPERATION,
            width_policy=QSizePolicy.Fixed,
            height_policy=QSizePolicy.Fixed,
        )
        label_o.setToolTip(str(task.get(Key.Operation, "") or ""))
        layout_plan_line.addWidget(label_o)
        label_t = QtUI.create_label(
            self._elide_text(task[Key.TriggerType], self.COL_TRIGGER, size=front_size),
            size=front_size,
            alignment=label_alignment,
            fixed_width=self.COL_TRIGGER,
            width_policy=QSizePolicy.Fixed,
            height_policy=QSizePolicy.Fixed,
        )
        layout_plan_line.addWidget(label_t)
        label_et = QtUI.create_label(task[Key.ExecuteTime], size=front_size, alignment=Qt.AlignCenter, fixed_width=self.COL_TIME, width_policy=QSizePolicy.Fixed, height_policy=QSizePolicy.Fixed)
        layout_plan_line.addWidget(label_et)
        label_s = QtUI.create_label(
            self._elide_text(schedule_text, self.COL_SCHEDULE, size=front_size),
            size=front_size,
            alignment=Qt.AlignCenter,
            fixed_width=self.COL_SCHEDULE,
            width_policy=QSizePolicy.Fixed,
            height_policy=QSizePolicy.Fixed,
        )
        layout_plan_line.addWidget(label_s)
        label_r = QtUI.create_label(
            self._elide_text(last_result, self.COL_RESULT, size=front_size),
            size=front_size,
            alignment=label_alignment,
            fixed_width=self.COL_RESULT,
            width_policy=QSizePolicy.Fixed,
            height_policy=QSizePolicy.Fixed,
        )
        label_r.setToolTip(last_result)
        layout_plan_line.addWidget(label_r)
        self._status_button = QPushButton()
        self._status_button.setCheckable(True)
        self._status_button.setChecked(status_on)
        self._status_button.setFixedWidth(self.COL_STATUS)
        self._status_button.clicked.connect(self._on_status_clicked)
        self._apply_status_button_style(status_on)
        layout_plan_line.addWidget(self._status_button)
