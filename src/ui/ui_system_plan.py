import copy
import platform
from datetime import datetime, timedelta

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QDate, QLocale
from PyQt5.QtWidgets import QDialogButtonBox, QVBoxLayout, QComboBox, QWidget, QHBoxLayout, QLineEdit, QDialog, QLabel

from src.utils.log import Log
from src.utils.const import Key
from src.ui.ui_calendar import Calendar, WeeklyCalendar
from src.utils.utils import Utils, QtUI
from src.ui.ui_message import MessageBox


class SystemPlanDialog(QDialog):
    trigger_types = [Key.Once, Key.Multiple, Key.Daily, Key.Weekly, Key.Monthly, Key.SmartHoliday]
    day_time_types = [Key.Specify, Key.Random]
    operation_types = [Key.AutoClock, Key.ShutDownSystem, Key.SystemSleep, Key.DisconnectNetwork, Key.ConnectNetwork]

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setMinimumWidth(500)
            self.setWindowTitle("Create Windows Plan")
            self.setWindowIcon(QIcon(Utils.get_ico_path()))
            self.locale = QLocale(QLocale.English)
            # 任务名
            self.plan_name_edit = QLineEdit()
            self.plan_name_edit.setText(Key.DefaultSystemPlanName)
            # 触发类型
            self.trigger_type = QComboBox()
            self.trigger_type.addItems(self.trigger_types)
            self.trigger_type.currentTextChanged.connect(self.trigger_type_changed)
            # 操作
            self.operation = QComboBox()
            self.operation.addItems(self.operation_types)
            # dayTime类型
            self.day_time_type = QComboBox()
            self.day_time_type.addItems(self.day_time_types)
            self.day_time_type.currentTextChanged.connect(self.day_time_type_changed)

            widget_layout = QVBoxLayout(self)

            # 常规设置
            widget_setting = QWidget()
            layout_setting = QVBoxLayout(widget_setting)
            widget_line_1 = QHBoxLayout()
            # 选择Plan Name
            widget_line_1.addWidget(QtUI.create_label("Plan Name:"))
            widget_line_1.addWidget(self.plan_name_edit)
            widget_line_2 = QHBoxLayout()
            # 选择Trigger Type
            widget_line_2.addWidget(QtUI.create_label("Trigger Type:"))
            widget_line_2.addWidget(self.trigger_type)
            # 选择Operation
            widget_line_3 = QHBoxLayout()
            widget_line_3.addWidget(QtUI.create_label("Operation:"))
            widget_line_3.addWidget(self.operation)
            # 选择DayTime Type
            widget_line_4 = QHBoxLayout()
            widget_line_4.addWidget(QtUI.create_label("DayTime Type:"))
            widget_line_4.addWidget(self.day_time_type)

            layout_setting.addLayout(widget_line_1)
            layout_setting.addLayout(widget_line_2)
            layout_setting.addLayout(widget_line_3)
            layout_setting.addLayout(widget_line_4)
            widget_layout.addWidget(widget_setting)

            if platform.system() == "Linux":
                info_widget = QWidget()
                info_layout = QHBoxLayout(info_widget)
                info_label = QLabel("注意: Linux计划任务将使用crontab实现，可能需要sudo权限")
                info_label.setStyleSheet("color: orange; font-size: 12px;")
                info_layout.addWidget(info_label)
                widget_layout.addWidget(info_widget)

            # 特定DayTime
            self.widget_specify_day_time_selector = QWidget()
            self.layout_specify_day_time_selector = QHBoxLayout(self.widget_specify_day_time_selector)
            self.hour_sel = QComboBox()
            self.hour_sel.addItems(Utils.get_nums_array(0,23))
            self.hour_sel.setCurrentIndex(datetime.now().hour)
            self.minute_sel = QComboBox()
            self.minute_sel.addItems(Utils.get_nums_array(0,59))
            self.minute_sel.setCurrentIndex(datetime.now().minute)
            self.layout_specify_day_time_selector.addWidget(QtUI.create_label("DayTime:"))
            self.layout_specify_day_time_selector.addStretch()
            self.layout_specify_day_time_selector.addWidget(QtUI.create_label("Hours:", size=10, length=50))
            self.layout_specify_day_time_selector.addWidget(self.hour_sel)
            self.layout_specify_day_time_selector.addWidget(QtUI.create_label("Minute:", size=10, length=50))
            self.layout_specify_day_time_selector.addWidget(self.minute_sel)
            # 随机DayTime
            self.widget_random_day_time_selector = QWidget()
            self.layout_random_day_time_selector = QHBoxLayout(self.widget_random_day_time_selector)
            self.hour_sel_start = QComboBox()
            self.hour_sel_start.addItems(Utils.get_nums_array(0,23))
            self.hour_sel_start.setCurrentIndex(datetime.now().hour)
            self.minute_sel_start = QComboBox()
            self.minute_sel_start.addItems(Utils.get_nums_array(0,59))
            self.minute_sel_start.setCurrentIndex(datetime.now().minute)
            self.hour_sel_end = QComboBox()
            self.hour_sel_end.addItems(Utils.get_nums_array(0,23))
            self.hour_sel_end.setCurrentIndex(datetime.now().hour)
            self.minute_sel_end = QComboBox()
            self.minute_sel_end.addItems(Utils.get_nums_array(0,59))
            self.minute_sel_end.setCurrentIndex(datetime.now().minute)
            self.layout_random_day_time_selector.addWidget(QtUI.create_label("DayTime Scope:"))
            self.layout_random_day_time_selector.addStretch()
            self.layout_random_day_time_selector.addWidget(self.hour_sel_start)
            self.layout_random_day_time_selector.addWidget(self.minute_sel_start)
            self.layout_random_day_time_selector.addWidget(QLabel("-"))
            self.layout_random_day_time_selector.addWidget(self.hour_sel_end)
            self.layout_random_day_time_selector.addWidget(self.minute_sel_end)

            # 批量选择
            self.calendar_selector = Calendar()

            # 指定日
            self.widget_one_day_selector = QWidget()
            self.layout_one_day_selector = QHBoxLayout(self.widget_one_day_selector)
            self.year_sel = QComboBox()
            self.year_sel.addItems([str(QDate.currentDate().year()), str(QDate.currentDate().addYears(1).year())])
            self.year_sel.currentIndexChanged.connect(self.year_changed)
            self.month_sel = QComboBox()
            self.month_sel.addItems(Utils.get_nums_array(1,12))
            self.month_sel.setCurrentIndex(datetime.now().month - 1)
            self.month_sel.currentIndexChanged.connect(self.month_changed)
            self.day_sel = QComboBox()
            self.day_sel.addItems(Utils.get_nums_array(1, 31))
            self.day_sel.setCurrentIndex(datetime.now().day - 1)
            self.layout_one_day_selector.addWidget(QtUI.create_label("Year:", size=10, length=50))
            self.layout_one_day_selector.addWidget(self.year_sel)
            self.layout_one_day_selector.addWidget(QtUI.create_label("Month:", size=10, length=50))
            self.layout_one_day_selector.addWidget(self.month_sel)
            self.layout_one_day_selector.addWidget(QtUI.create_label("Day:", size=10, length=50))
            self.layout_one_day_selector.addWidget(self.day_sel)
            # 每日
            self.widget_daily_selector = QWidget()
            # 指定每周
            self.widget_weekly_selector = QWidget()
            self.layout_weekly_selector = QHBoxLayout(self.widget_weekly_selector)
            self.layout_weekly_selector.addWidget(QtUI.create_label("The Day:"))
            self.weekly_day_sel = WeeklyCalendar()
            self.layout_weekly_selector.addWidget(self.weekly_day_sel)
            # 指定每月
            self.widget_monthly_selector = QWidget()
            self.layout_monthly_selector = QHBoxLayout(self.widget_monthly_selector)
            self.monthly_day_sel = QComboBox()
            self.monthly_day_sel.addItems(Utils.get_nums_array(1,31))
            self.layout_monthly_selector.addWidget(QtUI.create_label("The Day:"))
            self.layout_monthly_selector.addWidget(self.monthly_day_sel)
            self.monthly_day_sel.setCurrentIndex(datetime.now().day - 1)

            # 预留变化区
            self.day_time_space_area = QVBoxLayout()
            self.day_time_space_area.addWidget(self.widget_specify_day_time_selector)
            self.day_time_space_area.addWidget(self.widget_random_day_time_selector)
            widget_layout.addLayout(self.day_time_space_area)
            self.space_area_hide_all_content(self.day_time_space_area)
            self.widget_specify_day_time_selector.show()

            self.space_area = QVBoxLayout()
            self.space_area.addWidget(self.widget_one_day_selector)
            self.space_area.addWidget(self.calendar_selector)
            self.space_area.addWidget(self.widget_daily_selector)
            self.space_area.addWidget(self.widget_weekly_selector)
            self.space_area.addWidget(self.widget_monthly_selector)
            widget_layout.addLayout(self.space_area)
            self.space_area_hide_all_content(self.space_area)
            self.widget_one_day_selector.show()

            # 按键
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            widget_layout.addWidget(buttons)
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
            # SmartHoliday does not allow manual date selection
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