import sys

from PyQt5.QtCore import QDate, Qt, QLocale
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QPushButton,
                             QLabel, QHBoxLayout, QToolButton, QVBoxLayout, QSizePolicy)


class Calendar(QWidget):
    selected_dates = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.locale = QLocale(QLocale.English)
        self.init_ui()
        self.current_date = QDate.currentDate()
        self.refresh_calendar()

    def init_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(320)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        widget_nav = QWidget(self)
        widget_nav.setStyleSheet("background-color: rgb(255, 255, 255);border: 1px solid #8b8b8b;border-radius: 4px;")
        self.nav_layout = QHBoxLayout(widget_nav)
        self.prev_btn = QToolButton()
        self.prev_btn.setText("<")
        self.prev_btn.setStyleSheet("font-size: 16px; width: 30px; height: 30px;")
        self.prev_btn.clicked.connect(self.prev_month)
        self.nav_layout.addWidget(self.prev_btn)

        self.date_label = QLabel()
        self.date_label.setStyleSheet("font-size: 18px; font-weight: bold; text-align: center;font-family: Arial, \"Helvetica Neue\", sans-serif;")
        self.nav_layout.addWidget(self.date_label, stretch=1)
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.next_btn = QToolButton()
        self.next_btn.setText(">")
        self.next_btn.setStyleSheet("font-size: 16px; width: 30px; height: 30px;")
        self.next_btn.clicked.connect(self.next_month)
        self.nav_layout.addWidget(self.next_btn)

        # 网格布局
        widget_grid = QWidget()
        widget_grid.setStyleSheet("background-color: rgb(255, 255, 255);border: 1px solid #8b8b8b;border-radius: 4px;")
        self.grid_layout = QGridLayout(widget_grid)
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

        # 星期表头
        self.weekdays = [ "7", "1", "2", "3", "4", "5", "6"]
        for col, day in enumerate(self.weekdays):
            week_en = self.locale.dayName(int(day), QLocale.ShortFormat)
            label = QLabel(week_en)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(f"""
                QLabel {{
                    font-family: Arial, "Helvetica Neue", sans-serif;
                    font-size: 14px;
                    font-weight: bold;
                    color: {"#ff0000" if day == "7" or day == "6" else "#333"};
                    background-color: {"#d0d0d0" if day == "7" or day == "6" else "#f0f0f0"};
                    padding: 8px 0;
                    border-radius: 4px;
                }}
            """)
            self.grid_layout.addWidget(label, 0, col)

        self.date_buttons = []
        for row in range(1, 7):
            row_buttons = []
            for col in range(7):
                btn = QPushButton()
                btn.setCheckable(True)
                btn.setFlat(False)
                btn.setStyleSheet(get_btn_style())
                btn.clicked.connect(lambda checked, b=btn: self.on_date_click(b))
                self.grid_layout.addWidget(btn, row, col)
                row_buttons.append(btn)
            self.date_buttons.append(row_buttons)

        self.main_layout.addWidget(widget_nav)
        self.main_layout.addWidget(widget_grid)

    def refresh_calendar(self):
        year = self.current_date.year()
        month = self.current_date.month()
        month_full = self.locale.toString(QDate(2025, month, 1), "MMMM")
        self.date_label.setText(f"{month_full} {year}")

        first_day = QDate(year, month, 1)
        last_day = QDate(year, month, first_day.daysInMonth())
        week_to_col = {week_str: idx for idx, week_str in enumerate(self.weekdays)}
        first_day_week_str = str(first_day.dayOfWeek())
        if first_day_week_str in week_to_col:
            first_weekday = week_to_col[first_day_week_str]
        else:
            first_weekday = first_day.dayOfWeek() - 1

        for row in self.date_buttons:
            for btn in row:
                btn.setText("")
                btn.setEnabled(False)
                btn.setChecked(False)
                btn.setObjectName("")
                btn.setProperty("date", None)

        current_day = 1
        next_month_day = 1
        for row in range(6):
            for col in range(7):
                btn = self.date_buttons[row][col]
                date = QDate(year, month, current_day)
                day_str = str(current_day)
                if row == 0 and col < first_weekday:
                    last_month = self.current_date.addMonths(-1)
                    date = QDate(year - 1 if self.current_date.month() == 1 else year, last_month.month(), last_month.daysInMonth() - first_weekday + col + 1)
                    day_str = str(last_month.daysInMonth() - first_weekday + col + 1)
                    btn.setObjectName("not_this_month")
                elif current_day > last_day.day():
                    next_month = self.current_date.addMonths(1)
                    date = QDate(year + 1 if self.current_date.month() == 12 else year, next_month.month(), next_month_day)
                    day_str = str(next_month_day)
                    btn.setObjectName("not_this_month")
                    next_month_day += 1
                else:
                    if col == week_to_col["6"] or col == week_to_col["7"]:
                        btn.setObjectName("weekend")
                    if date == QDate.currentDate():
                        btn.setObjectName("today")
                    current_day += 1

                btn.setText(day_str)
                btn_date = date
                btn.setProperty("date", btn_date)
                btn.setChecked(btn_date in self.selected_dates)

                btn.setStyleSheet(get_btn_style())

                if btn_date >= QDate.currentDate():
                    btn.setEnabled(True)
                else:
                    btn.setEnabled(False)

    def on_date_click(self, btn):
        selected_date = btn.property("date")
        if not selected_date or not btn.isEnabled():
            return

        if btn.isChecked():
            if selected_date not in self.selected_dates:
                self.selected_dates.append(selected_date.toString('yyyy-MM-dd'))
        else:
            if selected_date in self.selected_dates:
                self.selected_dates.remove(selected_date.toString('yyyy-MM-dd'))
        print(f"点击日期：{selected_date.toString('yyyy-MM-dd')} 所有已选: {self.selected_dates}")

    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.refresh_calendar()

    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.refresh_calendar()

