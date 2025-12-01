import sys

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication

from ui.pages.auto_clock_window import AutoClockWindow
from ui.pages.ui_page_notification import NotificationPage
from ui.pages.ui_page_clock import ClockPage
from ui.pages.ui_page_task import SystemTaskPage
from ui.template.ui_main_window import MainWindow
from ui.template.ui_page import PageNavigation

def init_page_list(w):
    nav_task = PageNavigation(name="Task")
    con_task = SystemTaskPage(6,6)
    w.add_page(nav_task, con_task)

    nav_clock = PageNavigation(name="Clock")
    con_clock = ClockPage(6,6)
    w.add_page(nav_clock, con_clock)

    nav_notification = PageNavigation(name="Notice")
    con_notification = NotificationPage(6, 6)
    w.add_page(nav_notification, con_notification)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoClockWindow()
    init_page_list(window)
    window.show()
    sys.exit(app.exec_())