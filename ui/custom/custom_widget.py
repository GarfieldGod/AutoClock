from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QLineEdit, QCheckBox, QWidget, QHBoxLayout, QPushButton, QFileDialog, QComboBox, QSizePolicy, QVBoxLayout

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


class PasswordLineEdit(QWidget):
    def __init__(self, key, default="", parent=None):
        super(PasswordLineEdit, self).__init__(parent)
        self.key = key
        self.default = default

        self._line = QLineEdit()
        self._line.setEchoMode(QLineEdit.Password)

        self._btn = QPushButton()
        self._btn.setFixedWidth(28)
        self._btn.setStyleSheet("border: none; background-color: transparent; padding:0; font-size:18px;")

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn.setText("\U0001F512")
        self._btn.setToolTip("\u663E\u793A\u5BC6\u7801")
        self._btn.clicked.connect(self._toggle_visibility)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._line, 1)
        layout.addWidget(self._btn)

        self._set_func = None
        self._line.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self):
        if self._set_func is not None:
            self._set_func(self.key, self._line.text())

    def _toggle_visibility(self):
        if self._line.echoMode() == QLineEdit.Password:
            self._line.setEchoMode(QLineEdit.Normal)
            self._btn.setText("\U0001F441")
            self._btn.setToolTip("\u9690\u85CF\u5BC6\u7801")
        else:
            self._line.setEchoMode(QLineEdit.Password)
            self._btn.setText("\U0001F512")
            self._btn.setToolTip("\u663E\u793A\u5BC6\u7801")

    def value_changed_func(self, set_func):
        self._set_func = set_func

    def set_value(self, value):
        self._line.setText(str(value) if value is not None else "")


class FileSelectLineEdit(QWidget):
    def __init__(self, key, default="", parent=None):
        super(FileSelectLineEdit, self).__init__(parent)
        self.key = key
        self.default = default

        self._line = QLineEdit()
        self._btn = QPushButton("...")
        self._btn.setFixedWidth(30)
        self._btn.setStyleSheet(
            "QPushButton { background:transparent; border:1px solid #d1d5db; "
            "border-radius:4px; padding:0; font-size:14px; font-weight:bold; color:#4b5563; }"
            "QPushButton:hover { background-color:#f3f4f6; }"
        )

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
    NORMAL_COLS = {
        "task": 104,
        "operation": 86,
        "trigger": 60,
        "time": 44,
        "schedule": 66,
        "result": 90,
        "status": 74,
    }
    COMPACT_COLS = {
        "task": 90,
        "operation": 70,
        "trigger": 48,
        "time": 38,
        "schedule": 52,
        "result": 66,
        "status": 60,
    }

    COL_TASK = 104
    COL_OPERATION = 86
    COL_TRIGGER = 60
    COL_TIME = 44
    COL_SCHEDULE = 66
    COL_RESULT = 90
    COL_STATUS = 74

    @classmethod
    def set_compact(cls, compact: bool):
        cols = cls.COMPACT_COLS if compact else cls.NORMAL_COLS
        cls.COL_TASK = cols["task"]
        cls.COL_OPERATION = cols["operation"]
        cls.COL_TRIGGER = cols["trigger"]
        cls.COL_TIME = cols["time"]
        cls.COL_SCHEDULE = cols["schedule"]
        cls.COL_RESULT = cols["result"]
        cls.COL_STATUS = cols["status"]

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
        label_t.setToolTip(str(task.get(Key.TriggerType, "") or ""))
        layout_plan_line.addWidget(label_t)
        label_et = QtUI.create_label(task[Key.ExecuteTime], size=front_size, alignment=Qt.AlignCenter, fixed_width=self.COL_TIME, width_policy=QSizePolicy.Fixed, height_policy=QSizePolicy.Fixed)
        label_et.setToolTip(str(task.get(Key.ExecuteTime, "") or ""))
        layout_plan_line.addWidget(label_et)
        label_s = QtUI.create_label(
            self._elide_text(schedule_text, self.COL_SCHEDULE, size=front_size),
            size=front_size,
            alignment=Qt.AlignCenter,
            fixed_width=self.COL_SCHEDULE,
            width_policy=QSizePolicy.Fixed,
            height_policy=QSizePolicy.Fixed,
        )
        label_s.setToolTip(schedule_text)
        layout_plan_line.addWidget(label_s)
        label_r = QtUI.create_label(
            self._elide_text(last_result, self.COL_RESULT, size=front_size),
            size=front_size,
            alignment=Qt.AlignCenter,
            fixed_width=self.COL_RESULT,
            width_policy=QSizePolicy.Fixed,
            height_policy=QSizePolicy.Fixed,
        )
        label_r.setToolTip(last_result)
        layout_plan_line.addWidget(label_r)
        self._status_button = QPushButton()
        self._status_button.setCheckable(True)
        self._status_button.setChecked(status_on)
        self._status_button.setFixedWidth(52)
        self._status_button.clicked.connect(self._on_status_clicked)
        self._apply_status_button_style(status_on)

        status_holder = QWidget()
        status_holder.setFixedWidth(self.COL_STATUS)
        status_holder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        status_layout = QHBoxLayout(status_holder)
        status_layout.setContentsMargins(18, 0, 0, 0)
        status_layout.setSpacing(0)
        status_layout.addWidget(self._status_button, 0, Qt.AlignCenter)
        layout_plan_line.addWidget(status_holder)
