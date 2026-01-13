from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel

from src.utils.const import Key
from ui.main_window.auto_clock_window import AutoClockPageContent, AutoClockContainer
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import CheckBox
import platform


class ToolSettingsPage(AutoClockPageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(ToolSettingsPage, self).__init__(y, x)

    def init_container(self):
        tool_config = ToolConfigContainer(3, 2)
        self.add_container(tool_config, 0, 0)

        self.input_save_widget = []
        if platform.system() == 'Linux':
            self.input_save_widget.append(tool_config.check_linux_credentials_on_plan_create)


class ToolConfigContainer(AutoClockContainer):
    def __init__(self, x, y):
        super(ToolConfigContainer, self).__init__(x, y)

        self.check_linux_credentials_on_plan_create = CheckBox(Key.CheckLinuxCredentialsOnPlanCreate, default=True)

        self.init_ui_layout()

    def init_ui_layout(self):
        group_tool = QGroupBox("Tool Settings")
        group_tool.setStyleSheet(get_group_css({}))
        layout_tool = QVBoxLayout(group_tool)

        if platform.system() == 'Linux':
            label = QLabel("Linux: 创建系统计划前提示检查账号/自动登录配置")
            layout_tool.addWidget(label)
            layout_tool.addWidget(self.check_linux_credentials_on_plan_create)
        else:
            label = QLabel("当前系统无Linux相关工具设置")
            layout_tool.addWidget(label)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_tool)
