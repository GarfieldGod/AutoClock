import platform
from datetime import datetime

from PyQt5.QtCore import QSize, QDate
from PyQt5.QtGui import QFont
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
from src.ui.ui_system_plan_edit import EditSystemPlanDialog
from src.utils.const import WebPath

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
        task = TaskListContainer(6, 4)
        self.add_container(task, 0,0)

        login = SystemLoginContainer(2,2)
        self.add_container(login, 4,0)

        if platform.system() == 'Linux':
            nettest = NetWorkTestContainer(2,2)
            self.add_container(nettest, 4,2)

class TaskListContainer(Container):
    def __init__(self, x, y):
        super(TaskListContainer, self).__init__(x, y)

        self.task_list = []
        self.system_plan_list = QListWidget()
        self.button_create = QPushButton("Create")
        self.button_delete = QPushButton("Delete")

        self.init_ui_layout()
        self.update_plan_list()

    def _get_cfg(self, key, default=None):
        try:
            w = self.window()
            if hasattr(w, "get_save_data"):
                return w.get_save_data(key, default)
        except Exception:
            pass
        return default

    @staticmethod
    def _error_text(error, default: str) -> str:
        text = str(error or "").strip()
        return text if text else default

    def _normalize_task(self, task: dict) -> tuple[dict, bool]:
        changed = False
        if Key.Enabled not in task:
            task[Key.Enabled] = True
            changed = True
        if Key.LastRunResult not in task:
            task[Key.LastRunResult] = "-"
            changed = True
        return task, changed

    def _read_tasks(self):
        try:
            w = self.window()
            if hasattr(w, "read_tasks_list"):
                return w.read_tasks_list()
        except Exception:
            pass
        return Utils.read_dict_from_json(AppPath.TasksJson)

    def _write_tasks(self, tasks) -> bool:
        try:
            w = self.window()
            if hasattr(w, "write_tasks_list"):
                return bool(w.write_tasks_list(tasks))
        except Exception:
            pass
        try:
            Utils.write_dict_to_file(AppPath.TasksJson, tasks)
            return True
        except Exception:
            return False

    def _get_remote_plan_service(self):
        try:
            w = self.window()
            if hasattr(w, "remote_plan_service"):
                return w.remote_plan_service
        except Exception:
            pass
        return None

    def _read_config(self) -> dict:
        try:
            w = self.window()
            if hasattr(w, "data_store") and hasattr(w.data_store, "read_config"):
                data = w.data_store.read_config()
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
        try:
            data = Utils.read_dict_from_json(AppPath.DataJson)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_config(self, config: dict) -> bool:
        try:
            w = self.window()
            if hasattr(w, "data_store") and hasattr(w.data_store, "write_config"):
                return bool(w.data_store.write_config(config))
        except Exception:
            pass
        try:
            Utils.write_dict_to_file(AppPath.DataJson, config)
            return True
        except Exception:
            return False

    def init_ui_layout(self):
        group_system = QGroupBox(f"System Plan List")
        group_system.setStyleSheet(get_group_css({}))
        layout_system = QVBoxLayout(group_system)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(6, 0, 6, 0)
        header_layout.setSpacing(6)
        header_defs = [
            ("Task Name", TaskListWidget.COL_TASK),
            ("Operation", TaskListWidget.COL_OPERATION),
            ("Trigger", TaskListWidget.COL_TRIGGER),
            ("Time", TaskListWidget.COL_TIME),
            ("Schedule", TaskListWidget.COL_SCHEDULE),
            ("Last Result", TaskListWidget.COL_RESULT),
            ("Status", TaskListWidget.COL_STATUS),
        ]
        for title, width in header_defs:
            label = QLabel(title)
            label.setFixedWidth(width)
            f = QFont()
            f.setPointSize(11)
            f.setBold(True)
            label.setFont(f)
            header_layout.addWidget(label, 0)
        layout_system.addLayout(header_layout)

        self.system_plan_list.setSpacing(2)
        self.system_plan_list.setUniformItemSizes(True)
        layout_system.addWidget(self.system_plan_list)

        layout_plan_list_buttons = QHBoxLayout()
        layout_plan_list_buttons.addWidget(self.button_create)
        layout_plan_list_buttons.addWidget(self.button_delete)
        layout_system.addLayout(layout_plan_list_buttons)

        self.button_create.clicked.connect(self.create_system_plan)
        self.button_delete.clicked.connect(self.delete_system_plan)
        self.system_plan_list.itemDoubleClicked.connect(self.edit_system_plan)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_system)

    def _create_plan_tasks(self, task_list_to_create):
        for task in task_list_to_create:
            try:
                if platform.system() == "Windows":
                    w = self.window()
                    if hasattr(w, "is_remote_connected") and w.is_remote_connected():
                        svc = self._get_remote_plan_service()
                        if svc is None:
                            return False, "远端服务未初始化，请重新连接SSH"
                        ok, error = svc.cron_create(task)
                    else:
                        ok, error = create_task(task)
                elif platform.system() == "Linux":
                    ok, error = create_crontab_task(task)
                else:
                    return False, "System not supported"
            except Exception as e:
                return False, self._error_text(e, "Create plan failed")

            if error or not ok:
                return False, self._error_text(error, "Create plan failed")
        return True, None

    def _delete_plan_task(self, task):
        plan_name = task[Key.SystemPlanName]

        try:
            if platform.system() == "Windows":
                w = self.window()
                if hasattr(w, "is_remote_connected") and w.is_remote_connected():
                    svc = self._get_remote_plan_service()
                    if svc is None:
                        return False, "远端服务未初始化，请重新连接SSH"

                    names = svc.task_names_from_plan(task)
                    ok, error = svc.cron_delete(names)
                else:
                    if task[Key.TriggerType] == Key.Multiple and isinstance(plan_name, dict):
                        for task_name in plan_name:
                            ok, error = delete_scheduled_task(plan_name.get(task_name))
                            if not ok:
                                return False, self._error_text(error, "Delete plan failed")
                    else:
                        ok, error = delete_scheduled_task(plan_name)
                        if not ok:
                            return False, self._error_text(error, "Delete plan failed")
            elif platform.system() == "Linux":
                if task[Key.TriggerType] == Key.Multiple and isinstance(plan_name, dict):
                    for task_name in plan_name:
                        ok, error = delete_crontab_task(plan_name.get(task_name))
                        if not ok:
                            return False, self._error_text(error, "Delete plan failed")
                else:
                    ok, error = delete_crontab_task(plan_name)
                    if not ok:
                        return False, self._error_text(error, "Delete plan failed")
            else:
                return False, "System not supported"
        except Exception as e:
            return False, self._error_text(e, "Delete plan failed")

        return True, None

    def _find_task_by_plan_id(self, plan_id):
        for index, task in enumerate(self.task_list):
            if task[Key.TaskID] == plan_id:
                return index, task
        return -1, None

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
            message = self._error_text(e, "Edit task failed")
            Log.error(message)
            MessageBox(message)
            return False

    def create_system_plan(self):
        if platform.system() == 'Linux':
            # 如果当前Linux账号配置已有效，则不再弹出提示，直接创建计划
            try:
                login_dlg = LinuxLoginDialog(self)
                is_valid, _ = login_dlg.get_credentials_status()
            except Exception as e:
                Log.error(str(e))
                is_valid = False

            if not is_valid:
                try:
                    config = self._read_config() or {}
                except Exception as e:
                    Log.error(str(e))
                    config = {}

                need_check = config.get(Key.CheckLinuxCredentialsOnPlanCreate, True)

                if need_check:
                    choice = MessageBox(
                        "建议先配置并验证Linux账号与自动登录，以确保计划任务执行后能够自动登录系统。\n\n"
                        "请选择下一步操作：",
                        "Linux账号配置提示",
                        buttons=["去配置并验证", "直接创建", "不再提示"],
                    )

                    if choice == "去配置并验证":
                        if not self.check_linux_credentials():
                            return
                    elif choice == "不再提示":
                        config[Key.CheckLinuxCredentialsOnPlanCreate] = False
                        try:
                            self._write_config(config)
                        except Exception as e:
                            Log.error(str(e))
                    # "直接创建" 以及 "不再提示" 最终都继续创建计划

        task = self.do_create_plan()

        if task is None: return
        self.task_list.append(task)
        if not self._write_tasks(self.task_list):
            MessageBox("Save tasks failed")
            return
        self.update_plan_list()

    def do_create_plan(self):
        try:
            plan_ui = SystemPlanDialog(self)
            if plan_ui.exec_() == QDialog.Accepted:
                value = plan_ui.values()
                task_to_json, task_list_to_create = UiFunc.parse_ui_value_to_task(value)
                ok, error = self._create_plan_tasks(task_list_to_create)
                if not ok:
                    raise Exception(error or "Create task failed")

                task_to_json[Key.Enabled] = True
                task_to_json[Key.LastRunResult] = "-"

                MessageBox(f"Create Task: {task_to_json[Key.TaskName]} Success!")
                Log.info(f"create system plan task: {task_to_json}")

                return task_to_json
        except Exception as e:
            message = self._error_text(e, "Create task failed")
            Log.error(message)
            MessageBox(message)
            return None

    def edit_system_plan(self, current_item):
        try:
            if current_item is None:
                return
            selected_widget = self.system_plan_list.itemWidget(current_item)
            if not selected_widget:
                return

            plan_id = selected_widget.objectName()
            task_index, old_task = self._find_task_by_plan_id(plan_id)
            if old_task is None:
                raise Exception(f"Edit plan failed, no plan id: {plan_id}")

            edit_dlg = EditSystemPlanDialog(old_task, self)
            if edit_dlg.exec_() != QDialog.Accepted:
                return

            value = edit_dlg.values()
            parsed = UiFunc.parse_ui_value_to_task(value, task_id_override=old_task.get(Key.TaskID))
            if not parsed:
                raise Exception("Edit plan failed, invalid plan data")

            task_to_json, task_list_to_create = parsed
            task_to_json[Key.Enabled] = bool(old_task.get(Key.Enabled, True))
            task_to_json[Key.LastRunResult] = str(old_task.get(Key.LastRunResult, "-") or "-")
            ok, error = self._delete_plan_task(old_task)
            if not ok:
                raise Exception(error or "Delete old task failed")

            ok, error = self._create_plan_tasks(task_list_to_create)
            if not ok:
                raise Exception(error or "Create new task failed")

            self.task_list[task_index] = task_to_json
            if not self._write_tasks(self.task_list):
                raise Exception("Save tasks failed")
            self.update_plan_list()
            MessageBox(f"Edit Task: {task_to_json[Key.TaskName]} Success!")
        except Exception as e:
            Log.error(str(e))
            MessageBox(str(e))

    def delete_system_plan(self):
        try:
            current_item = self.system_plan_list.currentItem()
            if current_item is None:
                MessageBox("请选择要删除的计划任务")
                return
            selected_widget = self.system_plan_list.itemWidget(current_item)
            if not selected_widget:
                Log.error("选中项未绑定Plan")
                return

            plan_id = selected_widget.objectName()
            Log.info(f"删除Plan: {plan_id}")

            _, delete_task = self._find_task_by_plan_id(plan_id)
            if delete_task is None:
                raise Exception(f"Delete plan failed, no plan id: {plan_id}")
            short_name = delete_task[Key.TaskName]

            dlg = MessageBox(f"\nAre you really want to delete this Plan:\n\n{short_name}\n", need_check=True, message_only=False, message_name="Delete Plan")
            if dlg.exec_() != QDialog.Accepted:
                return

            ok, error = self._delete_plan_task(delete_task)
            if not ok:
                raise Exception(error or "Delete plan failed")

            self.task_list.remove(delete_task)
            if not self._write_tasks(self.task_list):
                raise Exception("Save tasks failed")
            self.update_plan_list()

        except Exception as e:
            message = self._error_text(e, "Delete plan failed")
            Log.error(message)
            MessageBox(message)

    def toggle_system_plan_enabled(self, plan_id=None, enabled=None):
        try:
            if not plan_id:
                current_item = self.system_plan_list.currentItem()
                if current_item is None:
                    MessageBox("Please select one task")
                    return False
                selected_widget = self.system_plan_list.itemWidget(current_item)
                if not selected_widget:
                    return False
                plan_id = selected_widget.objectName()

            task_index, task = self._find_task_by_plan_id(plan_id)
            if task is None or task_index < 0:
                raise Exception(f"Task not found: {plan_id}")

            if enabled is None:
                new_enabled = not bool(task.get(Key.Enabled, True))
            else:
                new_enabled = bool(enabled)

            self.task_list[task_index][Key.Enabled] = new_enabled
            if not self._write_tasks(self.task_list):
                raise Exception("Save task status failed")

            self.update_plan_list()
            if enabled is None:
                MessageBox(f"Task status updated: {'ON' if new_enabled else 'OFF'}")
            return True
        except Exception as e:
            message = self._error_text(e, "Update task status failed")
            Log.error(message)
            MessageBox(message)
            return False

    def update_plan_list(self):
        try:
            dict_list = self._read_tasks()
            if dict_list is None: return

            self.system_plan_list.clear()
            self.task_list = []
            changed = False
            if isinstance(dict_list, list):
                for plan_dict in dict_list:
                    if not isinstance(plan_dict, dict):
                        continue
                    normalized_task, task_changed = self._normalize_task(plan_dict)
                    self.task_list.append(normalized_task)
                    changed = changed or task_changed
                    self.add_plan_ui(normalized_task)
            elif isinstance(dict_list, dict):
                normalized_task, changed = self._normalize_task(dict_list)
                self.task_list.append(normalized_task)
                self.add_plan_ui(normalized_task)
            else:
                raise Exception("Load tasks failed!")

            if changed:
                self._write_tasks(self.task_list)

        except Exception as e:
            message = f"Update windows plan list failed: {e}"
            Log.error(message)
            MessageBox(message)

    def add_plan_ui(self, task):
        widget_plan_line = TaskListWidget(task, on_status_toggle=self.toggle_system_plan_enabled)

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 34))
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


