import platform
from datetime import datetime

from PyQt5.QtCore import QSize, QDate
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, \
    QDialog

from src.ui.ui_message import MessageBox
from src.utils.const import AppPath, Key
from src.utils.log import Log
from src.utils.utils import Utils
from ui.custom.custom_function import UiFunc
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import TaskListWidget
from ui.template.ui_page import PageContent, Container
from src.ui.ui_system_plan import SystemPlanDialog

# 根据操作系统导入相应的模块
if platform.system() == 'Windows':
    from src.ui.ui_windows_login import WindowsLoginDialog
    from src.extend.auto_windows_plan import create_task, delete_scheduled_task
    from src.extend.network_manager import connect_network, disconnect_network
elif platform.system() == 'Linux':
    from src.ui.ui_linux_login import LinuxLoginDialog
    from src.extend.auto_linux_plan import create_crontab_task, delete_crontab_task
    from src.extend.auto_linux_network import connect_network, disconnect_network
else:
    # 其他系统暂不支持特定功能
    pass


class SystemTaskPage(PageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(SystemTaskPage, self).__init__(y, x)

    def init_container(self):
        task = TaskListContainer(4, 6)
        self.add_container(task, 0,0)

        login = SystemLoginContainer(2,2)
        self.add_container(login, 0,4)

        if platform.system() == 'Linux':
            nettest = NetWorkTestContainer(2,2)
            self.add_container(nettest, 2,4)

class TaskListContainer(Container):
    task_list=[]
    def __init__(self, x, y):
        super(TaskListContainer, self).__init__(x, y)

        self.system_plan_list = QListWidget()
        self.button_create = QPushButton("Create")
        self.button_delete = QPushButton("Delete")

        self.init_ui_layout()
        self.update_plan_list()

    def init_ui_layout(self):
        group_system = QGroupBox(f"System Plan List")
        group_system.setStyleSheet(get_group_css({}))
        layout_system = QVBoxLayout(group_system)

        layout_system.addWidget(self.system_plan_list)

        layout_plan_list_buttons = QHBoxLayout()
        layout_plan_list_buttons.addWidget(self.button_create)
        layout_plan_list_buttons.addWidget(self.button_delete)
        layout_system.addLayout(layout_plan_list_buttons)

        self.button_create.clicked.connect(self.create_system_plan)
        self.button_delete.clicked.connect(self.delete_system_plan)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_system)

    def check_linux_credentials(self):
        try:
            credentials_valid = False
            max_attempts = 3
            attempt = 0

            while not credentials_valid and attempt < max_attempts:
                # 检查当前账号状态
                login_dlg = LinuxLoginDialog(self)

                # 如果是第一次尝试，先检查是否已有有效配置
                if attempt == 0:
                    is_valid, status_msg = login_dlg.get_credentials_status()
                    if is_valid:
                        credentials_valid = True
                        break

                # 显示登录对话框要求用户配置或验证账号
                if login_dlg.exec_() == QDialog.Accepted:
                    is_valid, status_msg = login_dlg.get_credentials_status()
                    if is_valid:
                        credentials_valid = True
                        break
                    else:
                        # 账号无效，询问是否重试
                        retry = MessageBox(f"账号验证失败：{status_msg}\n\n是否重新配置账号信息？", "账号验证失败",
                                           buttons=["重试", "取消"])
                        if retry != "重试":
                            return False
                else:
                    # 用户取消了登录对话框
                    return False

                attempt += 1

            if not credentials_valid:
                MessageBox("账号验证失败次数过多，无法创建任务。请确保Linux账号配置正确后重试。")
                return False

            return True
        except Exception as e:
            Log.error(str(e))
            MessageBox(str(e))
            return False

    def create_system_plan(self):
        if platform.system() == 'Linux' and not self.check_linux_credentials():
            return

        task = self.do_create_plan()

        if task is None: return
        self.task_list.append(task)
        Utils.write_dict_to_file(AppPath.TasksJson, self.task_list)
        self.update_plan_list()

    def do_create_plan(self):
        try:
            plan_ui = SystemPlanDialog(self)
            if plan_ui.exec_() == QDialog.Accepted:
                value = plan_ui.values()
                task_to_json, task_list_to_create = UiFunc.parse_ui_value_to_task(value)
                for task in task_list_to_create:
                    ok, error = create_task(task)
                    if error:
                        raise Exception(error)

                MessageBox(f"Create Task: {task_to_json[Key.TaskName]} Success!")
                Log.info(f"create system plan task: {task_to_json}")

                return task_to_json
        except Exception as e:
            Log.error(str(e))
            MessageBox(str(e))
            return None

    def delete_system_plan(self):
        try:
            selected_item = self.system_plan_list.currentItem()
            selected_widget = self.system_plan_list.itemWidget(selected_item)
            if not selected_widget:
                Log.error("选中项未绑定Plan")
                return

            plan_id = selected_widget.objectName()
            Log.info(f"删除Plan: {plan_id}")

            delete_task = None
            for task in self.task_list:
                if task[Key.TaskID] == plan_id:
                    delete_task = task
                    break
            if delete_task is None:
                raise Exception(f"Delete plan failed, no plan id: {plan_id}")
            short_name = delete_task[Key.TaskName]
            plan_name = delete_task[Key.WindowsPlanName]

            dlg = MessageBox(f"\nAre you really want to delete this Plan:\n\n{short_name}\n", need_check=True, message_only=False, message_name="Delete Plan")
            if dlg.exec_() != QDialog.Accepted:
                return

            if platform.system() == "Windows":
                if delete_task[Key.TriggerType] == Key.Multiple:
                    for task_name in plan_name:
                        ok, error = delete_scheduled_task(plan_name.get(task_name))
                        if not ok: raise Exception(error)
                else:
                    ok, error = delete_scheduled_task(plan_name)
                    if not ok: raise Exception(error)
            elif platform.system() == "Linux":
                ok, error = delete_crontab_task(plan_name)
                if not ok: raise Exception(error)
            else:
                raise Exception("System not supported")

            self.task_list.remove(delete_task)
            Utils.write_dict_to_file(AppPath.TasksJson, self.task_list)
            self.update_plan_list()

        except Exception as e:
            Log.error(e)
            MessageBox(e)

    def update_plan_list(self):
        try:
            dict_list = Utils.read_dict_from_json(AppPath.TasksJson)
            if dict_list is None: return

            self.system_plan_list.clear()
            if isinstance(dict_list, list):
                self.task_list = dict_list
                for plan_dict in self.task_list:
                    self.add_plan_ui(plan_dict)
            elif isinstance(dict_list, dict):
                self.task_list.append(dict_list)
                self.add_plan_ui(dict_list)
            else:
                raise Exception("Load tasks failed!")

        except Exception as e:
            message = f"Update windows plan list failed: {e}"
            Log.error(message)
            MessageBox(message)

    def add_plan_ui(self, task):
        widget_plan_line = TaskListWidget(task)

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 40))
        self.system_plan_list.addItem(item)
        self.system_plan_list.setItemWidget(item, widget_plan_line)