class WeeklyCalendar(QWidget):
    selected_dates = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.locale = QLocale(QLocale.English)

        self.setMinimumHeight(70)
        self.setMinimumWidth(350)
        self.btnSize = 40

        self.init_ui()

    def init_ui(self):
        widget = QWidget(self)
        widget.setStyleSheet("background-color: rgb(255, 255, 255);border-radius: 5px;")
        layout = QHBoxLayout(widget)
        current_day_of_week = self.locale.dayName(QDate.currentDate().dayOfWeek(), QLocale.ShortFormat)

        for i in range(1, 8):
            day_name = self.locale.dayName(i, QLocale.ShortFormat)
            btn = QPushButton(day_name)
            if day_name in ["Sat", "Sun"]:
                btn.setObjectName("weekend")
            if day_name == current_day_of_week:
                btn.setObjectName("today")
            btn.setFixedSize(self.btnSize, self.btnSize)
            btn.setCheckable(True)
            btn.setFlat(False)
            btn.setStyleSheet(get_btn_style())
            btn.clicked.connect(lambda checked, b=day_name: self.on_day_clicked(b))
            layout.addWidget(btn)

    def on_day_clicked(self, date):
        if date in self.selected_dates:
            self.selected_dates.remove(date)
        else:
            self.selected_dates.append(date)

def get_btn_style():
    return """
        QPushButton:!checked:enabled {
            font-weight: bold;
            font-family: Arial, "Helvetica Neue", sans-serif;
            text-align: center;
            font-size: 14px;
            color: #333;
            background-color: white;
            border: 0.5px solid #eee;
            border-radius: 4px;
            padding: 10px 0;
        }
        QPushButton:!checked:enabled:hover {
            background-color: #f8f8f8;
            border-color: #ddd;
        }
        QPushButton:checked:enabled {
            text-align: center;
            font-size: 14px;
            color: white;
            background-color: #4ecdc4;
            border: 1px solid #3dbbb4;
            border-radius: 4px;
            padding: 10px 0;
            font-weight: bold;
        }
        QPushButton:checked:enabled:hover {
            background-color: #3dbbb4;
        }
        QPushButton:disabled {
            color: #ccc;
            background-color: #fafafa;
            border-color: #eee;
            border-radius: 4px;
            padding: 10px 0;
        }
        QPushButton#today:!checked:enabled {
            color: white;
            background-color: #ff8b8b;
            border: 1px solid #ff4949;
        }
        QPushButton#today:checked:enabled {
            color: white;
            background-color: #ff0000;
            border: 1px solid #ff3333;
        }
        QPushButton#weekend:!checked:enabled {
            color: #ff0000;
            background-color: white;
            border: 1px solid #eee;
        }
        QPushButton#weekend:checked:enabled {
            color: white;
            background-color: #4ecdc4;
            border: 1px solid #3dbbb4;
        }
        QPushButton#not_this_month:!checked:enabled {
            color: #ccc;
            background-color: #fafafa;
            border-color: #eee;
            border-radius: 4px;
            padding: 10px 0;
        }
    """
