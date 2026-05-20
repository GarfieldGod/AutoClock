import os.path
import sys

from PyQt5.QtCore import QSize, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from src.utils.const import AppPath
from ui.main_window.auto_clock_window import AutoClockWindow
from ui.pages.ui_page_notification import NotificationPage
from ui.pages.ui_page_clock import ClockPage
from ui.pages.ui_page_task import SystemTaskPage
from ui.pages.ui_page_settings import ToolSettingsPage
from ui.pages.ui_page_daily_report import DailyReportPage

from ui.template.ui_page import PageNavigation

def init_page_list(w):
    icon_size = QSize(50, 50)
    image_path = os.path.join(os.path.join(AppPath.UiResourcePath, "image"))
    nav_task = PageNavigation(
        name="Task",
        ico=os.path.join(image_path, "task_icon.png"),
        image_size=icon_size
    )
    con_task = SystemTaskPage(6,6)
    w.add_page(nav_task, con_task)

    nav_clock = PageNavigation(
        name="Clock",
        ico=os.path.join(image_path, "clock_icon.png"),
        image_size=icon_size
    )
    con_clock = ClockPage(6,6)
    w.add_page(nav_clock, con_clock)

    nav_daily = PageNavigation(
        name="Daily",
        ico=os.path.join(image_path, "daily_icon.png"),
        image_size=icon_size
    )
    con_daily = DailyReportPage(1, 1)
    w.add_page(nav_daily, con_daily)

    nav_notification = PageNavigation(
        name="Notice",
        ico=os.path.join(image_path, "notice_icon.png"),
        image_size=icon_size
    )
    con_notification = NotificationPage(6, 6)
    w.add_page(nav_notification, con_notification)

    nav_settings = PageNavigation(
        name="Settings",
        ico=os.path.join(image_path, "settings_icon.png"),
        image_size=icon_size
    )
    con_settings = ToolSettingsPage(6, 6)
    w.add_page(nav_settings, con_settings)

def init_ui(startup_hook=None):
    app = QApplication(sys.argv)
    try:
        icon_path = os.path.join(AppPath.UiResourcePath, "image", "app_icon.png")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass
    window = AutoClockWindow()
    init_page_list(window)
    window.show()

    if callable(startup_hook):
        def _run_hook():
            try:
                startup_hook(window, app)
            except Exception:
                pass

        QTimer.singleShot(0, _run_hook)

    sys.exit(app.exec_())

if __name__ == "__main__":
    init_ui()