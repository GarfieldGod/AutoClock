import copy
import platform
from datetime import datetime, timedelta

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QDate, QLocale, Qt
from PyQt5.QtWidgets import QVBoxLayout, QComboBox, QWidget, QHBoxLayout, QLineEdit, QDialog, QLabel, QPushButton

from src.utils.log import Log
from src.utils.const import Key
from src.ui.ui_calendar import Calendar, WeeklyCalendar
from src.utils.utils import Utils
from src.utils.qt_ui import QtUI
from src.ui.ui_message import MessageBox


_DIALOG_STYLE = """
    QDialog {
        background-color: #ffffff;
    }
"""

_BTN_PRIMARY = """
    QPushButton {
        background-color: #2563eb; color: white;
        border: none; border-radius: 6px;
        padding: 8px 24px; font-weight: 600; font-size: 13px;
        min-width: 80px;
    }
    QPushButton:hover { background-color: #1d4ed8; }
    QPushButton:pressed { background-color: #1e40af; }
"""

_BTN_SECONDARY = """
    QPushButton {
        background-color: #ffffff; color: #374151;
        border: 1px solid #d1d5db; border-radius: 6px;
        padding: 8px 24px; font-weight: 600; font-size: 13px;
        min-width: 80px;
    }
    QPushButton:hover { background-color: #f3f4f6; border-color: #9ca3af; }
    QPushButton:pressed { background-color: #e5e7eb; }
"""


