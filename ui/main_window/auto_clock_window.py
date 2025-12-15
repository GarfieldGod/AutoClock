import os

from PyQt5.QtCore import QSize, QTimer

from src.utils.const import AppPath
from src.utils.utils import Utils
from ui.template.ui_main_window import MainWindow
from ui.template.ui_page import Container, PageContent


class AutoClockWindow(MainWindow):
    save_data = None

    def __init__(self):
        super().__init__(
            title_text="Auto Clock",
            title_desc="--automatically execute the tasks",
            show_max_button=False,
            window_size=QSize(800, 600),
            icon_path=os.path.join(os.path.join(os.path.join(AppPath.UiResourcePath, "image")), "app_icon.png"),
            icon_size=QSize(90, 120)
        )

        self.load_data_json()

        self.write_timer = QTimer(self)
        self.write_timer.setInterval(1000)
        self.write_timer.timeout.connect(self.write_data_json)

    def load_data_json(self):
        try:
            if not os.path.exists(AppPath.DataJson):
                return False

            self.save_data = Utils.read_dict_from_json(AppPath.DataJson)
        except Exception as e:
            print(e)

    def write_data_json(self):
        print("write_data_json")
        Utils.write_dict_to_file(AppPath.DataJson, self.save_data)
        self.write_timer.stop()

    def get_save_data(self, key, default=None):
        return self.save_data.get(key, default)

    def on_window_close(self):
        self.write_data_json()
        self.close()

    def set_save_data(self, key, value):
        try:
            self.save_data[key] = value

            self.write_timer.stop()
            self.write_timer.start()
        except Exception as e:
            print(e)

    def add_page(self, navigation, page):
        super().add_page(navigation, page)

        if self.save_data is not None and isinstance(page, AutoClockPageContent):
            page.set_save_data(self.set_save_data, self.get_save_data)

class AutoClockPageContent(PageContent):
    set_data_func = None
    get_data_func = None
    input_save_widget = []

    def __init__(self, y, x):
        super().__init__(y, x)

    def set_save_data(self, set_func, get_func):
        self.set_data_func = set_func
        self.get_data_func = get_func

        for widget in self.input_save_widget:
            widget.set_value(self.get_data_func(widget.key, widget.default))
            widget.value_changed_func(self.set_data_func)

class AutoClockContainer(Container):
    def __init__(self, x, y):
        super().__init__(x, y)
