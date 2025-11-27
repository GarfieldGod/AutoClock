import platform

from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QListWidget

from ui.pages.custom_style import get_group_css
from ui.template.ui_page import PageContent, Container

if platform.system() == 'Windows':
    from src.ui.ui_windows_login import WindowsLoginDialog
elif platform.system() == 'Linux':
    from src.ui.ui_linux_login import LinuxLoginDialog


class SystemTaskPage(PageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(SystemTaskPage, self).__init__(y, x)

    def init_container(self):
        task = TaskListContainer(3, 6)
        self.add_container(task, 0,0)

        login = SystemLoginContainer(3,2)
        self.add_container(login, 0,3)

        if platform.system() == 'Linux':
            nettest = NetWorkTestContainer(3,2)
            self.add_container(nettest, 2,3)

        nettest = NetWorkTestContainer(3, 2)
        self.add_container(nettest, 2, 3)

class TaskListContainer(Container):
    def __init__(self, x, y):
        super(TaskListContainer, self).__init__(x, y)

        self.system_plan_list = QListWidget()
        self.button_create = QPushButton("Create")
        self.button_delete = QPushButton("Delete")

        self.init_ui_layout()

    def init_ui_layout(self):
        system_name = platform.system()
        group_system = QGroupBox(f"System Plan List")
        group_system.setStyleSheet(get_group_css({}))
        layout_system = QVBoxLayout(group_system)

        layout_system.addWidget(self.system_plan_list)

        layout_plan_list_buttons = QHBoxLayout()
        layout_plan_list_buttons.addWidget(self.button_create)
        layout_plan_list_buttons.addWidget(self.button_delete)
        layout_system.addLayout(layout_plan_list_buttons)

        if system_name == 'Windows':
            self.button_create.clicked.connect(self.create_windows_plan)
            self.button_delete.clicked.connect(self.delete_windows_plan)
        elif system_name == 'Linux':
            self.button_create.clicked.connect(self.create_linux_plan)
            self.button_delete.clicked.connect(self.delete_linux_plan)

            # net_layout = QHBoxLayout()
            # net_layout.setSpacing(5)
            # net_layout.setContentsMargins(0, 0, 0, 0)
            # self.button_disconnect_network.clicked.connect(self.disconnect_network_now)
            # self.button_connect_network.clicked.connect(self.connect_network_now)
            # net_layout.addWidget(self.button_disconnect_network)
            # net_layout.addWidget(self.button_connect_network)

            # layout_system.addLayout(net_layout)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_system)

    def create_linux_plan(self):
        pass

    def delete_linux_plan(self):
        pass

    def create_windows_plan(self):
        pass
    def delete_windows_plan(self):
        pass

class SystemLoginContainer(Container):
    def __init__(self, x, y):
        super(SystemLoginContainer, self).__init__(x, y)

        self.set_auto_login = QPushButton("Set System Auto Login")

        self.init_ui_layout()

    def init_ui_layout(self):
        system_name = platform.system()
        group_system = QGroupBox(f"Auto Login")
        group_system.setStyleSheet(get_group_css({}))
        layout_system = QVBoxLayout(group_system)

        if system_name == 'Windows':
            self.set_auto_login.clicked.connect(self.auto_login_windows)
        elif system_name == 'Linux':
            self.set_auto_login.clicked.connect(self.auto_login_linux)

            tip_label = QLabel("提示：Linux自动登录功能需要管理员权限运行应用")
            tip_label.setStyleSheet("color: orange; font-size: 12px;")
            tip_label.setWordWrap(True)
            layout_system.addWidget(tip_label)

        layout_system.addWidget(self.set_auto_login)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_system)

    def auto_login_windows(self):
        if platform.system() == 'Windows':
            dlg = WindowsLoginDialog(self)
            dlg.exec_()
            # 重新加载配置
            self.load()

    def auto_login_linux(self):
        if platform.system() == 'Linux':
            dlg = LinuxLoginDialog(self)
            dlg.exec_()
            # 重新加载配置
            self.load()

class NetWorkTestContainer(Container):
    def __init__(self, x, y):
        super(NetWorkTestContainer, self).__init__(x, y)

        self.button_disconnect_network = QPushButton("立即断网")
        self.button_connect_network = QPushButton("立即联网")

        self.init_ui_layout()

    def init_ui_layout(self):
        self.button_disconnect_network.clicked.connect(self.disconnect_network_now)
        self.button_connect_network.clicked.connect(self.connect_network_now)

        group_system = QGroupBox(f"Test Network")
        group_system.setStyleSheet(get_group_css({}))

        net_layout = QHBoxLayout(group_system)
        net_layout.addWidget(self.button_disconnect_network)
        net_layout.addWidget(self.button_connect_network)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_system)

    def disconnect_network_now(self):
        pass

    def connect_network_now(self):
        pass