class SystemLoginContainer(Container):
    def __init__(self, x, y):
        super(SystemLoginContainer, self).__init__(x, y)

        self.set_auto_login = QPushButton("System Auto Login")

        self.init_ui_layout()

    def init_ui_layout(self):
        system_name = platform.system()
        group_system = QGroupBox(f"Auto Login")
        group_system.setStyleSheet(get_group_css({}))
        layout_system = QVBoxLayout(group_system)

        self.set_auto_login.clicked.connect(self.auto_system_login)

        if system_name == 'Linux':
            tip_label = QLabel("提示：Linux自动登录功能需要管理员权限运行应用")
            tip_label.setStyleSheet("color: orange; font-size: 12px;")
            tip_label.setWordWrap(True)
            layout_system.addWidget(tip_label)

        layout_system.addWidget(self.set_auto_login)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_system)

    def auto_system_login(self):
        dlg = None
        if platform.system() == 'Linux':
            dlg = LinuxLoginDialog(self)
        elif platform.system() == 'Windows':
            dlg = WindowsLoginDialog(self)

        if dlg is not None:
            dlg.exec_()

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
        try:
            # 检查网络管理功能是否可用
            if disconnect_network is None:
                MessageBox("Network management is not supported on this platform")
                return

            success, error = disconnect_network()
            if success:
                MessageBox("Network disconnected successfully!")
            else:
                MessageBox(f"Failed to disconnect network: {error}")
        except Exception as e:
            MessageBox(f"Error disconnecting network: {str(e)}")

    def connect_network_now(self):
        try:
            # 检查网络管理功能是否可用
            if connect_network is None:
                MessageBox("Network management is not supported on this platform")
                return

            success, error = connect_network()
            if success:
                MessageBox("Network connected successfully!")
            else:
                MessageBox(f"Failed to connect network: {error}")
        except Exception as e:
            MessageBox(f"Error connecting network: {str(e)}")