class SystemPlanDialog(QDialog):
    trigger_types = [Key.Once, Key.Multiple, Key.Daily, Key.Weekly, Key.Monthly, Key.SmartHoliday]
    day_time_types = [Key.Specify, Key.Random]
    operation_types = [Key.AutoClock, Key.ShutDownSystem, Key.SystemSleep, Key.DisconnectNetwork, Key.ConnectNetwork]

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setMinimumWidth(520)
            self.setWindowTitle("Create Windows Plan")
            self.setWindowIcon(QIcon(Utils.get_ico_path()))
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            self.setStyleSheet(_DIALOG_STYLE)
            self.locale = QLocale(QLocale.English)

            self.plan_name_edit = QLineEdit()
            self.plan_name_edit.setText(Key.DefaultSystemPlanName)
            self.plan_name_edit.setStyleSheet(
                "QLineEdit { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px; font-size: 13px; }"
                "QLineEdit:focus { border-color: #2563eb; }"
            )

            self.trigger_type = QComboBox()
            self.trigger_type.addItems(self.trigger_types)
            self.trigger_type.currentTextChanged.connect(self.trigger_type_changed)

            self.operation = QComboBox()
            self.operation.addItems(self.operation_types)

            self.day_time_type = QComboBox()
            self.day_time_type.addItems(self.day_time_types)
            self.day_time_type.currentTextChanged.connect(self.day_time_type_changed)

            _combo_style = (
                "QComboBox { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px; font-size: 13px; }"
                "QComboBox:focus { border-color: #2563eb; }"
                "QComboBox::drop-down { border: none; width: 24px; }"
            )
            for cb in [self.trigger_type, self.operation, self.day_time_type]:
                cb.setStyleSheet(_combo_style)

            widget_layout = QVBoxLayout(self)
            widget_layout.setContentsMargins(20, 16, 20, 16)
            widget_layout.setSpacing(10)

            widget_setting = QWidget()
            layout_setting = QVBoxLayout(widget_setting)
            layout_setting.setSpacing(8)
            layout_setting.setContentsMargins(0, 0, 0, 0)

            def _make_row(label_text, widget):
                row = QHBoxLayout()
                row.setSpacing(10)
                lbl = QtUI.create_label(label_text)
                lbl.setStyleSheet("color:#374151; font-weight:600; font-size:13px;")
                lbl.setFixedWidth(120)
                row.addWidget(lbl)
                row.addWidget(widget, 1)
                layout_setting.addLayout(row)

            _make_row("Plan Name:", self.plan_name_edit)
            _make_row("Trigger Type:", self.trigger_type)
            _make_row("Operation:", self.operation)
            _make_row("DayTime Type:", self.day_time_type)

            widget_layout.addWidget(widget_setting)

            if platform.system() == "Linux":
                info_label = QLabel("注意: Linux计划任务将使用crontab实现，可能需要sudo权限")
                info_label.setStyleSheet("color: #d97706; font-size: 12px; padding: 4px 0;")
                widget_layout.addWidget(info_label)

            self.widget_specify_day_time_selector = QWidget()
            self.layout_specify_day_time_selector = QHBoxLayout(self.widget_specify_day_time_selector)
            self.layout_specify_day_time_selector.setContentsMargins(0, 0, 0, 0)
            self.hour_sel = QComboBox()
            self.hour_sel.addItems(Utils.get_nums_array(0,23))
            self.hour_sel.setCurrentIndex(datetime.now().hour)
            self.hour_sel.setStyleSheet(_combo_style)
            self.minute_sel = QComboBox()
            self.minute_sel.addItems(Utils.get_nums_array(0,59))
            self.minute_sel.setCurrentIndex(datetime.now().minute)
            self.minute_sel.setStyleSheet(_combo_style)
            self.layout_specify_day_time_selector.addWidget(QtUI.create_label("DayTime:"))
            self.layout_specify_day_time_selector.addStretch()
            self.layout_specify_day_time_selector.addWidget(QtUI.create_label("Hours:", size=10, length=50))
            self.layout_specify_day_time_selector.addWidget(self.hour_sel)
            self.layout_specify_day_time_selector.addWidget(QtUI.create_label("Minute:", size=10, length=50))
            self.layout_specify_day_time_selector.addWidget(self.minute_sel)

            self.widget_random_day_time_selector = QWidget()
            self.layout_random_day_time_selector = QHBoxLayout(self.widget_random_day_time_selector)
            self.layout_random_day_time_selector.setContentsMargins(0, 0, 0, 0)
            self.hour_sel_start = QComboBox()
            self.hour_sel_start.addItems(Utils.get_nums_array(0,23))
            self.hour_sel_start.setCurrentIndex(datetime.now().hour)
            self.hour_sel_start.setStyleSheet(_combo_style)
            self.minute_sel_start = QComboBox()
            self.minute_sel_start.addItems(Utils.get_nums_array(0,59))
            self.minute_sel_start.setCurrentIndex(datetime.now().minute)
            self.minute_sel_start.setStyleSheet(_combo_style)
            self.hour_sel_end = QComboBox()
            self.hour_sel_end.addItems(Utils.get_nums_array(0,23))
            self.hour_sel_end.setCurrentIndex(datetime.now().hour)
            self.hour_sel_end.setStyleSheet(_combo_style)
            self.minute_sel_end = QComboBox()
            self.minute_sel_end.addItems(Utils.get_nums_array(0,59))
            self.minute_sel_end.setCurrentIndex(datetime.now().minute)
            self.minute_sel_end.setStyleSheet(_combo_style)
            dash_label = QLabel("-")
            dash_label.setStyleSheet("color:#6b7280; font-weight:bold;")
            self.layout_random_day_time_selector.addWidget(QtUI.create_label("DayTime Scope:"))
            self.layout_random_day_time_selector.addStretch()
            self.layout_random_day_time_selector.addWidget(self.hour_sel_start)
            self.layout_random_day_time_selector.addWidget(self.minute_sel_start)
            self.layout_random_day_time_selector.addWidget(dash_label)
            self.layout_random_day_time_selector.addWidget(self.hour_sel_end)
            self.layout_random_day_time_selector.addWidget(self.minute_sel_end)

            self.calendar_selector = Calendar()

            self.widget_one_day_selector = QWidget()
            self.layout_one_day_selector = QHBoxLayout(self.widget_one_day_selector)
            self.layout_one_day_selector.setContentsMargins(0, 0, 0, 0)
            self.year_sel = QComboBox()
            self.year_sel.addItems([str(QDate.currentDate().year()), str(QDate.currentDate().addYears(1).year())])
            self.year_sel.currentIndexChanged.connect(self.year_changed)
            self.year_sel.setStyleSheet(_combo_style)
            self.month_sel = QComboBox()
            self.month_sel.addItems(Utils.get_nums_array(1,12))
            self.month_sel.setCurrentIndex(datetime.now().month - 1)
            self.month_sel.currentIndexChanged.connect(self.month_changed)
            self.month_sel.setStyleSheet(_combo_style)
            self.day_sel = QComboBox()
            self.day_sel.addItems(Utils.get_nums_array(1, 31))
            self.day_sel.setCurrentIndex(datetime.now().day - 1)
            self.day_sel.setStyleSheet(_combo_style)
            self.layout_one_day_selector.addWidget(QtUI.create_label("Year:", size=10, length=50))
            self.layout_one_day_selector.addWidget(self.year_sel)
            self.layout_one_day_selector.addWidget(QtUI.create_label("Month:", size=10, length=50))
            self.layout_one_day_selector.addWidget(self.month_sel)
            self.layout_one_day_selector.addWidget(QtUI.create_label("Day:", size=10, length=50))
            self.layout_one_day_selector.addWidget(self.day_sel)

            self.widget_daily_selector = QWidget()

            self.widget_weekly_selector = QWidget()
            self.layout_weekly_selector = QHBoxLayout(self.widget_weekly_selector)
            self.layout_weekly_selector.setContentsMargins(0, 0, 0, 0)
            self.layout_weekly_selector.addWidget(QtUI.create_label("The Day:"))
            self.weekly_day_sel = WeeklyCalendar()
            self.layout_weekly_selector.addWidget(self.weekly_day_sel)

            self.widget_monthly_selector = QWidget()
            self.layout_monthly_selector = QHBoxLayout(self.widget_monthly_selector)
            self.layout_monthly_selector.setContentsMargins(0, 0, 0, 0)
            self.monthly_day_sel = QComboBox()
            self.monthly_day_sel.addItems(Utils.get_nums_array(1,31))
            self.monthly_day_sel.setStyleSheet(_combo_style)
            self.layout_monthly_selector.addWidget(QtUI.create_label("The Day:"))
            self.layout_monthly_selector.addWidget(self.monthly_day_sel)
            self.monthly_day_sel.setCurrentIndex(datetime.now().day - 1)

            self.day_time_space_area = QVBoxLayout()
            self.day_time_space_area.setContentsMargins(0, 0, 0, 0)
            self.day_time_space_area.addWidget(self.widget_specify_day_time_selector)
            self.day_time_space_area.addWidget(self.widget_random_day_time_selector)
            widget_layout.addLayout(self.day_time_space_area)
            self.space_area_hide_all_content(self.day_time_space_area)
            self.widget_specify_day_time_selector.show()

            self.space_area = QVBoxLayout()
            self.space_area.setContentsMargins(0, 0, 0, 0)
            self.space_area.addWidget(self.widget_one_day_selector)
            self.space_area.addWidget(self.calendar_selector)
            self.space_area.addWidget(self.widget_daily_selector)
            self.space_area.addWidget(self.widget_weekly_selector)
            self.space_area.addWidget(self.widget_monthly_selector)
            widget_layout.addLayout(self.space_area)
            self.space_area_hide_all_content(self.space_area)
            self.widget_one_day_selector.show()

            btn_row = QHBoxLayout()
            btn_row.setSpacing(10)
            btn_row.addStretch()
            ok_btn = QPushButton("OK")
            ok_btn.setStyleSheet(_BTN_PRIMARY)
            ok_btn.clicked.connect(self.accept)
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setStyleSheet(_BTN_SECONDARY)
            cancel_btn.clicked.connect(self.reject)
            btn_row.addWidget(ok_btn)
            btn_row.addWidget(cancel_btn)
            widget_layout.addLayout(btn_row)
        except Exception as e:
            Log.error(e)
            MessageBox(e)

    def space_area_hide_all_content(self, area):
        for i in range(area.count()):
            item = area.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.hide()

    def trigger_type_changed(self):
        self.space_area_hide_all_content(self.space_area)
        current = self.trigger_type.currentText()
        if current == self.trigger_types[1]:
            self.calendar_selector.show()
        elif current == self.trigger_types[0]:
            self.widget_one_day_selector.show()
        elif current == self.trigger_types[3]:
            self.widget_weekly_selector.show()
        elif current == self.trigger_types[4]:
            self.widget_monthly_selector.show()
        elif current == Key.SmartHoliday:
            pass
        else:
            self.widget_daily_selector.show()

        self.layout().invalidate()
        self.layout().activate()
        self.adjustSize()

    def day_time_type_changed(self):
        self.space_area_hide_all_content(self.day_time_space_area)
        if self.day_time_type.currentText() == self.day_time_types[0]:
            self.widget_specify_day_time_selector.show()
        elif self.day_time_type.currentText() == self.day_time_types[1]:
            self.widget_random_day_time_selector.show()
        else:
            self.widget_specify_day_time_selector.show()

        self.adjustSize()

    def year_changed(self):
        self.month_sel.setCurrentIndex(0)
        self.day_sel.setCurrentIndex(0)

    def month_changed(self):
        self.day_sel.clear()
        if self.month_sel.currentText() in ["01", "03", "05", "07", "08", "10", "12"]:
            day = 31
        elif self.month_sel.currentText() == "02":
            if QDate.isLeapYear(int(self.year_sel.currentText())):
                day = 29
            else:
                day = 28
        else:
            day = 30
        self.day_sel.addItems(Utils.get_nums_array(1, day))
        self.day_sel.setCurrentIndex(0)

    def get_time_offset(self):
        start_time_str = f'{self.hour_sel_start.currentText().strip()}:{self.minute_sel_start.currentText().strip()}'
        end_time_str = f'{self.hour_sel_end.currentText().strip()}:{self.minute_sel_end.currentText().strip()}'

        start_time = datetime.strptime(start_time_str, "%H:%M")
        end_time = datetime.strptime(end_time_str, "%H:%M")

        if end_time < start_time:
            end_time += timedelta(days=1)

        time_offset = end_time - start_time
        return int(time_offset.total_seconds())

    def values(self):
        selected_multiple_dates = copy.deepcopy(self.calendar_selector.selected_dates)
        self.calendar_selector.selected_dates.clear()
        selected_weekly_dates = copy.deepcopy(self.weekly_day_sel.selected_dates)
        self.weekly_day_sel.selected_dates.clear()

        hour = self.hour_sel.currentText().strip() if self.day_time_type.currentText() == Key.Specify else self.hour_sel_start.currentText().strip()
        minute = self.minute_sel.currentText().strip() if self.day_time_type.currentText() == Key.Specify else self.minute_sel_start.currentText().strip()
        time_offset = self.get_time_offset()
        return {
            Key.PlanName: self.plan_name_edit.text().strip(),
            Key.TriggerType: self.trigger_type.currentText().strip(),
            Key.Operation: self.operation.currentText().strip(),
            Key.DayTimeType: self.day_time_type.currentText().strip(),
            Key.Year: self.year_sel.currentText().strip(),
            Key.Month: self.month_sel.currentText().strip(),
            Key.Day: self.day_sel.currentText().strip(),
            Key.Hour: hour,
            Key.Minute: minute,
            Key.TimeOffset: time_offset,
            Key.ExecuteDays: selected_multiple_dates,
            Key.Weekly: selected_weekly_dates,
            Key.Monthly: self.monthly_day_sel.currentText().strip()
        }
